"""Search result cache — PostgreSQL-backed with TTL expiration."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from quote_agent.models.search_cache import SearchCache
from quote_agent.search.models import SearchRequest, SearchResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def compute_cache_key(request: SearchRequest, method: str) -> str:
    """Deterministic SHA-256 hash of search parameters and method."""
    key_data = json.dumps(
        {
            "method": method,
            "query": request.query,
            "limit": request.limit,
            "include_stale": request.include_stale,
            "apply_proposability_filter": request.apply_proposability_filter,
        },
        sort_keys=True,
    )
    return hashlib.sha256(key_data.encode()).hexdigest()


async def get_cached(session: AsyncSession, cache_key: str) -> SearchResult | None:
    """Look up a cached result by key. Returns None if not found or expired."""
    stmt = select(SearchCache).where(SearchCache.cache_key == cache_key)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        logger.info(
            "Cache miss",
            extra={"context": {"cache_key": cache_key[:12], "reason": "not_found"}},
        )
        return None

    now = datetime.now(UTC)
    if row.expires_at <= now:
        logger.info(
            "Cache miss",
            extra={"context": {"cache_key": cache_key[:12], "reason": "expired"}},
        )
        return None

    logger.info(
        "Cache hit",
        extra={"context": {"cache_key": cache_key[:12], "query": row.query}},
    )
    return SearchResult.model_validate(row.results_json)


async def put_cached(
    session: AsyncSession,
    cache_key: str,
    request: SearchRequest,
    result: SearchResult,
    ttl_seconds: int,
) -> None:
    """Store a search result in the cache. Upserts on duplicate key."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    results_json = result.model_dump(mode="json")

    stmt = (
        pg_insert(SearchCache)
        .values(
            cache_key=cache_key,
            query=request.query,
            search_params={
                "limit": request.limit,
                "include_stale": request.include_stale,
                "apply_proposability_filter": request.apply_proposability_filter,
            },
            results_json=results_json,
            expires_at=expires_at,
        )
        .on_conflict_do_update(
            index_elements=["cache_key"],
            set_={
                "results_json": results_json,
                "expires_at": expires_at,
                "updated_at": now,
            },
        )
    )
    await session.execute(stmt)
    await session.flush()

    logger.info(
        "Cache stored",
        extra={"context": {"cache_key": cache_key[:12], "ttl_seconds": ttl_seconds}},
    )


async def invalidate_all(session: AsyncSession) -> int:
    """Delete all cache entries. Returns the number of entries removed."""
    stmt = delete(SearchCache)
    cursor_result = await session.execute(stmt)
    await session.flush()
    count = int(cursor_result.rowcount)  # type: ignore[attr-defined]

    logger.info(
        "Cache invalidated",
        extra={"context": {"entries_removed": count}},
    )
    return count


async def cleanup_expired(session: AsyncSession) -> int:
    """Delete expired cache entries. Returns the number of entries removed."""
    now = datetime.now(UTC)
    stmt = delete(SearchCache).where(SearchCache.expires_at < now)
    cursor_result = await session.execute(stmt)
    await session.flush()
    count = int(cursor_result.rowcount)  # type: ignore[attr-defined]

    logger.info(
        "Cache cleanup",
        extra={"context": {"expired_removed": count}},
    )
    return count


async def count_entries(session: AsyncSession) -> int:
    """Count total cache entries (for observability and max_entries enforcement)."""
    stmt = select(func.count()).select_from(SearchCache)
    result = await session.execute(stmt)
    return int(result.scalar_one())
