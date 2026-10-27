"""
Agentic Memory System for Firefly III AI Agent.

Implements multi-tiered memory:
1. Short-Term & Episodic: LangGraph Checkpointer (MemorySaver).
2. Long-Term Facts & Preferences: SQLite database (long_term_facts).
3. Reflection Episodes: SQLite database (reflection_episodes).
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages persistent SQLite memory and LangGraph checkpointer."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()
        # In-memory LangGraph checkpointer for conversation session state
        self.checkpointer = MemorySaver()

    def _init_db(self) -> None:
        """Initialize SQLite tables for long-term facts and reflection episodes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS long_term_facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'preference',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reflection_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_goal TEXT NOT NULL,
                    plan TEXT,
                    outcome TEXT NOT NULL,
                    learnings TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def store_fact(self, key: str, value: str, category: str = "preference") -> None:
        """Store or update a user financial fact, preference, or rule."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO long_term_facts (key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    category=excluded.category,
                    updated_at=excluded.updated_at
            """, (key, value, category, now, now))
            conn.commit()
            logger.info("Stored fact [%s]: %s (%s)", key, value, category)

    def get_all_facts(self) -> list[dict[str, Any]]:
        """Retrieve all long-term facts and user preferences."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, category, updated_at FROM long_term_facts ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_formatted_facts(self) -> str:
        """Format all stored long-term facts as a string for prompt injection."""
        facts = self.get_all_facts()
        if not facts:
            return "No prior user preferences or financial rules recorded yet."
        lines = ["User Preferences & Financial Rules (Long-Term Memory):"]
        for f in facts:
            lines.append(f"- [{f['category'].upper()}] {f['key']}: {f['value']}")
        return "\n".join(lines)

    def save_reflection_episode(
        self,
        user_goal: str,
        plan: str,
        outcome: str,
        learnings: str,
    ) -> None:
        """Record an episodic reflection after completing a task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reflection_episodes (user_goal, plan, outcome, learnings)
                VALUES (?, ?, ?, ?)
            """, (user_goal, plan, outcome, learnings))
            conn.commit()
            logger.info("Saved reflection episode for goal: %s", user_goal[:50])

    def get_recent_episodes(self, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve recent episodic interaction reflections."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, user_goal, plan, outcome, learnings, created_at FROM reflection_episodes ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the agent memory system."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM long_term_facts")
            total_facts = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM reflection_episodes")
            total_episodes = cursor.fetchone()[0]
            return {
                "total_long_term_facts": total_facts,
                "total_episodes": total_episodes,
                "db_path": self.db_path,
            }
