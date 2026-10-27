"""
Main CLI Interface for Firefly III AI Agent Level 2.

Integrates all components:
- Loop Engineering (LangGraph StateGraph: Planning, ReAct, Reflection)
- Dynamic RAG (ChromaDB Vector Store with Delta Indexing)
- Agentic Memory (SQLite Long-Term Facts + Checkpointer)
- Agent Harness (Lifecycle Hooks & Circuit Breaker)
- Firefly III Full Toolkit (Accounts, Transactions, Budgets, Piggy Banks, Bills, Categories)
"""

import sys
import logging
import warnings
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from langchain_core.messages import HumanMessage

# Suppress fixed sampling warning from langchain_google_genai
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
    handlers=[logging.FileHandler(DATA_DIR / "agent.log", encoding="utf-8")],
)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

console = Console()


def display_banner() -> None:
    """Display startup welcome banner."""
    console.print(
        Panel.fit(
            "[bold cyan]🤖 Firefly III AI Agent (Level 2)[/bold cyan]\n"
            "[dim]Powered by LangChain & LangGraph | Google Gemini | ChromaDB Vector Store[/dim]\n\n"
            "✨ [bold green]Dynamic RAG[/] | [bold purple]Agentic Memory[/] | "
            "[bold yellow]Agent Harness[/] | [bold blue]Loop Engineering[/]\n\n"
            "Type [bold yellow]/help[/] for command list, or ask anything about your finances.",
            title="Firefly III Autonomous Assistant",
            border_style="cyan",
        )
    )


def display_help() -> None:
    """Display available terminal diagnostic commands."""
    table = Table(title="Available Terminal Commands", border_style="cyan")
    table.add_column("Command", style="bold yellow")
    table.add_column("Description")
    table.add_row("/help", "Show this list of commands")
    table.add_row("/whoami", "Display currently authenticated user profile")
    table.add_row("/accounts", "Quick inspect all financial accounts & balances")
    table.add_row("/budgets", "Quick inspect all budgets, limits & spending")
    table.add_row("/piggy", "Quick inspect all savings goals (piggy banks)")
    table.add_row("/bills", "Quick inspect recurring bills & subscriptions")
    table.add_row("/rag", "Display RAG index statistics")
    table.add_row("/sync", "Trigger dynamic delta sync with Firefly III")
    table.add_row("/memory", "Display Long-Term Facts and Episodic Reflections")
    table.add_row("/rule <key> <val>", "Teach agent a persistent rule/preference manually")
    table.add_row("/exit or /quit", "Exit the assistant")
    console.print(table)


def main() -> None:
    display_banner()

    # Validate configuration
    errors = config.validate()
    if errors:
        console.print("\n[bold red]⚠️ Configuration Check:[/]")
        for err in errors:
            console.print(f"  [red]• {err}[/]")

    console.print("\n[dim]Connecting to Firefly III...[/dim]")
    client = FireflyClient(config.FIREFLY_BASE_URL, config.FIREFLY_API_TOKEN)
    try:
        about = client.get_about()
        version = about.get("version", "unknown")
        console.print(f"[green]✓ Connected to Firefly III (v{version}) at {config.FIREFLY_BASE_URL}[/]")
    except Exception as e:
        err_str = str(e)
        console.print(f"[bold red]✗ Cannot reach Firefly III at {config.FIREFLY_BASE_URL}:[/] {err_str}")

        if "401" in err_str or "Unauthenticated" in err_str:
            console.print(
                Panel(
                    "[bold yellow]Firefly III is running, but the API Token is missing or invalid![/]\n\n"
                    "Untuk mendapatkan Personal Access Token:\n"
                    "1. Buka browser: [link=http://localhost:8085]http://localhost:8085[/link]\n"
                    "2. Login ke akun Anda, lalu klik menu [bold]Profile[/] (kanan atas) atau buka [link=http://localhost:8085/profile]http://localhost:8085/profile[/link]\n"
                    "3. Klik tab [bold]OAuth[/] -> [bold]Personal Access Tokens[/]\n"
                    "4. Klik tombol [bold]Create New Token[/], beri nama (misal: 'AI-Agent'), lalu copy token yang muncul.\n"
                    "5. Buka berkas [bold]firefly-aiagent/.env[/bold] dan ganti nilai [bold]FIREFLY_API_TOKEN[/bold].",
                    title="Petunjuk Autentikasi Firefly III",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel(
                    "[bold yellow]Ingin menguji tanpa Docker atau Firefly offline?[/]\n\n"
                    "Jalankan emulator lokal mock server di terminal terpisah:\n"
                    "   [bold green]python mock_firefly.py[/bold green]\n\n"
                    "Lalu pastikan [bold]FIREFLY_BASE_URL=http://localhost:8080[/bold] pada berkas .env Anda.",
                    title="Opsi Local Mock Server",
                    border_style="yellow",
                )
            )
        sys.exit(1)

    # Fetch authenticated user profile
    current_user = {}
    try:
        current_user = client.get_current_user()
        user_email = current_user.get("email", "unknown")
        user_role = current_user.get("role", "owner")
        console.print(f"[green]✓ Authenticated as: [bold cyan]{user_email}[/] (Role: {user_role})[/]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not fetch user profile: {e}[/]")

    console.print("[dim]Initializing RAG, Memory, and Tools...[/dim]")
    # 1. RAG Engine
    rag_engine = DynamicRAGEngine(
        persist_directory=config.CHROMA_PERSIST_DIR,
        collection_name=config.RAG_COLLECTION_NAME,
        gemini_api_key=config.GEMINI_API_KEY,
        firefly_client=client,
    )
    try:
        new_indexed = rag_engine.sync_with_firefly()
        console.print(f"[green]✓ Dynamic RAG: Synced {new_indexed} transactions into ChromaDB.[/]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Initial RAG sync notice: {e}[/]")

    # 2. Memory Manager
    memory_manager = MemoryManager(db_path=config.MEMORY_DB_PATH)
    console.print("[green]✓ Agentic Memory: SQLite Long-Term store & Checkpointer ready.[/]")

    # 3. Tools
    finance_tools = create_finance_tools(client)
    retriever_tool = rag_engine.get_retriever_tool()
    all_tools = finance_tools + [retriever_tool]
    console.print(f"[green]✓ Tools: Loaded {len(all_tools)} tools (including user profile & semantic RAG).[/]")

    # 4. Agent Harness
    harness = AgentHarnessCallback(max_tool_retries=3)
    console.print("[green]✓ Agent Harness: Lifecycle hooks and circuit breaker active.[/]")

    # 5. LangGraph Agent Graph (Loop Engineering)
    app = create_agent_graph(
        llm_model=config.LLM_MODEL,
        gemini_api_key=config.GEMINI_API_KEY,
        tools=all_tools,
        memory_manager=memory_manager,
        harness=harness,
        user_info=current_user,
    )
    console.print("[green]✓ Loop Engineering: LangGraph StateGraph compiled with user identity.[/]")

    thread_config = {"configurable": {"thread_id": "session_user_main"}}
    console.print("\n[bold green]Ready! Ask me anything about your finances.[/]\n")

    # ── Interactive Chat Loop ─────────────────────────────────────
    while True:
        try:
            user_input = console.input("[bold green]You:[/] ").strip()
            if not user_input:
                continue

            # Command Handling
            if user_input.startswith("/"):
                cmd_parts = user_input.split(maxsplit=2)
                cmd = cmd_parts[0].lower()

                if cmd in ("/exit", "/quit"):
                    console.print("[cyan]👋 Goodbye! Take care of your finances.[/]")
                    break
                elif cmd == "/help":
                    display_help()
                elif cmd == "/whoami":
                    try:
                        u = client.get_current_user()
                        console.print(
                            Panel(
                                f"[bold cyan]User Email:[/] {u.get('email', 'N/A')}\n"
                                f"[bold cyan]Role:[/] {u.get('role', 'N/A')}\n"
                                f"[bold cyan]User ID:[/] {u.get('id', 'N/A')}\n"
                                f"[bold cyan]Account Status:[/] {'Blocked' if u.get('blocked') else 'Active'}",
                                title="👤 Current Authenticated User",
                                border_style="cyan",
                            )
                        )
                    except Exception as e:
                        console.print(f"[red]Error retrieving user profile: {e}[/]")
                elif cmd == "/accounts":
                    accounts = client.get_accounts()
                    table = Table(title="Financial Accounts", border_style="cyan")
                    table.add_column("ID", style="bold")
                    table.add_column("Name")
                    table.add_column("Type")
                    table.add_column("Balance")
                    for a in accounts:
                        table.add_row(
                            str(a["id"]),
                            a["name"],
                            a["type"],
                            f"{a.get('currency_symbol', '')}{a['current_balance']} {a.get('currency_code', '')}",
                        )
                    console.print(table)
                elif cmd == "/budgets":
                    budgets = client.get_budgets()
                    table = Table(title="Budgets & Limits", border_style="cyan")
                    table.add_column("ID", style="bold")
                    table.add_column("Name")
                    table.add_column("Limit")
                    table.add_column("Spent")
                    for b in budgets:
                        table.add_row(
                            str(b["id"]),
                            b["name"],
                            f"Rp{b.get('auto_budget_amount', '0')}/{b.get('auto_budget_period', 'monthly')}",
                            f"Rp{b.get('spent', '0')}",
                        )
                    console.print(table)
                elif cmd == "/piggy":
                    piggies = client.get_piggy_banks()
                    table = Table(title="Savings Goals (Piggy Banks)", border_style="magenta")
                    table.add_column("ID", style="bold")
                    table.add_column("Goal Name")
                    table.add_column("Saved")
                    table.add_column("Target")
                    table.add_column("Progress")
                    for p in piggies:
                        table.add_row(
                            str(p["id"]),
                            p["name"],
                            f"Rp{p.get('current_amount', '0')}",
                            f"Rp{p.get('target_amount', '0')}",
                            f"{p.get('percentage', 0)}%",
                        )
                    console.print(table)
                elif cmd == "/bills":
                    bills = client.get_bills()
                    table = Table(title="Recurring Bills", border_style="yellow")
                    table.add_column("ID", style="bold")
                    table.add_column("Bill Name")
                    table.add_column("Amount Range")
                    table.add_column("Frequency")
                    table.add_column("Next Due")
                    for b in bills:
                        table.add_row(
                            str(b["id"]),
                            b["name"],
                            f"Rp{b.get('amount_min', '0')} - Rp{b.get('amount_max', '0')}",
                            b.get("repeat_freq", "monthly"),
                            b.get("next_expected_match", "N/A"),
                        )
                    console.print(table)
                elif cmd == "/rag":
                    stats = rag_engine.get_stats()
                    table = Table(title="Dynamic RAG Statistics", border_style="cyan")
                    for k, v in stats.items():
                        table.add_row(k, str(v))
                    console.print(table)
                elif cmd == "/sync":
                    console.print("[dim]Syncing latest transactions with Firefly III...[/dim]")
                    added = rag_engine.sync_with_firefly()
                    console.print(f"[bold green]✓ Synced {added} new transaction(s).[/]")
                elif cmd == "/memory":
                    stats = memory_manager.get_stats()
                    console.print(f"[bold purple]🧠 Memory Stats:[/] {stats}")
                    facts = memory_manager.get_all_facts()
                    if facts:
                        table = Table(title="Long-Term Rules & Preferences", border_style="purple")
                        table.add_column("Key", style="bold")
                        table.add_column("Value")
                        table.add_column("Category")
                        for f in facts:
                            table.add_row(f["key"], f["value"], f["category"])
                        console.print(table)
                    episodes = memory_manager.get_recent_episodes(3)
                    if episodes:
                        console.print("\n[bold purple]Recent Episodes / Reflections:[/]")
                        for ep in episodes:
                            console.print(f"• [cyan]{ep['user_goal'][:60]}[/] -> [dim]{ep['outcome']}[/]")
                elif cmd == "/rule" and len(cmd_parts) >= 3:
                    rule_key = cmd_parts[1]
                    rule_val = cmd_parts[2]
                    memory_manager.store_fact(key=rule_key, value=rule_val, category="rule")
                    console.print(f"[bold green]✓ Stored rule:[/] {rule_key} = {rule_val}")
                else:
                    console.print(f"[red]Unknown command: {cmd}. Type /help for options.[/]")
                continue

            # Execute via LangGraph Loop Engineering
            harness.reset()
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "plan": [],
                "is_complex": False,
                "reflection": "",
            }

            result = app.invoke(initial_state, config=thread_config)

            # Display plan if task is complex
            plan_steps = result.get("plan", [])
            if plan_steps and result.get("is_complex"):
                plan_rendered = "\n".join(f"[bold yellow]{i+1}.[/] {step}" for i, step in enumerate(plan_steps))
                console.print(
                    Panel(
                        plan_rendered,
                        title="📋 Autonomous Execution Plan",
                        subtitle="Planning Loop Decomposed Task",
                        border_style="yellow",
                    )
                )

            # Extract final message from agent
            messages = result.get("messages", [])
            final_content = ""
            for m in reversed(messages):
                if hasattr(m, "content") and m.content and not getattr(m, "tool_calls", None):
                    if isinstance(m.content, str):
                        final_content = m.content
                    elif isinstance(m.content, list):
                        final_content = " ".join(str(part) for part in m.content)
                    break

            console.print("\n[bold cyan]🤖 Assistant:[/]")
            console.print(Markdown(final_content or "Action completed."))

            # Auto trigger dynamic RAG delta update if transactions were created
            for action in harness.action_history:
                if "transaction" in action.get("tool", ""):
                    rag_engine.sync_with_firefly()
                    break

            console.print()

        except KeyboardInterrupt:
            console.print("\n[cyan]👋 Session ended.[/]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error: {e}[/]")
            logging.exception("Unhandled error in main loop")


if __name__ == "__main__":
    main()
