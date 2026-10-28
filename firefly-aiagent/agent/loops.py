"""
Loop Engineering for Firefly III AI Agent using LangGraph StateGraph.

Implements:
1. Planning Loop: Decomposes complex financial inquiries into sequential sub-goals.
2. ReAct Loop: Cyclical Reason -> Act (Tool Call) -> Observe (Observation) loop.
3. Reflection Loop: Post-execution evaluation and automatic user preference discovery.
"""

import json
import logging
import re
import warnings
from typing import Annotated, Any, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from memory.manager import MemoryManager
from agent.harness import AgentHarnessCallback

warnings.filterwarnings("ignore", category=UserWarning, module="langchain_google_genai")

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Internal graph state passed between cognition nodes."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    plan: list[str]
    is_complex: bool
    reflection: str


def _extract_json_block(text: str) -> dict[str, Any]:
    """Safely extract and parse JSON object from LLM response text."""
    try:
        # First attempt: find outermost JSON curly brackets
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        # Second attempt: strip markdown code blocks
        cleaned = text.strip().strip("`").removeprefix("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.debug("Failed to extract JSON from text: %s | text: %s", e, text[:150])
        return {}


def create_agent_graph(
    llm_model: str,
    gemini_api_key: str,
    tools: list[BaseTool],
    memory_manager: MemoryManager,
    harness: AgentHarnessCallback,
    user_info: Any = None,
):
    """Build and compile the LangGraph StateGraph agent."""

    # Initialize Gemini LLM with bound tools & automatic retry backoff
    llm = ChatGoogleGenerativeAI(
        model=llm_model,
        google_api_key=gemini_api_key,
        temperature=0.1,
        max_retries=3,
    )
    llm_with_tools = llm.bind_tools(tools)

    user_info_dict = user_info if isinstance(user_info, dict) else {}
    user_email = user_info_dict.get("email", "")
    user_role = user_info_dict.get("role", "owner")
    user_id = str(user_info_dict.get("id", "1"))

    # ── Node 1: Planning Loop ───────────────────────────────────
    def planner_node(state: AgentState) -> dict[str, Any]:
        """Classify task complexity and decompose into steps if complex."""
        last_user_msg = ""
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                last_user_msg = str(m.content)
                break

        if not last_user_msg:
            return {"plan": [], "is_complex": False}

        # Smart Heuristic Optimization: Skip LLM call for simple inquiries to conserve rate limits
        complex_triggers = [
            "lalu", "kemudian", "dan bandingkan", "bandingkan", "evaluasi",
            "analisis", "setelah itu", "serta", "jika ", "laporan lengkap", "hitung dan"
        ]
        is_potentially_complex = any(trig in last_user_msg.lower() for trig in complex_triggers) or len(last_user_msg.split()) > 16

        if not is_potentially_complex:
            logger.info("Planner: Skipped LLM call for simple query '%s' to conserve quota.", last_user_msg[:40])
            return {"is_complex": False, "plan": []}

        facts_context = memory_manager.get_formatted_facts()
        user_identity_context = f"Logged-in User: {user_email} (Role: {user_role})" if user_email else ""
        classify_prompt = (
            f"You are a financial task planner. Analyze this user request:\n"
            f"'{last_user_msg}'\n\n"
            f"{user_identity_context}\n"
            f"User Context & Preferences: {facts_context}\n\n"
            f"Determine if this request is SIMPLE (a single inquiry or single tool action) "
            f"or COMPLEX (requires multi-step analysis, checking limits, comparing spending, calculating remaining balance, or multiple tool actions).\n"
            f"If COMPLEX, formulate 2-4 concrete sequential steps to solve it.\n"
            f"Respond strictly in valid JSON format:\n"
            f'{{"is_complex": true, "plan": ["Step 1: ...", "Step 2: ...", "Step 3: ..."]}}\n'
            f"Or if simple:\n"
            f'{{"is_complex": false, "plan": []}}'
        )

        try:
            res = llm.invoke([HumanMessage(content=classify_prompt)])
            raw_text = str(res.content) if hasattr(res, "content") else str(res)
            data = _extract_json_block(raw_text)
            is_complex = bool(data.get("is_complex", False))
            plan = data.get("plan", [])
            logger.info("Planner: is_complex=%s, plan=%s", is_complex, plan)
            return {"is_complex": is_complex, "plan": plan}
        except Exception as e:
            logger.warning("Planning fallback: %s", e)
            return {"is_complex": False, "plan": []}

    # ── Node 2: Reasoning Node (ReAct) ──────────────────────────
    def agent_node(state: AgentState) -> dict[str, Any]:
        """Core reasoning node: calls LLM with tools and memory injection."""
        facts_context = memory_manager.get_formatted_facts()
        plan_steps = state.get("plan", [])
        if plan_steps:
            plan_str = "\n".join(f"- {s}" for s in plan_steps)
        else:
            plan_str = "Direct single-step execution."

        user_identity_instruction = (
            f"Active User Session:\n"
            f"- User Email: {user_email}\n"
            f"- Role: {user_role}\n"
            f"- User ID: {user_id}\n"
            f"You know this user is currently logged in. Greet or address them accordingly if asked who is logged in.\n\n"
        ) if user_email else ""

        system_instruction = (
            "You are an intelligent, proactive autonomous AI financial assistant connected to Firefly III Personal Finance Manager.\n"
            f"{user_identity_instruction}"
            "You can interact with real-time financial data via Docker REST API.\n\n"
            f"{facts_context}\n\n"
            f"Execution Plan:\n{plan_str}\n\n"
            "Capabilities & Guidelines:\n"
            "1. User Profile: You know the active user details and can check via `get_user_profile` if needed.\n"
            "2. Accounts: Query accounts, inspect balances, or create new accounts (asset/liability/credit card).\n"
            "3. Transactions, Transfers & Deposits:\n"
            "   - Expenses/Withdrawals: Use `create_transaction` (type='withdrawal') when money leaves asset account to pay expense.\n"
            "   - Transfers: Use `create_transfer` when moving money between user's own asset accounts (e.g. BCA to Dompet/GoPay).\n"
            "   - Incomes/Deposits: Use `create_deposit` when user receives salary, revenue, or cashback into an asset account.\n"
            "   - Listing & Search: `list_transactions`, `search_transactions`, or `delete_transaction` for mistakes.\n"
            "4. Budgets & Limits: Inspect budget limits vs actual spending (`check_budget_spending_and_limit`), list budgets, or create budgets.\n"
            "5. Piggy Banks / Celengan: Track savings goals, create goals (`create_piggy_bank`), or allocate money (`add_to_piggy_bank`).\n"
            "6. Recurring Bills: List scheduled bills and track upcoming due dates (`list_bills`, `create_bill`).\n"
            "7. Tags: Label transactions for special occasions (#liburan, #reimburse) with `list_tags` and `create_tag`.\n"
            "8. Automation Rules & Recurrences: Inspect automated rules (`list_rules`) and recurring schedules (`list_recurrences`).\n"
            "9. Past Spending & Search: For questions about past spending history or specific transactions ('kapan terakhir beli kopi?', 'cari pengeluaran bensin'), use `search_transactions` or `list_transactions` to query real-time records directly.\n"
            "10. Output Formatting Guidelines for Web Display (CRITICAL FOR USER READABILITY):\n"
            "   - Format all output in clean, elegant GitHub Flavored Markdown that renders beautifully on the user's web interface.\n"
            "   - Executive Summary: Always start with 1-2 friendly, conversational opening sentences summarizing the answer directly.\n"
            "   - Markdown Tables for Lists: Whenever displaying multiple items (accounts, transactions, bills, budgets, piggies), ALWAYS use a neat Markdown Table with clear headers:\n"
            "     Example for Accounts:\n"
            "     | No | Nama Rekening | Tipe Akun | Saldo Saat Ini | Status |\n"
            "     | :--- | :--- | :--- | :--- | :--- |\n"
            "     | 1 | Rekening BCA | Asset Account | **Rp 15.000.000** | 🟢 Aktif |\n"
            "   - Receipt Cards for Completed Actions: When an action occurs (transfer, new transaction, deposit), summarize it in a neat key-value table or receipt card:\n"
            "     | Rincian Transaksi | Keterangan |\n"
            "     | :--- | :--- |\n"
            "     | **Jenis Transaksi** | 🔄 Transfer Saldo |\n"
            "     | **Dari Rekening** | Rekening BCA |\n"
            "     | **Ke Rekening** | Dompet Tunai |\n"
            "     | **Nominal** | **Rp 500.000** |\n"
            "     | **Status** | ✅ Berhasil Dicatat di Firefly III |\n"
            "   - Currency Formatting: ALWAYS format money numbers with Indonesian Rupiah style and dot thousand separators (e.g., `Rp 150.000`, `Rp 2.500.000`). NEVER write plain digits like 1500000 or raw JSON.\n"
            "   - Bold Key Values: Bold important figures (e.g. **Total Saldo:** Rp 15.500.000).\n"
            "   - Visual Emojis: Use visual status indicators:\n"
            "     * 🟢 Aktif / ✅ Berhasil / 📈 Pemasukan\n"
            "     * ⚠️ Mendekati Limit / 🟡 Peringatan\n"
            "     * 🔴 Over-budget / 📉 Pengeluaran\n"
            "     * 💳 Rekening / 🏦 Bank / 🎯 Target / 🏷️ Tag\n"
            "   - Callout Insights: For helpful notes, tips, or budget advice, use Markdown blockquotes (e.g. `> 💡 **Catatan Finansial:** ...`).\n"
            "   - Next Steps: Finish with 1-2 proactive, brief bullet points offering helpful follow-up options.\n"
            "11. Always query real data before making conclusions. Respond politely, warmly, and clearly in Indonesian (matching the user)."
        )

        messages = [SystemMessage(content=system_instruction)] + list(state["messages"])
        response = llm_with_tools.invoke(messages, config={"callbacks": [harness]})
        return {"messages": [response]}

    # ── Node 3: Tool Execution Node ─────────────────────────────
    tool_node = ToolNode(tools)

    # ── Node 4: Reflection Loop ─────────────────────────────────
    def reflection_node(state: AgentState) -> dict[str, Any]:
        """Post-execution evaluation and automatic long-term preference discovery."""
        last_ai_msg = state["messages"][-1]
        ai_text = ""
        if hasattr(last_ai_msg, "content"):
            if isinstance(last_ai_msg.content, str):
                ai_text = last_ai_msg.content
            elif isinstance(last_ai_msg.content, list):
                ai_text = " ".join(str(part) for part in last_ai_msg.content)

        last_user_msg = ""
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                last_user_msg = str(m.content)
                break

        # Smart Heuristic Optimization: Only call LLM reflection if user stated a preference or rule
        preference_triggers = [
            "ingat", "catat aturan", "jangan", "selalu", "maksimal", "minimal",
            "preferensi", "rule", "mulai sekarang", "patokan", "default", "prefer", "kebiasaan"
        ]
        has_pref_hint = any(trig in last_user_msg.lower() for trig in preference_triggers)

        if not has_pref_hint:
            summary = "Task completed successfully."
            memory_manager.save_reflection_episode(
                user_goal=last_user_msg,
                plan=json.dumps(state.get("plan", [])),
                outcome=summary,
                learnings="",
            )
            return {"reflection": summary}

        reflect_prompt = (
            f"Reflect on this completed financial interaction:\n"
            f"User Goal: {last_user_msg}\n"
            f"AI Response: {ai_text[:500]}\n\n"
            f"Did the user state or express any persistent rules, preferences, habits, or budget constraints?\n"
            f"(e.g., maximum daily lunch limit, default payment account, preferred category mapping for coffee/transport).\n"
            f"Reply strictly in JSON:\n"
            f'{{"has_preference": true/false, "key": "e.g. max_lunch_budget", "value": "e.g. Rp 35.000 per hari", "category": "preference/rule", "summary": "Brief summary of interaction"}}\n'
            f"If no persistent rule was expressed:\n"
            f'{{"has_preference": false, "summary": "Task completed successfully"}}'
        )

        try:
            res = llm.invoke([HumanMessage(content=reflect_prompt)])
            raw_text = str(res.content) if hasattr(res, "content") else str(res)
            data = _extract_json_block(raw_text)
            summary = data.get("summary", "Task completed.")

            # Record episodic memory
            memory_manager.save_reflection_episode(
                user_goal=last_user_msg,
                plan=json.dumps(state.get("plan", [])),
                outcome=summary,
                learnings=str(data.get("value", "")),
            )

            # Record any discovered long-term user preference
            if data.get("has_preference") and data.get("key") and data.get("value"):
                memory_manager.store_fact(
                    key=data["key"],
                    value=data["value"],
                    category=data.get("category", "preference"),
                )
                logger.info("Reflection stored preference: %s = %s", data["key"], data["value"])

            return {"reflection": summary}
        except Exception as e:
            logger.debug("Reflection error: %s", e)
            return {"reflection": "Task concluded."}

    # ── Edge Decision ───────────────────────────────────────────
    def should_continue(state: AgentState) -> str:
        """Route to tools node if tool_calls present, otherwise to reflection."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "reflect"

    # ── Assemble StateGraph ─────────────────────────────────────
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("reflect", reflection_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "agent")
    workflow.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "reflect": "reflect",
    })
    workflow.add_edge("tools", "agent")
    workflow.add_edge("reflect", END)

    return workflow.compile(checkpointer=memory_manager.checkpointer)
