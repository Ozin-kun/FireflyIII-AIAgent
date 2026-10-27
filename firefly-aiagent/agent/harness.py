"""
Agent Harness Callback for LangGraph.

Provides lifecycle state management, execution hooks, observability logging,
and circuit-breaker error handling.
"""

import logging
from typing import Any
from langchain_core.callbacks import BaseCallbackHandler
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class AgentHarnessCallback(BaseCallbackHandler):
    """Harness callback implementing observability hooks and circuit breaker."""

    def __init__(self, max_tool_retries: int = 3) -> None:
        super().__init__()
        self.max_tool_retries = max_tool_retries
        self.action_history: list[dict[str, Any]] = []
        self.tool_error_counts: dict[str, int] = {}
        self.current_state: str = "IDLE"

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Hook triggered before LLM reasoning begins."""
        self.current_state = "THINKING"
        logger.debug("Harness State -> THINKING")

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Pre-execution hook: validates circuit breaker and logs tool invocation."""
        tool_name = serialized.get("name", "unknown_tool")
        self.current_state = "ACTING"

        # Check circuit breaker limit
        err_count = self.tool_error_counts.get(tool_name, 0)
        if err_count >= self.max_tool_retries:
            console.print(f"[bold red]⚠️ Circuit Breaker Active:[/] Tool '{tool_name}' has failed {err_count} times.")
            logger.warning("Tool '%s' reached circuit breaker threshold.", tool_name)
            raise RuntimeError(
                f"Circuit Breaker Tripped: Tool '{tool_name}' has exceeded maximum allowed retries ({self.max_tool_retries}). "
                f"Execution blocked to prevent infinite loops. Please choose an alternative tool or inform the user."
            )

        console.print(f"[bold yellow]🔧 Tool Action:[/] [cyan]{tool_name}[/] with input: {input_str}")
        self.action_history.append({
            "tool": tool_name,
            "input": input_str,
            "status": "started",
        })

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Post-execution hook: logs clean observation preview."""
        self.current_state = "OBSERVING"
        preview = output[:250] + "..." if len(output) > 250 else output
        console.print(f"[bold green]📊 Tool Observation:[/] {preview}")

        if self.action_history:
            self.action_history[-1]["status"] = "success"
            self.action_history[-1]["output"] = preview

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Error hook: records failure and increments circuit breaker counter."""
        self.current_state = "ERROR"
        tool_name = self.action_history[-1]["tool"] if self.action_history else "unknown"
        self.tool_error_counts[tool_name] = self.tool_error_counts.get(tool_name, 0) + 1

        console.print(f"[bold red]❌ Tool Error ({tool_name}):[/] {error}")
        logger.error("Error executing tool %s: %s", tool_name, error)

        if self.action_history:
            self.action_history[-1]["status"] = "error"
            self.action_history[-1]["error"] = str(error)

    def reset(self) -> None:
        """Reset transient history and counters for a new user request."""
        self.action_history.clear()
        self.tool_error_counts.clear()
        self.current_state = "IDLE"
