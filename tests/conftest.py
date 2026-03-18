"""Shared test fixtures."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterator


def _minimal_env() -> dict[str, str]:
    """Return the minimal set of env vars required by Settings."""
    return {
        "DATABASE__URL": "postgresql://test:test@localhost:5432/test_db",
        "LLM__API_KEY": "sk-test-key-for-unit-tests",
        "ERP__URL": "https://erp.test.local",
        "ERP__DATABASE": "test_erp",
        "ERP__USERNAME": "admin",
        "ERP__API_KEY": "erp-test-key",
        "EMAIL__IMAP_SERVER": "imap.test.local",
        "EMAIL__USERNAME": "test@test.local",
        "EMAIL__PASSWORD": "test-password",
    }


@pytest.fixture()
def env_vars() -> Iterator[dict[str, str]]:
    """Set minimal valid environment variables for Settings, then clean up."""
    env = _minimal_env()
    old: dict[str, str | None] = {}
    for key, value in env.items():
        old[key] = os.environ.get(key)
        os.environ[key] = value
    yield env
    for key in env:
        if old[key] is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old[key]


@pytest.fixture()
def _clear_settings_cache() -> Iterator[None]:
    """Clear the get_settings LRU cache before and after each test."""
    from quote_agent.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- Shared test helpers for health endpoint integration tests ---


def create_test_app() -> Any:
    """Create a fresh app instance (must be called after env/cache setup)."""
    from quote_agent.adapters.email import get_email_adapter
    from quote_agent.adapters.erp import get_erp_adapter
    from quote_agent.adapters.llm import get_llm_adapter
    from quote_agent.adapters.notification import get_notification_adapter
    from quote_agent.config import get_settings

    get_settings.cache_clear()
    get_llm_adapter.cache_clear()
    get_erp_adapter.cache_clear()
    get_email_adapter.cache_clear()
    get_notification_adapter.cache_clear()

    from quote_agent.models.base import _get_session_factory, create_async_engine_from_settings

    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()

    import importlib

    import quote_agent.main

    importlib.reload(quote_agent.main)
    return quote_agent.main.app


def mock_healthy_adapter() -> MagicMock:
    """Mock adapter that reports healthy (used for LLM, ERP, email)."""
    from quote_agent.api.health import ServiceHealth

    adapter = MagicMock()
    adapter.health_check = AsyncMock(return_value=ServiceHealth(status="healthy"))
    return adapter


async def mock_healthy_session() -> AsyncGenerator[AsyncSession, None]:
    """Mock session that succeeds on execute."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())
    yield session
