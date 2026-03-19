"""Embedding adapter package — sentence-transformers integration."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from quote_agent.adapters.embedding.models import EmbeddingRequest, EmbeddingResult
from quote_agent.adapters.embedding.protocol import EmbeddingAdapter

if TYPE_CHECKING:
    from quote_agent.adapters.embedding.sentence_transformers import SentenceTransformerAdapter

__all__ = [
    "EmbeddingAdapter",
    "EmbeddingRequest",
    "EmbeddingResult",
    "get_embedding_adapter",
]


@lru_cache(maxsize=1)
def get_embedding_adapter() -> SentenceTransformerAdapter:
    """Create and return a cached embedding adapter singleton."""
    from quote_agent.adapters.embedding.sentence_transformers import SentenceTransformerAdapter
    from quote_agent.config import get_settings

    return SentenceTransformerAdapter(get_settings().embedding)
