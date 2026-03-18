"""Tests for the email adapter — health check, caching, protocol compliance, and health endpoint."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.email.imap import IMAPAdapter
from quote_agent.adapters.email.protocol import EmailAdapter
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.adapters.notification import get_notification_adapter
from quote_agent.models.base import get_async_session
from tests.conftest import create_test_app, mock_healthy_adapter, mock_healthy_session


@pytest.fixture()
def email_settings(env_vars: dict[str, str], _clear_settings_cache: None) -> Any:
    """Provide EmailSettings for tests."""
    from quote_agent.config import get_settings

    return get_settings().email


@pytest.fixture()
def adapter(email_settings: Any) -> IMAPAdapter:
    """Create adapter with test settings."""
    return IMAPAdapter(email_settings)


# --- Health Check Tests ---


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_healthy_on_success(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns healthy when IMAP login + select succeed."""
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"42"])
    mock_imap_cls.return_value = mock_conn

    result = await adapter.health_check()

    assert result.status == "healthy"
    assert result.error is None


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_unhealthy_on_connection_error(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns unhealthy when IMAP connection is refused."""
    mock_imap_cls.side_effect = ConnectionRefusedError("Connection refused")

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Connection refused" in (result.error or "")


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_unhealthy_on_auth_failure(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns unhealthy when IMAP login fails."""
    import imaplib

    mock_conn = MagicMock()
    mock_conn.login.side_effect = imaplib.IMAP4.error("LOGIN failed")
    mock_imap_cls.return_value = mock_conn

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert result.error is not None


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_returns_unhealthy_on_bad_folder(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """health_check() returns unhealthy when IMAP folder select fails."""
    import imaplib

    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.side_effect = imaplib.IMAP4.error("Folder not found")
    mock_imap_cls.return_value = mock_conn

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert result.error is not None


@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_health_check_caches_result(
    mock_imap_cls: MagicMock,
    adapter: IMAPAdapter,
) -> None:
    """Second health_check() call within 30s returns cached result."""
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"42"])
    mock_imap_cls.return_value = mock_conn

    result1 = await adapter.health_check()
    result2 = await adapter.health_check()

    assert result1.status == "healthy"
    assert result2.status == "healthy"
    # IMAP4_SSL should only be constructed once (for the first call)
    assert mock_imap_cls.call_count == 1


# --- Protocol Compliance ---


def test_adapter_conforms_to_protocol(adapter: IMAPAdapter) -> None:
    """IMAPAdapter satisfies the EmailAdapter protocol."""
    assert isinstance(adapter, EmailAdapter)


# --- Health Endpoint Integration ---


@pytest.fixture()
def _app_env(env_vars: dict[str, str], _clear_settings_cache: None) -> None:
    """Combine env_vars and cache clearing for app instantiation."""


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_includes_email_service() -> None:
    """GET /health response includes services.email key."""
    app = create_test_app()
    app.dependency_overrides[get_async_session] = mock_healthy_session
    app.dependency_overrides[get_llm_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_erp_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_email_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_notification_adapter] = mock_healthy_adapter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert "email" in body["data"]["services"]
    assert body["data"]["services"]["email"]["status"] == "healthy"

    app.dependency_overrides.clear()
