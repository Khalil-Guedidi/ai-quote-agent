"""Tests for the ERP adapter — health check, caching, protocol compliance, and health endpoint."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.erp.odoo import OdooAdapter
from quote_agent.adapters.erp.protocol import ERPAdapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.models.base import get_async_session
from tests.conftest import create_test_app, mock_healthy_adapter, mock_healthy_session


@pytest.fixture()
def erp_settings(env_vars: dict[str, str], _clear_settings_cache: None) -> Any:
    """Provide ERPSettings for tests."""
    from quote_agent.config import get_settings

    return get_settings().erp


@pytest.fixture()
def adapter(erp_settings: Any) -> OdooAdapter:
    """Create adapter with test settings."""
    return OdooAdapter(erp_settings)


# --- Health Check Tests ---


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_health_check_returns_healthy_on_success(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """health_check() returns healthy when XML-RPC version + authenticate succeed."""
    mock_proxy = MagicMock()
    mock_proxy.version.return_value = {"server_version": "17.0", "protocol_version": 1}
    mock_proxy.authenticate.return_value = 2  # uid
    mock_proxy_cls.return_value = mock_proxy

    result = await adapter.health_check()

    assert result.status == "healthy"
    assert result.error is None


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_health_check_returns_unhealthy_on_connection_error(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """health_check() returns unhealthy when connection is refused."""
    mock_proxy = MagicMock()
    mock_proxy.version.side_effect = ConnectionRefusedError("Connection refused")
    mock_proxy_cls.return_value = mock_proxy

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Connection refused" in (result.error or "")


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_health_check_returns_unhealthy_on_auth_failure(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """health_check() returns unhealthy when authenticate returns False."""
    mock_proxy = MagicMock()
    mock_proxy.version.return_value = {"server_version": "17.0"}
    mock_proxy.authenticate.return_value = False
    mock_proxy_cls.return_value = mock_proxy

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "Authentication failed" in (result.error or "")


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_health_check_returns_unhealthy_on_protocol_error(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """health_check() returns unhealthy when Odoo returns an HTTP error (e.g. 502)."""
    import xmlrpc.client

    mock_proxy = MagicMock()
    mock_proxy.version.side_effect = xmlrpc.client.ProtocolError(
        "https://erp.test.local/xmlrpc/2/common", 502, "Bad Gateway", {}
    )
    mock_proxy_cls.return_value = mock_proxy

    result = await adapter.health_check()

    assert result.status == "unhealthy"
    assert "502" in (result.error or "")


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_health_check_caches_result(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """Second health_check() call within 30s returns cached result without hitting XML-RPC."""
    mock_proxy = MagicMock()
    mock_proxy.version.return_value = {"server_version": "17.0"}
    mock_proxy.authenticate.return_value = 2
    mock_proxy_cls.return_value = mock_proxy

    result1 = await adapter.health_check()
    result2 = await adapter.health_check()

    assert result1.status == "healthy"
    assert result2.status == "healthy"
    # ServerProxy should only be constructed once (for the first call)
    assert mock_proxy_cls.call_count == 1


# --- Protocol Compliance ---


def test_adapter_conforms_to_protocol(adapter: OdooAdapter) -> None:
    """OdooAdapter satisfies the ERPAdapter protocol."""
    assert isinstance(adapter, ERPAdapter)


# --- Health Endpoint Integration ---


@pytest.fixture()
def _app_env(env_vars: dict[str, str], _clear_settings_cache: None) -> None:
    """Combine env_vars and cache clearing for app instantiation."""


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_includes_erp_service() -> None:
    """GET /health response includes services.erp key."""
    app = create_test_app()
    app.dependency_overrides[get_async_session] = mock_healthy_session
    app.dependency_overrides[get_llm_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_erp_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_email_adapter] = mock_healthy_adapter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert "erp" in body["data"]["services"]
    assert body["data"]["services"]["erp"]["status"] == "healthy"

    app.dependency_overrides.clear()
