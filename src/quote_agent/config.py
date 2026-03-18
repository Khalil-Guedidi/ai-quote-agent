"""Centralized type-safe configuration system using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """PostgreSQL database configuration."""

    url: str
    echo: bool = False

    @field_validator("url")
    @classmethod
    def url_must_be_postgresql(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            msg = "DATABASE__URL must start with 'postgresql://' or 'postgresql+asyncpg://'"
            raise ValueError(msg)
        return v


class LLMSettings(BaseModel):
    """LLM provider configuration."""

    api_key: SecretStr
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"
    simple_model: str = "gpt-4o-mini"
    complex_model: str = "gpt-4o"
    timeout: int = 60
    max_retries: int = 3


class ERPSettings(BaseModel):
    """Odoo ERP connection configuration."""

    url: str
    database: str
    username: str
    api_key: SecretStr


class EmailSettings(BaseModel):
    """Email IMAP configuration."""

    imap_server: str
    imap_port: int = 993
    username: str
    password: SecretStr
    folder: str = "INBOX"
    poll_interval: int = 60


class NotificationSettings(BaseModel):
    """Notification channel configuration."""

    channel: str = "teams"
    teams_webhook_url: str = ""


class AppSettings(BaseModel):
    """Application-level configuration."""

    name: str = "ai-quote-agent"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000


class Settings(BaseSettings):
    """Root settings — loads from .env with __ as nested delimiter."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
    )

    database: DatabaseSettings
    llm: LLMSettings
    erp: ERPSettings
    email: EmailSettings
    notification: NotificationSettings = NotificationSettings()
    app: AppSettings = AppSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Create and return a validated Settings instance (cached singleton)."""
    return Settings()


def __getattr__(name: str) -> Any:
    """Lazy module attribute — ``from quote_agent.config import settings``."""
    if name == "settings":
        return get_settings()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
