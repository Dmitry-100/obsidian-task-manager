"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


# Get the path to config/.env (relative to this file)
# This file is at: src/core/config.py
# .env is at: config/.env
# So we need to go: src/core/ -> src/ -> project_root/ -> config/
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Go up to project root
ENV_FILE = BASE_DIR / "config" / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/obsidian_tasks"
    DATABASE_ECHO: bool = False  # Log SQL queries

    # Application
    APP_NAME: str = "Obsidian Task Manager"
    DEBUG: bool = False

    # Authentication
    # API Key для авторизации запросов
    # В продакшене ОБЯЗАТЕЛЬНО установить через переменную окружения!
    API_KEY: str = "dev-api-key-change-in-production"

    # Obsidian integration
    OBSIDIAN_VAULT_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Create global settings instance
settings = Settings()
