"""Centralized type-safe configuration system using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator
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

    @field_validator("default_model", "simple_model", "complex_model")
    @classmethod
    def model_name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            msg = "Model name must not be empty"
            raise ValueError(msg)
        return v


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


class EmbeddingSettings(BaseModel):
    """Embedding model configuration."""

    model_name: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    batch_size: int = 64
    device: str = "cpu"


class ProposabilitySettings(BaseModel):
    """Proposability filter rules — which products can be proposed to clients."""

    exclude_out_of_stock: bool = True
    exclude_inactive: bool = True
    excluded_categories: list[str] = Field(default_factory=list)


class SearchCacheSettings(BaseModel):
    """Search result cache settings."""

    enabled: bool = True
    ttl_seconds: int = 3600
    max_entries: int = 10_000


class ClassificationSettings(BaseModel):
    """Complexity classification configuration."""

    timeout_seconds: int = 10
    fallback_complexity: Literal["simple", "ambiguous", "complex", "out_of_scope"] = "complex"


class ConfidenceScoringSettings(BaseModel):
    """Confidence scoring and tier routing configuration."""

    timeout_seconds: int = 10
    high_threshold: float = 0.85
    low_threshold: float = 0.50
    max_proposals: int = 5
    min_proposals: int = 2
    fallback_tier: Literal["high", "medium", "low"] = "low"


class ReasoningSettings(BaseModel):
    """Adaptive reasoning strategy configuration."""

    timeout_seconds: int = 15
    simple_search_limit: int = 5
    ambiguous_search_limit: int = 10
    complex_search_limit: int = 15


class SearchSettings(BaseModel):
    """Hybrid search configuration."""

    default_limit: int = 10
    semantic_weight: float = 0.5  # Reserved for future weighted RRF variant (not yet used)
    keyword_weight: float = 0.5  # Reserved for future weighted RRF variant (not yet used)
    rrf_k: int = 60
    hnsw_ef_search: int = 100


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
        extra="ignore",
    )

    database: DatabaseSettings
    llm: LLMSettings
    erp: ERPSettings
    email: EmailSettings
    notification: NotificationSettings = NotificationSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    classification: ClassificationSettings = ClassificationSettings()
    confidence_scoring: ConfidenceScoringSettings = ConfidenceScoringSettings()
    reasoning: ReasoningSettings = ReasoningSettings()
    search: SearchSettings = SearchSettings()
    search_cache: SearchCacheSettings = SearchCacheSettings()
    proposability: ProposabilitySettings = ProposabilitySettings()
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
