"""Fixtures for E2E tests requiring real services (PostgreSQL, IMAP, LLM)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import delete, text

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.config import get_settings
from quote_agent.models.base import _get_session_factory, create_async_engine_from_settings
from quote_agent.models.email_request import EmailRequest
from quote_agent.models.quote_request import QuoteRequest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Marker: skip if any required service env var is missing
# ---------------------------------------------------------------------------

_E2E_TEST_PREFIX = "e2e-test"


def _has_real_database() -> bool:
    """Check if a real DATABASE__URL is available."""
    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


def _has_real_llm() -> bool:
    """Check if a real LLM__API_KEY is available (not a placeholder)."""
    key = os.environ.get("LLM__API_KEY", "")
    return bool(key) and not key.startswith("test") and key != "placeholder"


requires_e2e = pytest.mark.skipif(
    not (_has_real_database() and _has_real_llm()),
    reason="E2E tests require real DATABASE__URL and LLM__API_KEY",
)


# ---------------------------------------------------------------------------
# Cache clearing — must happen before/after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_all_caches() -> Iterator[None]:
    """Clear all singleton caches before/after each E2E test."""
    get_settings.cache_clear()
    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()
    get_llm_adapter.cache_clear()
    get_email_adapter.cache_clear()
    yield
    get_settings.cache_clear()
    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()
    get_llm_adapter.cache_clear()
    get_email_adapter.cache_clear()


# ---------------------------------------------------------------------------
# Database session with migration + cleanup
# ---------------------------------------------------------------------------


@pytest.fixture()
async def e2e_db_session() -> AsyncIterator[AsyncSession]:
    """Connect to real PostgreSQL, run migrations, yield session, clean up test data."""
    import subprocess

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Build env with current os.environ (includes loaded .env vars)
    env = {**os.environ}

    # Run Alembic migrations to ensure schema is current
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Alembic migration failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    factory = _get_session_factory()
    async with factory() as session:
        # Verify connectivity
        await session.execute(text("SELECT 1"))
        yield session

    # Cleanup: delete test data created during E2E tests
    async with factory() as cleanup_session:
        # Delete QuoteRequests linked to test EmailRequests first (FK constraint)
        test_emails = await cleanup_session.execute(
            EmailRequest.__table__.select().where(
                EmailRequest.message_id.like(f"%{_E2E_TEST_PREFIX}%")
            )
        )
        test_email_ids = [row.id for row in test_emails]
        if test_email_ids:
            await cleanup_session.execute(
                delete(QuoteRequest).where(QuoteRequest.email_request_id.in_(test_email_ids))
            )
        await cleanup_session.execute(
            delete(EmailRequest).where(EmailRequest.message_id.like(f"%{_E2E_TEST_PREFIX}%"))
        )
        await cleanup_session.commit()


# ---------------------------------------------------------------------------
# Real adapter fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def e2e_email_adapter():
    """Return a real IMAPAdapter connected to the configured IMAP server."""
    return get_email_adapter()


@pytest.fixture()
def e2e_llm_adapter():
    """Return a real LLM adapter using LLM__API_KEY — uses simple_model to minimize cost."""
    return get_llm_adapter()
