"""Hybrid search engine — orchestrates semantic + keyword search with RRF fusion."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from quote_agent.config import get_settings
from quote_agent.search.keyword import is_reference_code, search_exact_ref, search_keyword
from quote_agent.search.models import ScoredProduct, SearchRequest, SearchResult
from quote_agent.search.vector import search_semantic

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.embedding.protocol import EmbeddingAdapter

logger = logging.getLogger(__name__)

_PREFETCH_MULTIPLIER = 2


def _rrf_fuse(
    semantic_results: list[ScoredProduct],
    keyword_results: list[ScoredProduct],
    k: int = 60,
) -> list[ScoredProduct]:
    """Fuse two ranked lists using Reciprocal Rank Fusion. k=60 is standard default."""
    scores: dict[uuid.UUID, float] = {}
    products: dict[uuid.UUID, ScoredProduct] = {}

    for rank, item in enumerate(semantic_results, start=1):
        scores[item.product_id] = scores.get(item.product_id, 0) + 1.0 / (k + rank)
        products[item.product_id] = item

    for rank, item in enumerate(keyword_results, start=1):
        scores[item.product_id] = scores.get(item.product_id, 0) + 1.0 / (k + rank)
        products[item.product_id] = item

    sorted_ids = sorted(scores, key=lambda pid: scores[pid], reverse=True)

    return [
        products[pid].model_copy(update={"score": scores[pid], "rank": i + 1, "match_source": "hybrid"})
        for i, pid in enumerate(sorted_ids)
    ]


class SearchEngine:
    """Hybrid search orchestration combining semantic, keyword, and exact reference search."""

    def __init__(self, session: AsyncSession, embedding_adapter: EmbeddingAdapter) -> None:
        self._session = session
        self._embedding = embedding_adapter
        self._settings = get_settings().search

    async def search_hybrid(self, request: SearchRequest) -> SearchResult:
        """Run hybrid search: exact ref shortcut, then semantic + keyword with RRF fusion."""
        start = time.monotonic()
        query = request.query.strip()
        limit = request.limit or self._settings.default_limit

        # Fast path: if query looks like a reference code, try exact match first
        if is_reference_code(query):
            exact_results = await search_exact_ref(
                self._session, query, limit, include_stale=request.include_stale,
            )
            if exact_results:
                duration = time.monotonic() - start
                logger.info(
                    "Exact reference search completed",
                    extra={"context": {
                                "query": query,
                        "method": "exact_ref",
                        "results": len(exact_results),
                        "duration_s": round(duration, 4),
                    }},
                )
                return SearchResult(
                    results=exact_results,
                    total_found=len(exact_results),
                    query=query,
                    method="exact_ref",
                    duration_seconds=round(duration, 4),
                )

        # Generate query embedding
        embeddings = await self._embedding.embed_texts([query])
        query_embedding = embeddings[0]

        # Run semantic and keyword search sequentially (asyncpg doesn't support
        # concurrent queries on the same connection)
        prefetch_limit = limit * _PREFETCH_MULTIPLIER
        semantic_results = await search_semantic(
            self._session, query_embedding, prefetch_limit, include_stale=request.include_stale,
        )
        keyword_results = await search_keyword(
            self._session, query, prefetch_limit, include_stale=request.include_stale,
        )

        # Fuse results using RRF
        fused = _rrf_fuse(semantic_results, keyword_results, k=self._settings.rrf_k)
        final_results = fused[:limit]

        duration = time.monotonic() - start
        logger.info(
            "Hybrid search completed",
            extra={"context": {
                "query": query,
                "method": "hybrid",
                "results": len(final_results),
                "semantic_count": len(semantic_results),
                "keyword_count": len(keyword_results),
                "duration_s": round(duration, 4),
            }},
        )

        return SearchResult(
            results=final_results,
            total_found=len(fused),
            query=query,
            method="hybrid",
            duration_seconds=round(duration, 4),
        )

    async def search_semantic_only(self, request: SearchRequest) -> SearchResult:
        """Expose semantic (vector) search alone."""
        start = time.monotonic()
        query = request.query.strip()
        limit = request.limit or self._settings.default_limit

        embeddings = await self._embedding.embed_texts([query])
        query_embedding = embeddings[0]

        results = await search_semantic(
            self._session, query_embedding, limit, include_stale=request.include_stale,
        )

        duration = time.monotonic() - start
        logger.info(
            "Semantic search completed",
            extra={"context": {
                "query": query,
                "method": "semantic",
                "results": len(results),
                "duration_s": round(duration, 4),
            }},
        )

        return SearchResult(
            results=results,
            total_found=len(results),
            query=query,
            method="semantic",
            duration_seconds=round(duration, 4),
        )

    async def search_keyword_only(self, request: SearchRequest) -> SearchResult:
        """Expose keyword (tsvector) search alone."""
        start = time.monotonic()
        query = request.query.strip()
        limit = request.limit or self._settings.default_limit

        results = await search_keyword(
            self._session, query, limit, include_stale=request.include_stale,
        )

        duration = time.monotonic() - start
        logger.info(
            "Keyword search completed",
            extra={"context": {
                "query": query,
                "method": "keyword",
                "results": len(results),
                "duration_s": round(duration, 4),
            }},
        )

        return SearchResult(
            results=results,
            total_found=len(results),
            query=query,
            method="keyword",
            duration_seconds=round(duration, 4),
        )
