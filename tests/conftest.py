"""Shared test fixtures."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


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
