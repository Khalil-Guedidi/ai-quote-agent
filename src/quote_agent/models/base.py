"""SQLAlchemy declarative base, async engine, and session management."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — SQLAlchemy needs runtime access for Mapped[datetime]
from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy import MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    metadata = MetaData(naming_convention=convention)


class TimestampMixin:
    """Mixin that adds created_at / updated_at columns to any model."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


def _ensure_async_url(url: str) -> str:
    """Convert ``postgresql://`` to ``postgresql+asyncpg://`` if needed."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@lru_cache(maxsize=1)
def create_async_engine_from_settings() -> AsyncEngine:
    """Create an async engine from application settings (cached singleton)."""
    from quote_agent.config import settings

    return create_async_engine(
        _ensure_async_url(settings.database.url),
        echo=settings.database.echo,
    )


@lru_cache(maxsize=1)
def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Build a session factory bound to the settings-based engine (cached singleton)."""
    engine = create_async_engine_from_settings()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` — suitable for FastAPI dependency injection."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session
