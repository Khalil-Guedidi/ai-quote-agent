"""Fixtures for integration tests requiring a real PostgreSQL database."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


def _has_real_database() -> bool:
    """Check if a real DATABASE__URL is available (from .env or environment)."""
    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


requires_database = pytest.mark.skipif(
    not _has_real_database(),
    reason="No real DATABASE__URL configured — skipping integration tests",
)


@pytest.fixture(autouse=True)
def _integration_env_and_cache() -> Iterator[None]:
    """Set minimal env vars for Settings and clear caches around each test.

    CI only provides DATABASE__URL; Settings also requires LLM, ERP, EMAIL.
    """
    from quote_agent.config import get_settings
    from quote_agent.models.base import _get_session_factory, create_async_engine_from_settings

    minimal = {
        "LLM__API_KEY": "sk-test-key-for-integration-tests",
        "ERP__URL": "https://erp.test.local",
        "ERP__DATABASE": "test_erp",
        "ERP__USERNAME": "admin",
        "ERP__API_KEY": "erp-test-key",
        "EMAIL__IMAP_SERVER": "imap.test.local",
        "EMAIL__USERNAME": "test@test.local",
        "EMAIL__PASSWORD": "test-password",
        "NOTIFICATION__CHANNEL": "log",
    }

    old: dict[str, str | None] = {}
    for key, value in minimal.items():
        old[key] = os.environ.get(key)
        if key not in os.environ:
            os.environ[key] = value

    get_settings.cache_clear()
    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()
    yield
    get_settings.cache_clear()
    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()

    for key in minimal:
        if old[key] is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old[key]
