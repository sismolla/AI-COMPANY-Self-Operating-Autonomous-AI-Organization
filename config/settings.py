"""Centralized configuration for AI-COMPANY."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Base root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except Exception:
    pass

class Settings(BaseModel):
    """Application settings with environment variable overrides."""
    
    PROJECT_NAME: str = "AI-COMPANY"
    VERSION: str = "1.0.0"
    BASE_DIR: Path = BASE_DIR
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Storage paths
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "data" / "company.db"
    TOOLS_DIR: Path = BASE_DIR / "tools_data"
    WORKSPACE_DIR: Path = BASE_DIR / "workspace"
    CONFIG_DIR: Path = BASE_DIR / "config"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'company.db'}")
    
    # Task Queue / Redis
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)
    USE_IN_MEMORY_QUEUE: bool = os.getenv("USE_IN_MEMORY_QUEUE", "true").lower() in ("true", "1", "yes")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")  # 'mock', 'openai', 'gemini', 'anthropic', 'ollama'
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", None)
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Web Dashboard Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Tool Sandbox & Safety
    SANDBOX_TIMEOUT_SECONDS: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "15"))
    MAX_TOOL_EXECUTION_TIME: int = int(os.getenv("MAX_TOOL_EXECUTION_TIME", "30"))
    MAX_RETRIES: int = 3
    TASK_TIMEOUT_SECONDS: int = 120

    # Autonomous Orchestration Loop
    SCHEDULER_INTERVAL_SECONDS: int = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "10"))
    AUTONOMOUS_CYCLE_INTERVAL_SECONDS: int = int(os.getenv("AUTONOMOUS_CYCLE_INTERVAL_SECONDS", "15"))
    AUTO_CYCLE_ENABLED: bool = os.getenv("AUTO_CYCLE_ENABLED", "true").lower() in ("true", "1", "yes")

    # Multi-Platform Operations (Telegram, LinkedIn, Facebook)
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", None)
    TELEGRAM_CHANNEL_ID: Optional[str] = os.getenv("TELEGRAM_CHANNEL_ID", None)
    TELEGRAM_GROUP_ID: Optional[str] = os.getenv("TELEGRAM_GROUP_ID", None)

    LINKEDIN_ACCESS_TOKEN: Optional[str] = os.getenv("LINKEDIN_ACCESS_TOKEN", None)
    LINKEDIN_AUTHOR_URN: Optional[str] = os.getenv("LINKEDIN_AUTHOR_URN", None)

    FACEBOOK_PAGE_ACCESS_TOKEN: Optional[str] = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", None)
    FACEBOOK_PAGE_ID: Optional[str] = os.getenv("FACEBOOK_PAGE_ID", None)

    def ensure_directories(self) -> None:
        """Create necessary data, tools, and workspace directories."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        for role in ["director", "engineering", "research", "marketing", "analytics", "operations", "quality"]:
            (self.WORKSPACE_DIR / role).mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = Settings()
settings.ensure_directories()
