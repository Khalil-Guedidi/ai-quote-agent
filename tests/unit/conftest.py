"""Unit test configuration — ensures all unit tests have valid env vars for Settings."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _unit_env_vars() -> Iterator[None]:
    """Set minimal env vars for get_settings() and clear the LRU cache around each test.

    In CI, only DATABASE__URL is provided. Tests that call get_settings() (directly
    or via node code) need LLM, ERP, and EMAIL settings to exist. This fixture
    ensures a deterministic environment regardless of test execution order.
    """
    from quote_agent.config import get_settings

    minimal = {
        "DATABASE__URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
        "LLM__API_KEY": "sk-test-key-for-unit-tests",
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
    yield
    get_settings.cache_clear()

    for key in minimal:
        if old[key] is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old[key]
