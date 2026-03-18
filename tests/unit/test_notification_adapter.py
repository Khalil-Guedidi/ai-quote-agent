"""Tests for the notification adapter — health check, caching, protocol compliance, and health endpoint."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.adapters.notification import get_notification_adapter
from quote_agent.adapters.notification.protocol import NotificationAdapter
from quote_agent.adapters.notification.teams import TeamsAdapter
from quote_agent.exceptions import ConfigurationError
from quote_agent.models.base import get_async_session
from tests.conftest import create_test_app, mock_healthy_adapter, mock_healthy_session


@pytest.fixture()
def notification_settings(env_vars: dict[str, str], _clear_settings_cache: None) -> Any:
    """Provide NotificationSettings with a valid webhook URL for tests."""
    import os

    os.environ["NOTIFICATION__TEAMS_WEBHOOK_URL"] = "https://test.webhook.office.com/webhook/test"
    from quote_agent.config import get_settings

    get_settings.cache_clear()
    settings = get_settings().notification
    yield settings
    os.environ.pop("NOTIFICATION__TEAMS_WEBHOOK_URL", None)
    get_settings.cache_clear()


@pytest.fixture()
def adapter(notification_settings: Any) -> TeamsAdapter:
    """Create adapter with test settings."""
    return TeamsAdapter(notification_settings)


# --- Health Check Tests ---


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_returns_healthy_on_success(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """health_check() returns healthy when webhook responds."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    result = await adapter.health_check()

    assert result.status == "healthy"
    assert result.error is None


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_returns_unhealthy_on_connection_error(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """health_check() returns unhealthy when connection is refused."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client_cls.return_value = mock_client

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Connection refused" in (result.error or "")


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_returns_unhealthy_on_timeout(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """health_check() returns unhealthy when webhook times out."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
    mock_client_cls.return_value = mock_client

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Timed out" in (result.error or "")


def test_health_check_returns_unhealthy_on_empty_webhook_url(
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """TeamsAdapter raises ConfigurationError when webhook URL is empty."""
    from quote_agent.config import NotificationSettings

    settings = NotificationSettings(channel="teams", teams_webhook_url="")
    with pytest.raises(ConfigurationError, match="must not be empty"):
        TeamsAdapter(settings)


def test_health_check_returns_unhealthy_on_non_https_url(
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """TeamsAdapter raises ConfigurationError when webhook URL is not HTTPS."""
    from quote_agent.config import NotificationSettings

    settings = NotificationSettings(channel="teams", teams_webhook_url="http://insecure.example.com/webhook")
    with pytest.raises(ConfigurationError, match="must be an HTTPS URL"):
        TeamsAdapter(settings)


@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_health_check_caches_result(
    mock_client_cls: MagicMock,
    adapter: TeamsAdapter,
) -> None:
    """Second health_check() call within 30s returns cached result without hitting httpx."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    result1 = await adapter.health_check()
    result2 = await adapter.health_check()

    assert result1.status == "healthy"
    assert result2.status == "healthy"
    # AsyncClient should only be constructed once (for the first call)
    assert mock_client_cls.call_count == 1


# --- Protocol Compliance ---


def test_adapter_conforms_to_protocol(adapter: TeamsAdapter) -> None:
    """TeamsAdapter satisfies the NotificationAdapter protocol."""
    assert isinstance(adapter, NotificationAdapter)


# --- Health Endpoint Integration ---


@pytest.fixture()
def _app_env(env_vars: dict[str, str], _clear_settings_cache: None) -> None:
    """Combine env_vars and cache clearing for app instantiation."""


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_includes_notification_service() -> None:
    """GET /health response includes services.notification key."""
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
    assert "notification" in body["data"]["services"]
    assert body["data"]["services"]["notification"]["status"] == "healthy"

    app.dependency_overrides.clear()
