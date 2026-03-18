"""Tests for health check and API v1 base endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from quote_agent.models.base import get_async_session


@pytest.fixture()
def _app_env(env_vars: dict[str, str], _clear_settings_cache: None) -> None:
    """Combine env_vars and cache clearing for app instantiation."""


def _create_test_app() -> Any:
    """Create a fresh app instance (must be called after env/cache setup)."""
    from quote_agent.config import get_settings

    get_settings.cache_clear()

    from quote_agent.models.base import _get_session_factory, create_async_engine_from_settings

    create_async_engine_from_settings.cache_clear()
    _get_session_factory.cache_clear()

    # Re-import to get fresh app
    import importlib

    import quote_agent.main

    importlib.reload(quote_agent.main)
    return quote_agent.main.app


async def _mock_healthy_session() -> AsyncGenerator[AsyncSession, None]:
    """Mock session that succeeds on execute."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())
    yield session


async def _mock_unhealthy_session() -> AsyncGenerator[AsyncSession, None]:
    """Mock session that raises SQLAlchemyError on execute."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(side_effect=SQLAlchemyError("Connection refused"))
    yield session


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_returns_healthy() -> None:
    """GET /health returns 200 with healthy status when DB is reachable."""
    app = _create_test_app()
    app.dependency_overrides[get_async_session] = _mock_healthy_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "healthy"
    assert body["data"]["services"]["database"]["status"] == "healthy"
    assert body["data"]["services"]["database"]["error"] is None
    assert "timestamp" in body["meta"]

    app.dependency_overrides.clear()


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_returns_degraded_when_db_fails() -> None:
    """GET /health returns 200 with degraded status when DB is unreachable."""
    app = _create_test_app()
    app.dependency_overrides[get_async_session] = _mock_unhealthy_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "degraded"
    assert body["data"]["services"]["database"]["status"] == "unhealthy"
    assert "Connection refused" in body["data"]["services"]["database"]["error"]
    assert "timestamp" in body["meta"]

    app.dependency_overrides.clear()


@pytest.mark.usefixtures("_app_env")
async def test_api_v1_base_endpoint() -> None:
    """GET /api/v1/ returns app name, version, and meta timestamp."""
    app = _create_test_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["name"] == "ai-quote-agent"
    assert body["data"]["version"] == "0.1.0"
    assert "timestamp" in body["meta"]


@pytest.mark.usefixtures("_app_env")
async def test_api_response_format_has_meta_timestamp() -> None:
    """Any endpoint response includes ISO 8601 timestamp in meta."""
    app = _create_test_app()
    app.dependency_overrides[get_async_session] = _mock_healthy_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    timestamp = body["meta"]["timestamp"]
    # Verify it's a valid ISO 8601 timestamp
    assert "T" in timestamp
    assert len(timestamp) > 10  # More than just a date

    app.dependency_overrides.clear()


@pytest.mark.usefixtures("_app_env")
async def test_unhandled_exception_returns_500_error_format() -> None:
    """Unhandled exceptions return structured 500 error response."""
    app = _create_test_app()

    @app.get("/test-error")
    async def trigger_error() -> None:
        msg = "Test unhandled error"
        raise RuntimeError(msg)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-error")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred"
    assert body["error"]["detail"] is None
    assert "timestamp" in body["meta"]
