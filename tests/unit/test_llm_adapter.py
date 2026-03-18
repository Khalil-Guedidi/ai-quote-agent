"""Tests for the LLM adapter — model routing, health check, invoke, and protocol compliance."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from quote_agent.adapters.email import get_email_adapter
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.adapters.llm.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
)
from quote_agent.adapters.llm.openai_compat import OpenAICompatAdapter
from quote_agent.adapters.llm.protocol import LLMAdapter
from quote_agent.api.health import ServiceHealth
from quote_agent.models.base import get_async_session
from tests.conftest import create_test_app, mock_healthy_adapter, mock_healthy_session


@pytest.fixture()
def llm_settings(env_vars: dict[str, str], _clear_settings_cache: None) -> Any:
    """Provide LLMSettings for tests."""
    from quote_agent.config import get_settings

    return get_settings().llm


@pytest.fixture()
def adapter(llm_settings: Any) -> OpenAICompatAdapter:
    """Create adapter with test settings."""
    return OpenAICompatAdapter(llm_settings)


# --- Model Routing Tests ---


def test_get_model_returns_simple_model_for_simple_complexity(adapter: OpenAICompatAdapter) -> None:
    """get_model("simple") returns the model configured with simple_model."""
    model = adapter.get_model("simple")
    assert model.model_name == "gpt-4o-mini"


def test_get_model_returns_complex_model_for_complex_complexity(adapter: OpenAICompatAdapter) -> None:
    """get_model("complex") returns the model configured with complex_model."""
    model = adapter.get_model("complex")
    assert model.model_name == "gpt-4o"


def test_get_model_returns_default_model_for_unknown_complexity(adapter: OpenAICompatAdapter) -> None:
    """get_model("default") and get_model("anything") return the default model."""
    default = adapter.get_model("default")
    anything = adapter.get_model("anything")
    assert default.model_name == "gpt-4o"
    assert anything.model_name == "gpt-4o"


# --- Model Validation Tests ---


def test_empty_model_name_rejected_at_startup() -> None:
    """LLMSettings rejects empty model names with a clear validation error."""
    from quote_agent.config import LLMSettings

    with pytest.raises(ValidationError, match="Model name must not be empty"):
        LLMSettings(api_key="sk-test", default_model="")  # type: ignore[arg-type]


def test_whitespace_only_model_name_rejected() -> None:
    """LLMSettings rejects whitespace-only model names."""
    from quote_agent.config import LLMSettings

    with pytest.raises(ValidationError, match="Model name must not be empty"):
        LLMSettings(api_key="sk-test", simple_model="  ")  # type: ignore[arg-type]


# --- Invoke Exception Mapping Tests ---


async def test_invoke_raises_llm_timeout_error_on_api_timeout(adapter: OpenAICompatAdapter) -> None:
    """invoke() maps openai.APITimeoutError to LLMTimeoutError."""
    from quote_agent.exceptions import LLMTimeoutError

    with patch.object(
        ChatOpenAI,
        "ainvoke",
        new_callable=AsyncMock,
        side_effect=openai.APITimeoutError(request=MagicMock()),
    ):
        request = LLMRequest(messages=[LLMMessage(role="user", content="test")])
        with pytest.raises(LLMTimeoutError):
            await adapter.invoke(request)


async def test_invoke_raises_adapter_error_on_connection_error(adapter: OpenAICompatAdapter) -> None:
    """invoke() maps openai.APIConnectionError to AdapterError."""
    from quote_agent.exceptions import AdapterError

    with patch.object(
        ChatOpenAI,
        "ainvoke",
        new_callable=AsyncMock,
        side_effect=openai.APIConnectionError(request=MagicMock()),
    ):
        request = LLMRequest(messages=[LLMMessage(role="user", content="test")])
        with pytest.raises(AdapterError):
            await adapter.invoke(request)


# --- Health Check Tests ---


async def test_health_check_returns_healthy_on_success(adapter: OpenAICompatAdapter) -> None:
    """health_check() returns healthy when LLM API responds."""
    adapter._last_health = None
    with patch.object(ChatOpenAI, "ainvoke", new_callable=AsyncMock, return_value=AIMessage(content="pong")):
        result = await adapter.health_check()
    assert result.status == "healthy"
    assert result.error is None


async def test_health_check_returns_unhealthy_on_connection_error(adapter: OpenAICompatAdapter) -> None:
    """health_check() returns unhealthy when API connection fails."""
    adapter._last_health = None
    with patch.object(
        ChatOpenAI,
        "ainvoke",
        new_callable=AsyncMock,
        side_effect=openai.APIConnectionError(request=MagicMock()),
    ):
        result = await adapter.health_check()
    assert result.status == "unhealthy"
    assert result.error is not None


async def test_health_check_returns_unhealthy_on_auth_error(adapter: OpenAICompatAdapter) -> None:
    """health_check() returns unhealthy when authentication fails."""
    adapter._last_health = None
    with patch.object(
        ChatOpenAI,
        "ainvoke",
        new_callable=AsyncMock,
        side_effect=openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401, headers={}),
            body=None,
        ),
    ):
        result = await adapter.health_check()
    assert result.status == "unhealthy"
    assert result.error is not None


# --- Invoke Tests ---


async def test_invoke_returns_typed_response(adapter: OpenAICompatAdapter) -> None:
    """invoke() returns a typed LLMResponse with content and model."""
    mock_response = AIMessage(content="Hello, world!")
    mock_response.response_metadata = {"model_name": "gpt-4o"}
    mock_response.usage_metadata = {
        "input_tokens": 5,
        "output_tokens": 3,
        "total_tokens": 8,
    }
    with patch.object(ChatOpenAI, "ainvoke", new_callable=AsyncMock, return_value=mock_response):
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")],
        )
        result = await adapter.invoke(request)

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello, world!"
    assert result.model == "gpt-4o"
    assert result.usage is not None
    assert result.usage.prompt_tokens == 5
    assert result.usage.completion_tokens == 3
    assert result.usage.total_tokens == 8


# --- Protocol Compliance ---


def test_adapter_conforms_to_protocol(adapter: OpenAICompatAdapter) -> None:
    """OpenAICompatAdapter satisfies the LLMAdapter protocol."""
    assert isinstance(adapter, LLMAdapter)


# --- Health Endpoint Integration Tests ---


@pytest.fixture()
def _app_env(env_vars: dict[str, str], _clear_settings_cache: None) -> None:
    """Combine env_vars and cache clearing for app instantiation."""


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_includes_llm_service() -> None:
    """GET /health response includes services.llm key."""
    app = create_test_app()
    app.dependency_overrides[get_async_session] = mock_healthy_session

    mock_adapter = MagicMock()
    mock_adapter.health_check = AsyncMock(return_value=ServiceHealth(status="healthy"))
    app.dependency_overrides[get_llm_adapter] = lambda: mock_adapter
    app.dependency_overrides[get_erp_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_email_adapter] = mock_healthy_adapter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert "llm" in body["data"]["services"]
    assert body["data"]["services"]["llm"]["status"] == "healthy"

    app.dependency_overrides.clear()


@pytest.mark.usefixtures("_app_env")
async def test_health_endpoint_degraded_when_llm_unhealthy() -> None:
    """GET /health returns degraded status when LLM adapter is unhealthy."""
    app = create_test_app()
    app.dependency_overrides[get_async_session] = mock_healthy_session

    mock_adapter = MagicMock()
    mock_adapter.health_check = AsyncMock(
        return_value=ServiceHealth(status="unhealthy", error="Connection refused"),
    )
    app.dependency_overrides[get_llm_adapter] = lambda: mock_adapter
    app.dependency_overrides[get_erp_adapter] = mock_healthy_adapter
    app.dependency_overrides[get_email_adapter] = mock_healthy_adapter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert body["data"]["status"] == "degraded"
    assert body["data"]["services"]["llm"]["status"] == "unhealthy"

    app.dependency_overrides.clear()
