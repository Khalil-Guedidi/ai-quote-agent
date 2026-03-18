"""LLM adapter package — OpenAI-compatible provider integration."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from quote_agent.adapters.llm.models import LLMRequest, LLMResponse
from quote_agent.adapters.llm.protocol import LLMAdapter

if TYPE_CHECKING:
    from quote_agent.adapters.llm.openai_compat import OpenAICompatAdapter

__all__ = [
    "LLMAdapter",
    "LLMRequest",
    "LLMResponse",
    "get_llm_adapter",
]


@lru_cache(maxsize=1)
def get_llm_adapter() -> OpenAICompatAdapter:
    """Create and return a cached LLM adapter singleton."""
    from quote_agent.adapters.llm.openai_compat import OpenAICompatAdapter
    from quote_agent.config import get_settings

    return OpenAICompatAdapter(get_settings().llm)
