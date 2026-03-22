"""OpenAI-compatible LLM adapter implementation."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import openai
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from quote_agent.adapters.llm.models import LLMResponse, LLMUsage
from quote_agent.api.health import ServiceHealth
from quote_agent.exceptions import AdapterError, LLMTimeoutError

if TYPE_CHECKING:
    from quote_agent.adapters.llm.models import LLMRequest
    from quote_agent.config import LLMSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0

_ROLE_TO_CLASS = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


class OpenAICompatAdapter:
    """LLM adapter using any OpenAI-compatible API via langchain-openai."""

    def __init__(self, settings: LLMSettings) -> None:
        self._common_kwargs = {
            "api_key": settings.api_key.get_secret_value(),
            "base_url": settings.base_url,
            "timeout": settings.timeout,
            "max_retries": settings.max_retries,
            "temperature": 0,
        }
        self._default_model = ChatOpenAI(model=settings.default_model, **self._common_kwargs)
        self._simple_model = ChatOpenAI(model=settings.simple_model, **self._common_kwargs)
        self._complex_model = ChatOpenAI(model=settings.complex_model, **self._common_kwargs)

        self._last_health: ServiceHealth | None = None
        self._last_health_time: float = 0.0

    def get_model(self, complexity: str) -> ChatOpenAI:
        """Return the configured model for the given complexity level."""
        if complexity == "simple":
            return self._simple_model
        if complexity == "complex":
            return self._complex_model
        return self._default_model

    async def invoke(self, request: LLMRequest) -> LLMResponse:
        """Send a request to the LLM and return a typed response."""
        messages = [_ROLE_TO_CLASS[msg.role](content=msg.content) for msg in request.messages]

        model = self._default_model
        if request.model:
            model = ChatOpenAI(model=request.model, **self._common_kwargs)

        try:
            result: AIMessage = await model.ainvoke(messages)
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except (openai.AuthenticationError, openai.APIConnectionError, openai.RateLimitError) as exc:
            raise AdapterError(str(exc)) from exc

        usage: LLMUsage | None = None
        if result.usage_metadata:
            usage = LLMUsage(
                prompt_tokens=result.usage_metadata["input_tokens"],
                completion_tokens=result.usage_metadata["output_tokens"],
                total_tokens=result.usage_metadata["total_tokens"],
            )

        return LLMResponse(
            content=str(result.content),
            model=result.response_metadata.get("model_name", "unknown"),
            usage=usage,
        )

    async def health_check(self) -> ServiceHealth:
        """Check provider connectivity with caching to reduce API costs."""
        now = time.monotonic()
        if self._last_health and (now - self._last_health_time) < _HEALTH_CACHE_TTL:
            return self._last_health

        try:
            await asyncio.wait_for(
                self._default_model.ainvoke([HumanMessage(content="ping")]),
                timeout=_HEALTH_CHECK_TIMEOUT,
            )
            health = ServiceHealth(status="healthy")
        except Exception as exc:
            logger.warning("LLM health check failed: %s", exc)
            health = ServiceHealth(status="unhealthy", error=str(exc))

        self._last_health = health
        self._last_health_time = time.monotonic()
        return health
