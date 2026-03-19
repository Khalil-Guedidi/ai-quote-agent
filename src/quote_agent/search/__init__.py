"""Search package — hybrid search combining semantic + keyword with RRF fusion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from quote_agent.search.engine import SearchEngine
from quote_agent.search.models import ScoredProduct, SearchRequest, SearchResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "ScoredProduct",
    "SearchEngine",
    "SearchRequest",
    "SearchResult",
    "get_search_engine",
]


def get_search_engine(session: AsyncSession) -> SearchEngine:
    """Convenience factory — creates a SearchEngine with the cached embedding adapter."""
    from quote_agent.adapters.embedding import get_embedding_adapter

    return SearchEngine(session, get_embedding_adapter())
