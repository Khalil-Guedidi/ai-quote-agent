"""Fixtures for integration tests requiring a real PostgreSQL database."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


def _has_real_database() -> bool:
    """Check if a real DATABASE__URL is available (from .env or environment)."""
    import os

    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


requires_database = pytest.mark.skipif(
    not _has_real_database(),
    reason="No real DATABASE__URL configured — skipping integration tests",
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Clear settings and engine caches before/after each integration test."""
    from quote_agent.config import get_settings
    from quote_agent.models.base import _get_session_factory, create_async_engine_from_settings

    get_settings.cache_clear()
    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()
    yield
    get_settings.cache_clear()
    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()
