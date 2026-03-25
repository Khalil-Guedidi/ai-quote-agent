"""Tests for the configuration system."""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from quote_agent.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _reset_cache(_clear_settings_cache: None) -> None:
    """Ensure settings cache is cleared for every test in this module."""


class TestSettingsLoadFromEnv:
    """Settings load correctly from environment variables."""

    def test_settings_load_from_env(self, env_vars: dict[str, str]) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.database.url == env_vars["DATABASE__URL"]
        assert s.llm.api_key.get_secret_value() == env_vars["LLM__API_KEY"]
        assert s.erp.url == env_vars["ERP__URL"]
        assert s.email.imap_server == env_vars["EMAIL__IMAP_SERVER"]

    def test_settings_nested_delimiter(self, env_vars: dict[str, str]) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.database.url == env_vars["DATABASE__URL"]
        assert s.erp.database == env_vars["ERP__DATABASE"]

    def test_settings_default_values(self, env_vars: dict[str, str]) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.app.name == "ai-quote-agent"
        assert s.app.version == "0.1.0"
        assert s.app.debug is False
        assert s.llm.timeout == 60
        assert s.email.imap_port == 993
        assert s.notification.channel == "log"  # env_vars fixture + autouse safety net force log


class TestSettingsValidation:
    """Settings fail fast on missing or invalid configuration."""

    def test_settings_fail_on_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_settings_fail_on_invalid_database_url(self, env_vars: dict[str, str]) -> None:
        os.environ["DATABASE__URL"] = "mysql://bad:url@localhost/db"
        with pytest.raises(ValidationError, match="postgresql"):
            Settings()  # type: ignore[call-arg]


class TestSettingsSecretStr:
    """SecretStr values are not exposed in repr/str."""

    def test_settings_secret_str_not_exposed(self, env_vars: dict[str, str]) -> None:
        s = Settings()  # type: ignore[call-arg]
        repr_str = repr(s)
        assert "sk-test-key-for-unit-tests" not in repr_str
        assert "test-password" not in repr_str
        assert "erp-test-key" not in repr_str

    def test_secret_str_get_secret_value(self, env_vars: dict[str, str]) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.llm.api_key.get_secret_value() == "sk-test-key-for-unit-tests"


class TestGetSettings:
    """get_settings() returns a cached singleton."""

    def test_get_settings_returns_instance(self, env_vars: dict[str, str]) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_is_cached(self, env_vars: dict[str, str]) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
