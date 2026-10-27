"""
FastAPI Backend Server for Firefly III AI Agent Level 2.

Exposes REST APIs for the React Frontend:
- POST /api/chat: Execute LangGraph cognition loops (Planning, ReAct, Reflection)
- GET /api/user: Authenticated Firefly III user profile
- GET /api/accounts: Financial accounts & balances
- GET /api/budgets: Budgets & spending tracking
- GET /api/piggy: Savings goals & progress
- GET /api/bills: Recurring obligations
- GET /api/memory: Agentic Long-term facts & reflection episodes
- POST /api/sync: Trigger Dynamic RAG incremental delta sync
"""

import logging
import os
import warnings
from pathlib import Path
from typing import Any, Optional

import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

# Filter fixed sampling warnings
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_google_genai")

from config import config, DATA_DIR
from api.firefly_client import FireflyClient
from tools.finance_tools import create_finance_tools
from rag.engine import DynamicRAGEngine
from memory.manager import MemoryManager
from agent.harness import AgentHarnessCallback
from agent.loops import create_agent_graph

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(DATA_DIR / "agent_api.log", encoding="utf-8")],
)
logger = logging.getLogger("firefly_agent_api")

app = FastAPI(title="Firefly III AI Agent API", version="2.0.0")

# Enable CORS for React dev server (port 5173 / any origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firefly client & core services
client = FireflyClient(config.FIREFLY_BASE_URL, config.FIREFLY_API_TOKEN)
memory_manager = MemoryManager(db_path=config.MEMORY_DB_PATH)
harness = AgentHarnessCallback(max_tool_retries=3)

# RAG Engine
rag_engine = DynamicRAGEngine(
    persist_directory=config.CHROMA_PERSIST_DIR,
    collection_name=config.RAG_COLLECTION_NAME,
    gemini_api_key=config.GEMINI_API_KEY,
    firefly_client=client,
)

# Tools
finance_tools = create_finance_tools(client)
retriever_tool = rag_engine.get_retriever_tool()
all_tools = finance_tools + [retriever_tool]

# Authenticated user info cache
cached_user: dict[str, Any] = {}
try:
    cached_user = client.get_current_user()
    logger.info("Authenticated as: %s (role: %s)", cached_user.get("email"), cached_user.get("role"))
except Exception as e:
    logger.warning("Could not pre-fetch user info: %s", e)

# LangGraph Agent Graph
agent_app = create_agent_graph(
    llm_model=config.LLM_MODEL,
    gemini_api_key=config.GEMINI_API_KEY,
    tools=all_tools,
    memory_manager=memory_manager,
    harness=harness,
    user_info=cached_user,
)


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "web_session_main"
    history: Optional[list[dict[str, Any]]] = None


class FactRequest(BaseModel):
    key: str
    value: str
    category: Optional[str] = "preference"


@app.get("/api/health")
def get_health() -> dict[str, Any]:
    """Check connectivity to Firefly III and Gemini, fetching current user dynamically."""
    global cached_user
    firefly_status = "connected"
    firefly_version = "unknown"
    current_user_data = cached_user

    try:
        about = client.get_about()
        firefly_version = about.get("version", "unknown")
        # Dynamically fetch current user from Firefly III
        fresh_user = client.get_current_user()
        if fresh_user and fresh_user.get("email"):
            cached_user = fresh_user
            current_user_data = fresh_user
    except Exception as e:
        firefly_status = f"offline: {e}"

    return {
        "status": "healthy",
        "firefly_status": firefly_status,
        "firefly_version": firefly_version,
        "model": config.LLM_MODEL,
        "user": current_user_data,
    }


@app.get("/api/user")
def get_user() -> dict[str, Any]:
    """Fetch logged-in Firefly III user details dynamically."""
    global cached_user
    try:
        user = client.get_current_user()
        if user and user.get("email"):
            cached_user = user
        return {"success": True, "user": user}
    except Exception as e:
        logger.error("Error fetching user: %s", e)
        return {"success": False, "error": str(e), "user": cached_user}


@app.get("/api/accounts")
def get_accounts() -> dict[str, Any]:
    """Fetch financial accounts and balances."""
    try:
        accounts = client.get_accounts()
        return {"success": True, "accounts": accounts}
    except Exception as e:
        logger.error("Error fetching accounts: %s", e)
        return {"success": False, "error": str(e), "accounts": []}


@app.get("/api/budgets")
def get_budgets() -> dict[str, Any]:
    """Fetch budgets and spent limits."""
    try:
        budgets = client.get_budgets()
        return {"success": True, "budgets": budgets}
    except Exception as e:
        logger.error("Error fetching budgets: %s", e)
        return {"success": False, "error": str(e), "budgets": []}


@app.get("/api/piggy")
def get_piggy_banks() -> dict[str, Any]:
    """Fetch savings goals."""
    try:
        piggies = client.get_piggy_banks()
        return {"success": True, "piggy_banks": piggies}
    except Exception as e:
        logger.error("Error fetching piggy banks: %s", e)
        return {"success": False, "error": str(e), "piggy_banks": []}


@app.get("/api/bills")
def get_bills() -> dict[str, Any]:
    """Fetch recurring bills and obligations."""
    try:
        bills = client.get_bills()
        return {"success": True, "bills": bills}
    except Exception as e:
        logger.error("Error fetching bills: %s", e)
        return {"success": False, "error": str(e), "bills": []}


@app.get("/api/memory")
def get_memory() -> dict[str, Any]:
    """Fetch long-term facts and recent reflection episodes."""
    try:
        facts = memory_manager.get_all_facts()
        episodes = memory_manager.get_recent_episodes(10)
        stats = memory_manager.get_stats()
        return {
            "success": True,
            "facts": facts,
            "episodes": episodes,
            "stats": stats,
        }
    except Exception as e:
        logger.error("Error fetching memory: %s", e)
        return {"success": False, "error": str(e)}


@app.post("/api/memory/fact")
def add_fact(req: FactRequest) -> dict[str, Any]:
    """Manually add or update a user preference rule."""
    try:
        memory_manager.store_fact(key=req.key, value=req.value, category=req.category or "preference")
        return {"success": True, "message": f"Rule '{req.key}' stored successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/sync")
def sync_rag() -> dict[str, Any]:
    """Trigger manual incremental delta sync with Firefly III."""
    try:
        count = rag_engine.sync_with_firefly()
        stats = rag_engine.get_stats()
        return {"success": True, "new_indexed": count, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_clean_ai_reply(content: Any) -> str:
    """Extract clean Markdown text from LLM response content, unwrapping list of parts/dicts."""
    if not content:
        return ""

    # Handle list of content parts
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            elif hasattr(part, "text"):
                parts.append(str(part.text))
            else:
                parts.append(str(part))
        return "\n\n".join(p for p in parts if p.strip())

    # Handle dict content
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        return str(content)

    # Handle string content that might be serialized dict/list
    if isinstance(content, str):
        trimmed = content.strip()
        if (trimmed.startswith("{'type': 'text'") or trimmed.startswith('{"type": "text"')) and "'text':" in trimmed:
            try:
                import ast
                parsed = ast.literal_eval(trimmed)
                if isinstance(parsed, dict) and "text" in parsed:
                    return str(parsed["text"])
            except Exception:
                pass
        return content

    return str(content)


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """Stream LangGraph agent execution tokens live via Server-Sent Events (SSE)."""
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    harness.reset()
    target_thread_id = req.thread_id.strip() if req.thread_id and req.thread_id.strip() else "web_session_main"
    thread_config = {"configurable": {"thread_id": target_thread_id}}

    # Check if thread already has checkpointed messages in LangGraph
    existing_state = None
    try:
        existing_state = agent_app.get_state(thread_config)
    except Exception as state_err:
        logger.debug("Could not read thread state: %s", state_err)

    messages_to_send = []
    # If thread is brand new in memory, but frontend provided history, reconstruct context
    if (not existing_state or not existing_state.values or not existing_state.values.get("messages")) and req.history:
        for item in req.history:
            role = item.get("role")
            content = item.get("content", "")
            if not content:
                continue
            if role == "user":
                messages_to_send.append(HumanMessage(content=content))
            elif role == "assistant":
                messages_to_send.append(AIMessage(content=content))

    messages_to_send.append(HumanMessage(content=user_msg))

    initial_state = {
        "messages": messages_to_send,
        "plan": [],
        "is_complex": False,
        "reflection": "",
    }

    def sse_event_generator():
        emitted_actions = 0
        final_plan = []
        final_is_complex = False
        final_reflection = ""
        streamed_tokens = []

        try:
            for mode, payload in agent_app.stream(
                initial_state,
                config=thread_config,
                stream_mode=["messages", "updates"],
            ):
                # 1. State updates from nodes (planner, tools, reflect)
                if mode == "updates" and isinstance(payload, dict):
                    if "planner" in payload:
                        planner_data = payload["planner"]
                        final_plan = planner_data.get("plan", [])
                        final_is_complex = planner_data.get("is_complex", False)
                        plan_event = {
                            "type": "plan",
                            "plan": final_plan,
                            "is_complex": final_is_complex,
                        }
                        yield f"data: {json.dumps(plan_event, ensure_ascii=False)}\n\n"

                    if "reflect" in payload:
                        final_reflection = payload["reflect"].get("reflection", "")

                    # Flush tool executions from harness
                    current_actions = list(harness.action_history)
                    while emitted_actions < len(current_actions):
                        act = current_actions[emitted_actions]
                        yield f"data: {json.dumps({'type': 'action', 'action': act}, ensure_ascii=False)}\n\n"
                        emitted_actions += 1

                # 2. Token-by-token message chunks from the agent node
                elif mode == "messages":
                    msg, meta = payload
                    node = meta.get("langgraph_node")
                    if node == "agent":
                        # If this chunk is a tool call, do not stream JSON as text
                        if getattr(msg, "tool_call_chunks", None) or getattr(msg, "tool_calls", None):
                            continue

                        token_text = ""
                        if isinstance(msg.content, str):
                            token_text = msg.content
                        elif isinstance(msg.content, list):
                            parts = []
                            for p in msg.content:
                                if isinstance(p, str):
                                    parts.append(p)
                                elif isinstance(p, dict) and "text" in p:
                                    parts.append(str(p["text"]))
                            token_text = "".join(parts)

                        if token_text:
                            streamed_tokens.append(token_text)
                            token_event = {
                                "type": "token",
                                "content": token_text,
                            }
                            yield f"data: {json.dumps(token_event, ensure_ascii=False)}\n\n"

            # Flush any remaining tool executions
            current_actions = list(harness.action_history)
            while emitted_actions < len(current_actions):
                act = current_actions[emitted_actions]
                yield f"data: {json.dumps({'type': 'action', 'action': act}, ensure_ascii=False)}\n\n"
                emitted_actions += 1

            # Delta sync if any transaction was mutated
            mutation_tools = {"create_transaction", "create_transfer", "create_deposit", "delete_transaction"}
            for act in current_actions:
                if act.get("tool", "") in mutation_tools:
                    try:
                        rag_engine.sync_with_firefly()
                    except Exception as sync_err:
                        logger.warning("Auto sync error: %s", sync_err)
                    break

            # Send done event with complete summary and concatenated reply
            done_event = {
                "type": "done",
                "reply": "".join(streamed_tokens),
                "reflection": final_reflection,
                "actions": current_actions,
                "plan": final_plan,
                "is_complex": final_is_complex,
            }
            yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("Error in streaming chat")
            err_event = {
                "type": "error",
                "error": str(e),
                "reply": f"Maaf, terjadi kesalahan saat memproses permintaan: {e}",
            }
            yield f"data: {json.dumps(err_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    """Execute LangGraph cognitive loops for user request."""
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    harness.reset()
    target_thread_id = req.thread_id.strip() if req.thread_id and req.thread_id.strip() else "web_session_main"
    thread_config = {"configurable": {"thread_id": target_thread_id}}

    existing_state = None
    try:
        existing_state = agent_app.get_state(thread_config)
    except Exception as state_err:
        logger.debug("Could not read thread state: %s", state_err)

    messages_to_send = []
    if (not existing_state or not existing_state.values or not existing_state.values.get("messages")) and req.history:
        for item in req.history:
            role = item.get("role")
            content = item.get("content", "")
            if not content:
                continue
            if role == "user":
                messages_to_send.append(HumanMessage(content=content))
            elif role == "assistant":
                messages_to_send.append(AIMessage(content=content))

    messages_to_send.append(HumanMessage(content=user_msg))

    initial_state = {
        "messages": messages_to_send,
        "plan": [],
        "is_complex": False,
        "reflection": "",
    }

    try:
        result = agent_app.invoke(initial_state, config=thread_config)

        # Extract final AI response
        messages = result.get("messages", [])
        reply_content = ""
        for m in reversed(messages):
            if hasattr(m, "content") and m.content and not getattr(m, "tool_calls", None):
                reply_content = extract_clean_ai_reply(m.content)
                break

        plan = result.get("plan", [])
        is_complex = result.get("is_complex", False)
        reflection = result.get("reflection", "")
        actions = list(harness.action_history)

        # Delta sync ONLY when a transaction was actually mutated (created, transferred, deposited, deleted)
        mutation_tools = {"create_transaction", "create_transfer", "create_deposit", "delete_transaction"}
        for act in actions:
            if act.get("tool", "") in mutation_tools:
                try:
                    rag_engine.sync_with_firefly()
                except Exception as sync_err:
                    logger.warning("Auto sync error: %s", sync_err)
                break

        return {
            "success": True,
            "reply": reply_content or "Action completed.",
            "plan": plan,
            "is_complex": is_complex,
            "actions": actions,
            "reflection": reflection,
        }

    except Exception as e:
        logger.exception("Error executing agent chat")
        return {
            "success": False,
            "error": str(e),
            "reply": f"Maaf, terjadi kesalahan saat memproses permintaan: {e}",
            "actions": list(harness.action_history),
        }


# Mount built React static files if frontend/dist exists
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting Firefly III AI Agent Web Server on http://localhost:8000 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
