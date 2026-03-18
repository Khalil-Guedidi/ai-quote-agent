"""Integration tests for database connectivity and pgvector extension."""

from __future__ import annotations

from sqlalchemy import text

from quote_agent.models.base import get_async_session

from .conftest import requires_database


@requires_database
class TestSessionLifecycle:
    """Session opens and closes cleanly against a real database."""

    async def test_session_lifecycle(self) -> None:
        async for session in get_async_session():
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1


@requires_database
class TestPgvectorExtension:
    """pgvector extension is available after migration."""

    async def test_pgvector_extension_available(self) -> None:
        async for session in get_async_session():
            result = await session.execute(text("SELECT 'vector'::regtype"))
            assert result.scalar() == "vector"
