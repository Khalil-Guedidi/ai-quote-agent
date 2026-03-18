"""Tests for the database infrastructure (engine, session, base model)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _settings_env(env_vars: dict[str, str], _clear_settings_cache: None) -> Iterator[None]:
    """Ensure all env vars are set and settings cache is cleared for every test."""
    from quote_agent.models.base import _get_session_factory, create_async_engine_from_settings

    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()
    yield
    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()


# ---------------------------------------------------------------------------
# URL Conversion Tests
# ---------------------------------------------------------------------------


class TestUrlConversion:
    """_ensure_async_url converts plain postgresql:// to asyncpg driver."""

    def test_url_conversion_postgresql_to_asyncpg(self) -> None:
        from quote_agent.models.base import _ensure_async_url

        assert _ensure_async_url("postgresql://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"

    def test_url_passthrough_asyncpg(self) -> None:
        from quote_agent.models.base import _ensure_async_url

        url = "postgresql+asyncpg://u:p@host/db"
        assert _ensure_async_url(url) == url


# ---------------------------------------------------------------------------
# Base Model Tests
# ---------------------------------------------------------------------------


class TestBaseModel:
    """SQLAlchemy Base and TimestampMixin are correctly configured."""

    def test_naming_convention(self) -> None:
        from quote_agent.models.base import Base

        nc = Base.metadata.naming_convention
        assert nc["ix"] == "ix_%(table_name)s_%(column_0_N_name)s"  # type: ignore[index]
        assert nc["uq"] == "uq_%(table_name)s_%(column_0_N_name)s"  # type: ignore[index]
        assert nc["ck"] == "ck_%(table_name)s_%(constraint_name)s"  # type: ignore[index]
        assert nc["fk"] == "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s"  # type: ignore[index]
        assert nc["pk"] == "pk_%(table_name)s"  # type: ignore[index]

    def test_timestamp_mixin_fields(self) -> None:
        from quote_agent.models.base import TimestampMixin

        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")
        # Verify they are mapped columns (MappedColumn descriptors)
        assert hasattr(TimestampMixin.__dict__["created_at"], "name")
        assert hasattr(TimestampMixin.__dict__["updated_at"], "name")


# ---------------------------------------------------------------------------
# Engine / Session Tests
# ---------------------------------------------------------------------------


class TestAsyncEngine:
    """Async engine creation and session management."""

    def test_async_engine_creation(self) -> None:
        from quote_agent.models.base import create_async_engine_from_settings

        engine = create_async_engine_from_settings()
        assert str(engine.url).startswith("postgresql+asyncpg://")

    def test_engine_echo_from_settings(self) -> None:
        from quote_agent.models.base import create_async_engine_from_settings

        engine = create_async_engine_from_settings()
        assert engine.echo is False
