"""Protocol definition for LLM adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

    from quote_agent.adapters.llm.models import LLMRequest, LLMResponse
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class LLMAdapter(Protocol):
    """Interface contract for LLM provider adapters."""

    async def invoke(self, request: LLMRequest) -> LLMResponse:
        """Send a request to the LLM and return a typed response."""
        ...

    async def health_check(self) -> ServiceHealth:
        """Check provider connectivity and return health status."""
        ...

    def get_model(self, complexity: str) -> ChatOpenAI:
        """Return the configured ChatOpenAI instance for the given complexity level."""
        ...
