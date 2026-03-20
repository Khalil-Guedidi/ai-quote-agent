"""Hybrid search engine — orchestrates semantic + keyword search with RRF fusion."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from quote_agent.config import get_settings
from quote_agent.search.cache import (
    cleanup_expired,
    compute_cache_key,
    count_entries,
    get_cached,
    put_cached,
)
from quote_agent.search.keyword import is_reference_code, search_exact_ref, search_keyword
from quote_agent.search.models import ScoredProduct, SearchRequest, SearchResult
from quote_agent.search.proposability import build_proposability_clauses
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
        settings = get_settings()
        self._settings = settings.search
        self._proposability_settings = settings.proposability
        self._cache_settings = settings.search_cache
        self._cache_enabled = settings.search_cache.enabled

    async def _check_cache(self, request: SearchRequest, method: str) -> tuple[str, SearchResult | None]:
        """Check cache for a result. Returns (cache_key, cached_result_or_None)."""
        cache_key = compute_cache_key(request, method)
        cached = await get_cached(self._session, cache_key)
        return cache_key, cached

    async def _store_in_cache(self, cache_key: str, request: SearchRequest, result: SearchResult) -> None:
        """Store a result in cache, enforcing max_entries."""
        entry_count = await count_entries(self._session)
        if entry_count >= self._cache_settings.max_entries:
            await cleanup_expired(self._session)
            entry_count = await count_entries(self._session)
            if entry_count >= self._cache_settings.max_entries:
                return
        await put_cached(self._session, cache_key, request, result, self._cache_settings.ttl_seconds)

    async def search_hybrid(self, request: SearchRequest) -> SearchResult:
        """Run hybrid search: exact ref shortcut, then semantic + keyword with RRF fusion."""
        start = time.monotonic()

        if self._cache_enabled:
            cache_key, cached = await self._check_cache(request, "hybrid")
            if cached is not None:
                cached.from_cache = True
                cached.duration_seconds = round(time.monotonic() - start, 4)
                return cached
        query = request.query.strip()
        limit = request.limit or self._settings.default_limit
        prop_settings = self._proposability_settings
        prop_clauses = build_proposability_clauses(prop_settings) if request.apply_proposability_filter else None
        # When filter is off, pass settings so low-level functions can compute is_proposable
        tag_settings = None if request.apply_proposability_filter else prop_settings

        # Fast path: if query looks like a reference code, try exact match first
        if is_reference_code(query):
            exact_results = await search_exact_ref(
                self._session,
                query,
                limit,
                include_stale=request.include_stale,
                proposability_clauses=prop_clauses,
                proposability_settings=tag_settings,
            )
            if exact_results:
                duration = time.monotonic() - start
                logger.info(
                    "Exact reference search completed",
                    extra={
                        "context": {
                            "query": query,
                            "method": "exact_ref",
                            "results": len(exact_results),
                            "proposability_filter": request.apply_proposability_filter,
                            "duration_s": round(duration, 4),
                        }
                    },
                )
                exact_result = SearchResult(
                    results=exact_results,
                    total_found=len(exact_results),
                    query=query,
                    method="exact_ref",
                    duration_seconds=round(duration, 4),
                )

                if self._cache_enabled:
                    await self._store_in_cache(cache_key, request, exact_result)

                return exact_result

        # Generate query embedding
        embeddings = await self._embedding.embed_texts([query])
        query_embedding = embeddings[0]

        # Run semantic and keyword search sequentially (asyncpg doesn't support
        # concurrent queries on the same connection)
        prefetch_limit = limit * _PREFETCH_MULTIPLIER
        semantic_results = await search_semantic(
            self._session,
            query_embedding,
            prefetch_limit,
            include_stale=request.include_stale,
            proposability_clauses=prop_clauses,
            proposability_settings=tag_settings,
        )
        keyword_results = await search_keyword(
            self._session,
            query,
            prefetch_limit,
            include_stale=request.include_stale,
            proposability_clauses=prop_clauses,
            proposability_settings=tag_settings,
        )

        # Fuse results using RRF
        fused = _rrf_fuse(semantic_results, keyword_results, k=self._settings.rrf_k)
        final_results = fused[:limit]

        duration = time.monotonic() - start
        logger.info(
            "Hybrid search completed",
            extra={
                "context": {
                    "query": query,
                    "method": "hybrid",
                    "results": len(final_results),
                    "semantic_count": len(semantic_results),
                    "keyword_count": len(keyword_results),
                    "proposability_filter": request.apply_proposability_filter,
                    "duration_s": round(duration, 4),
                }
            },
        )

        result = SearchResult(
            results=final_results,
            total_found=len(fused),
            query=query,
            method="hybrid",
            duration_seconds=round(duration, 4),
        )

        if self._cache_enabled:
            await self._store_in_cache(cache_key, request, result)

        return result

    async def search_semantic_only(self, request: SearchRequest) -> SearchResult:
        """Expose semantic (vector) search alone."""
        start = time.monotonic()

        if self._cache_enabled:
            cache_key, cached = await self._check_cache(request, "semantic")
            if cached is not None:
                cached.from_cache = True
                cached.duration_seconds = round(time.monotonic() - start, 4)
                return cached

        query = request.query.strip()
        limit = request.limit or self._settings.default_limit
        prop_settings = self._proposability_settings
        prop_clauses = build_proposability_clauses(prop_settings) if request.apply_proposability_filter else None
        tag_settings = None if request.apply_proposability_filter else prop_settings

        embeddings = await self._embedding.embed_texts([query])
        query_embedding = embeddings[0]

        results = await search_semantic(
            self._session,
            query_embedding,
            limit,
            include_stale=request.include_stale,
            proposability_clauses=prop_clauses,
            proposability_settings=tag_settings,
        )

        duration = time.monotonic() - start
        logger.info(
            "Semantic search completed",
            extra={
                "context": {
                    "query": query,
                    "method": "semantic",
                    "results": len(results),
                    "proposability_filter": request.apply_proposability_filter,
                    "duration_s": round(duration, 4),
                }
            },
        )

        result = SearchResult(
            results=results,
            total_found=len(results),
            query=query,
            method="semantic",
            duration_seconds=round(duration, 4),
        )

        if self._cache_enabled:
            await self._store_in_cache(cache_key, request, result)

        return result

    async def search_keyword_only(self, request: SearchRequest) -> SearchResult:
        """Expose keyword (tsvector) search alone."""
        start = time.monotonic()

        if self._cache_enabled:
            cache_key, cached = await self._check_cache(request, "keyword")
            if cached is not None:
                cached.from_cache = True
                cached.duration_seconds = round(time.monotonic() - start, 4)
                return cached

        query = request.query.strip()
        limit = request.limit or self._settings.default_limit
        prop_settings = self._proposability_settings
        prop_clauses = build_proposability_clauses(prop_settings) if request.apply_proposability_filter else None
        tag_settings = None if request.apply_proposability_filter else prop_settings

        results = await search_keyword(
            self._session,
            query,
            limit,
            include_stale=request.include_stale,
            proposability_clauses=prop_clauses,
            proposability_settings=tag_settings,
        )

        duration = time.monotonic() - start
        logger.info(
            "Keyword search completed",
            extra={
                "context": {
                    "query": query,
                    "method": "keyword",
                    "results": len(results),
                    "proposability_filter": request.apply_proposability_filter,
                    "duration_s": round(duration, 4),
                }
            },
        )

        result = SearchResult(
            results=results,
            total_found=len(results),
            query=query,
            method="keyword",
            duration_seconds=round(duration, 4),
        )

        if self._cache_enabled:
            await self._store_in_cache(cache_key, request, result)

        return result
