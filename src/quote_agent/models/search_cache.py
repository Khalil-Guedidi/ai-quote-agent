"""SQLAlchemy model for the search_cache table."""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: TC003 — SQLAlchemy needs runtime access for Mapped[datetime]

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from quote_agent.models.base import Base, TimestampMixin


class SearchCache(Base, TimestampMixin):
    """Cached search results with TTL-based expiration."""

    __tablename__ = "search_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    cache_key: Mapped[str] = mapped_column(String(64))
    query: Mapped[str] = mapped_column(Text)
    search_params: Mapped[dict[str, object]] = mapped_column(JSONB)
    results_json: Mapped[dict[str, object]] = mapped_column(JSONB)
    expires_at: Mapped[datetime]

    __table_args__ = (
        Index("ix_search_cache_cache_key", "cache_key", unique=True),
        Index("ix_search_cache_expires_at", "expires_at"),
    )
