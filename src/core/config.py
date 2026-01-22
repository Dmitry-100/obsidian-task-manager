"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the path to config/.env (relative to this file)
# This file is at: src/core/config.py
# .env is at: config/.env
# So we need to go: src/core/ -> src/ -> project_root/ -> config/
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Go up to project root
ENV_FILE = BASE_DIR / "config" / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Все настройки можно переопределить через переменные окружения.
    Пример: DATABASE_URL=postgresql://... uvicorn src.main:app
    """

    # =========================================================================
    # Database
    # =========================================================================
    # DATABASE_URL - строка подключения к базе данных
    # Формат: postgresql+asyncpg://user:password@host:port/database
    # Для SQLite: sqlite+aiosqlite:///./database.db
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/obsidian_tasks"

    # DATABASE_ECHO - выводить SQL запросы в логи (для отладки)
    DATABASE_ECHO: bool = False

    # =========================================================================
    # Application
    # =========================================================================
    APP_NAME: str = "Obsidian Task Manager"
    DEBUG: bool = False

    # =========================================================================
    # Logging
    # =========================================================================
    # LOG_LEVEL - уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL
    # DEBUG - самый подробный, CRITICAL - только критические ошибки
    LOG_LEVEL: str = "INFO"

    # LOG_FORMAT - формат логов:
    # "json" - структурированный JSON (для production, легко парсить)
    # "simple" - человекочитаемый текст (для разработки)
    LOG_FORMAT: str = "json"

    # =========================================================================
    # Authentication
    # =========================================================================
    # API_KEY - ключ для авторизации запросов
    # В продакшене ОБЯЗАТЕЛЬНО установить через переменную окружения!
    API_KEY: str = "dev-api-key-change-in-production"

    # =========================================================================
    # Obsidian integration
    # =========================================================================
    # OBSIDIAN_VAULT_PATH - путь к Obsidian vault для синхронизации
    OBSIDIAN_VAULT_PATH: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE), env_file_encoding="utf-8", case_sensitive=True
    )


# Create global settings instance
settings = Settings()
