"""
Central Configuration Module.

Loads environment variables, defines folder paths for SQLite and ChromaDB,
and provides configuration validation.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file with override enabled
load_dotenv(override=True)

# Project directory paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    """Application configuration singleton."""

    # Project directory paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR

    # Firefly III API Settings
    FIREFLY_BASE_URL: str = os.getenv("FIREFLY_BASE_URL", "http://localhost:8085").rstrip("/")
    FIREFLY_API_TOKEN: str = os.getenv("FIREFLY_API_TOKEN", "")

    # Google Gemini LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")

    # Agentic Memory Database Path
    MEMORY_DB_PATH: str = str(DATA_DIR / "memory.db")

    def validate(self) -> list[str]:
        """Validate required configurations and return missing item warnings."""
        errors = []
        if not self.FIREFLY_API_TOKEN:
            errors.append("FIREFLY_API_TOKEN is not set in .env")
        if not self.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set in .env")
        return errors


config = Config()
