"""Unit tests for search result cache (Story 3.5)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from quote_agent.search.cache import (
    cleanup_expired,
    compute_cache_key,
    count_entries,
    get_cached,
    invalidate_all,
    put_cached,
)
from quote_agent.search.models import ScoredProduct, SearchRequest, SearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(**kwargs: object) -> SearchRequest:
    defaults: dict[str, object] = {
        "query": "tube inox 304L",
        "limit": 10,
        "include_stale": False,
        "apply_proposability_filter": True,
    }
    defaults.update(kwargs)
    return SearchRequest(**defaults)  # type: ignore[arg-type]


def _make_result(**kwargs: object) -> SearchResult:
    defaults: dict[str, object] = {
        "results": [],
        "total_found": 0,
        "query": "tube inox 304L",
        "method": "hybrid",
        "duration_seconds": 0.123,
    }
    defaults.update(kwargs)
    return SearchResult(**defaults)  # type: ignore[arg-type]


def _make_scored_product() -> ScoredProduct:
    return ScoredProduct(
        product_id=uuid.uuid4(),
        reference="REF-001",
        name="Tube Inox 304L",
        category="Tubes",
        description="Tube en acier inoxydable 304L",
        unit_price=42.5,
        score=0.95,
        rank=1,
        match_source="hybrid",
        is_proposable=True,
    )


# ---------------------------------------------------------------------------
# compute_cache_key Tests
# ---------------------------------------------------------------------------


class TestComputeCacheKey:
    """AC-6: Cache key is deterministic based on search parameters."""

    def test_deterministic_same_input_same_key(self) -> None:
        """AC-6: Same input produces same key."""
        req = _make_request()
        assert compute_cache_key(req, "hybrid") == compute_cache_key(req, "hybrid")

    def test_deterministic_equivalent_requests(self) -> None:
        """AC-6: Two identical requests produce the same key."""
        req1 = _make_request()
        req2 = _make_request()
        assert compute_cache_key(req1, "hybrid") == compute_cache_key(req2, "hybrid")

    def test_different_query_different_key(self) -> None:
        """AC-6: Changing query changes the key."""
        req1 = _make_request(query="tube inox")
        req2 = _make_request(query="plaque aluminium")
        assert compute_cache_key(req1, "hybrid") != compute_cache_key(req2, "hybrid")

    def test_different_limit_different_key(self) -> None:
        """AC-6: Changing limit changes the key."""
        req1 = _make_request(limit=10)
        req2 = _make_request(limit=20)
        assert compute_cache_key(req1, "hybrid") != compute_cache_key(req2, "hybrid")

    def test_different_include_stale_different_key(self) -> None:
        """AC-6: Changing include_stale changes the key."""
        req1 = _make_request(include_stale=False)
        req2 = _make_request(include_stale=True)
        assert compute_cache_key(req1, "hybrid") != compute_cache_key(req2, "hybrid")

    def test_different_proposability_filter_different_key(self) -> None:
        """AC-6: Changing apply_proposability_filter changes the key."""
        req1 = _make_request(apply_proposability_filter=True)
        req2 = _make_request(apply_proposability_filter=False)
        assert compute_cache_key(req1, "hybrid") != compute_cache_key(req2, "hybrid")

    def test_different_method_different_key(self) -> None:
        """AC-6: Changing search method changes the key."""
        req = _make_request()
        assert compute_cache_key(req, "hybrid") != compute_cache_key(req, "semantic")
        assert compute_cache_key(req, "hybrid") != compute_cache_key(req, "keyword")
        assert compute_cache_key(req, "semantic") != compute_cache_key(req, "keyword")

    def test_key_is_sha256_hex(self) -> None:
        """AC-6: Cache key is a 64-char hex string (SHA-256)."""
        key = compute_cache_key(_make_request(), "hybrid")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


# ---------------------------------------------------------------------------
# get_cached Tests
# ---------------------------------------------------------------------------


class TestGetCached:
    """AC-1, AC-3: Cache lookup with TTL checking."""

    async def test_returns_none_when_key_not_found(self) -> None:
        """AC-1: Cache miss returns None when key doesn't exist."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        result = await get_cached(session, "nonexistent_key_abc")
        assert result is None

    async def test_returns_none_when_entry_expired(self) -> None:
        """AC-3: Expired cache entry returns None and logs reason 'expired'."""
        from datetime import UTC, datetime, timedelta

        expired_row = MagicMock()
        expired_row.expires_at = datetime.now(UTC) - timedelta(seconds=60)
        expired_row.query = "tube inox 304L"

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expired_row
        session.execute.return_value = result_mock

        result = await get_cached(session, "expired_key_abc")
        assert result is None

    async def test_returns_search_result_when_valid_entry_exists(self) -> None:
        """AC-1: Valid cache entry returns deserialized SearchResult."""
        from datetime import UTC, datetime, timedelta

        search_result = _make_result(
            results=[_make_scored_product()],
            total_found=1,
        )
        row = MagicMock()
        row.query = "tube inox 304L"
        row.results_json = search_result.model_dump(mode="json")
        row.expires_at = datetime.now(UTC) + timedelta(hours=1)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        session.execute.return_value = result_mock

        result = await get_cached(session, "valid_key_abc123")
        assert result is not None
        assert result.total_found == 1
        assert result.query == "tube inox 304L"
        assert len(result.results) == 1


# ---------------------------------------------------------------------------
# put_cached Tests
# ---------------------------------------------------------------------------


class TestPutCached:
    """AC-2: Cache storage with upsert."""

    async def test_stores_result_in_cache(self) -> None:
        """AC-2: put_cached executes an upsert statement and flushes."""
        session = AsyncMock()
        request = _make_request()
        result = _make_result()

        await put_cached(session, "test_key_abc", request, result, 3600)

        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    async def test_upserts_on_duplicate_key(self) -> None:
        """AC-2: put_cached uses ON CONFLICT DO UPDATE (upsert)."""
        session = AsyncMock()
        request = _make_request()
        result = _make_result()

        # Call twice with same key — should not raise
        await put_cached(session, "same_key_123", request, result, 3600)
        await put_cached(session, "same_key_123", request, result, 3600)

        assert session.execute.await_count == 2


# ---------------------------------------------------------------------------
# invalidate_all Tests
# ---------------------------------------------------------------------------


class TestInvalidateAll:
    """AC-4: Full cache invalidation."""

    async def test_removes_all_entries_and_returns_count(self) -> None:
        """AC-4: invalidate_all DELETEs all rows and returns count."""
        session = AsyncMock()
        cursor = MagicMock()
        cursor.rowcount = 5
        session.execute.return_value = cursor

        count = await invalidate_all(session)

        assert count == 5
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# cleanup_expired Tests
# ---------------------------------------------------------------------------


class TestCleanupExpired:
    """AC-3: Expired cache cleanup."""

    async def test_removes_only_expired_entries(self) -> None:
        """AC-3: cleanup_expired DELETEs WHERE expires_at < now()."""
        session = AsyncMock()
        cursor = MagicMock()
        cursor.rowcount = 3
        session.execute.return_value = cursor

        count = await cleanup_expired(session)

        assert count == 3
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# count_entries Tests
# ---------------------------------------------------------------------------


class TestCountEntries:
    """Observability: count cache entries."""

    async def test_returns_count(self) -> None:
        """count_entries returns the COUNT from the DB."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 42
        session.execute.return_value = result_mock

        count = await count_entries(session)
        assert count == 42


# ---------------------------------------------------------------------------
# SearchEngine Cache Integration Tests
# ---------------------------------------------------------------------------


def _make_embedding_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024])
    return adapter


class TestSearchEngineCacheIntegration:
    """AC-1, AC-2, AC-5: Cache integration in SearchEngine."""

    async def test_cache_hit_skips_search(self) -> None:
        """AC-1: Cache hit returns cached result, skipping search execution."""
        from quote_agent.search.engine import SearchEngine

        session = AsyncMock()
        adapter = _make_embedding_adapter()
        cached_result = _make_result(total_found=5, method="hybrid")

        with patch("quote_agent.search.engine.get_settings") as mock_settings:
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = True
            settings.search_cache.ttl_seconds = 3600
            settings.search_cache.max_entries = 10000
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)

        with (
            patch("quote_agent.search.engine.get_cached", new_callable=AsyncMock, return_value=cached_result),
            patch("quote_agent.search.engine.compute_cache_key", return_value="test_key"),
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock) as mock_sem,
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock) as mock_kw,
        ):
            result = await engine.search_hybrid(_make_request())

        assert result.from_cache is True
        mock_sem.assert_not_awaited()
        mock_kw.assert_not_awaited()

    async def test_cache_miss_executes_search_and_stores(self) -> None:
        """AC-2: Cache miss runs search normally and stores result."""
        from quote_agent.search.engine import SearchEngine

        session = AsyncMock()
        adapter = _make_embedding_adapter()
        sem_result = _make_scored_product()

        with patch("quote_agent.search.engine.get_settings") as mock_settings:
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = True
            settings.search_cache.ttl_seconds = 3600
            settings.search_cache.max_entries = 10000
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)

        with (
            patch("quote_agent.search.engine.get_cached", new_callable=AsyncMock, return_value=None),
            patch("quote_agent.search.engine.compute_cache_key", return_value="test_key"),
            patch("quote_agent.search.engine.count_entries", new_callable=AsyncMock, return_value=0),
            patch("quote_agent.search.engine.put_cached", new_callable=AsyncMock) as mock_put,
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[sem_result]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(_make_request())

        assert result.from_cache is False
        mock_put.assert_awaited_once()

    async def test_cache_disabled_skips_all_cache_logic(self) -> None:
        """AC-5: When enabled=False, no cache interaction occurs."""
        from quote_agent.search.engine import SearchEngine

        session = AsyncMock()
        adapter = _make_embedding_adapter()

        with patch("quote_agent.search.engine.get_settings") as mock_settings:
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = False
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)

        with (
            patch("quote_agent.search.engine.get_cached", new_callable=AsyncMock) as mock_get,
            patch("quote_agent.search.engine.put_cached", new_callable=AsyncMock) as mock_put,
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(_make_request())

        assert result.from_cache is False
        mock_get.assert_not_awaited()
        mock_put.assert_not_awaited()

    async def test_from_cache_true_on_cache_hit(self) -> None:
        """AC-1: from_cache flag is True on cache hit."""
        from quote_agent.search.engine import SearchEngine

        session = AsyncMock()
        adapter = _make_embedding_adapter()
        cached_result = _make_result()

        with patch("quote_agent.search.engine.get_settings") as mock_settings:
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = True
            settings.search_cache.ttl_seconds = 3600
            settings.search_cache.max_entries = 10000
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)

        with (
            patch("quote_agent.search.engine.get_cached", new_callable=AsyncMock, return_value=cached_result),
            patch("quote_agent.search.engine.compute_cache_key", return_value="k"),
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(_make_request())

        assert result.from_cache is True

    async def test_from_cache_false_on_cache_miss(self) -> None:
        """AC-2: from_cache flag is False on cache miss."""
        from quote_agent.search.engine import SearchEngine

        session = AsyncMock()
        adapter = _make_embedding_adapter()

        with patch("quote_agent.search.engine.get_settings") as mock_settings:
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = True
            settings.search_cache.ttl_seconds = 3600
            settings.search_cache.max_entries = 10000
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)

        with (
            patch("quote_agent.search.engine.get_cached", new_callable=AsyncMock, return_value=None),
            patch("quote_agent.search.engine.compute_cache_key", return_value="k"),
            patch("quote_agent.search.engine.count_entries", new_callable=AsyncMock, return_value=0),
            patch("quote_agent.search.engine.put_cached", new_callable=AsyncMock),
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(_make_request())

        assert result.from_cache is False


# ---------------------------------------------------------------------------
# SearchCacheSettings Tests
# ---------------------------------------------------------------------------


class TestSearchCacheSettings:
    """AC-5: SearchCacheSettings configuration."""

    def test_defaults(self) -> None:
        """AC-5: SearchCacheSettings has correct defaults."""
        from quote_agent.config import SearchCacheSettings

        s = SearchCacheSettings()
        assert s.enabled is True
        assert s.ttl_seconds == 3600
        assert s.max_entries == 10_000

    def test_constructor_overrides(self) -> None:
        """AC-5: SearchCacheSettings accepts custom values."""
        from quote_agent.config import SearchCacheSettings

        s = SearchCacheSettings(enabled=False, ttl_seconds=1800, max_entries=5000)
        assert s.enabled is False
        assert s.ttl_seconds == 1800
        assert s.max_entries == 5000

    def test_env_var_mapping(self) -> None:
        """AC-5: Env vars map correctly via pydantic-settings nested delimiter."""
        import os

        env = {
            "SEARCH_CACHE__ENABLED": "false",
            "SEARCH_CACHE__TTL_SECONDS": "7200",
            "SEARCH_CACHE__MAX_ENTRIES": "5000",
            # Required fields that have no defaults — provide dummy values for CI
            "DATABASE__URL": "postgresql+asyncpg://test:test@localhost:5432/test",
            "LLM__API_KEY": "fake-key",
            "ERP__URL": "http://localhost:8069",
            "ERP__DATABASE": "test",
            "ERP__USERNAME": "test",
            "ERP__API_KEY": "fake-key",
            "EMAIL__IMAP_SERVER": "localhost",
            "EMAIL__USERNAME": "test",
            "EMAIL__PASSWORD": "fake",
        }
        with patch.dict(os.environ, env, clear=False):
            from quote_agent.config import get_settings

            get_settings.cache_clear()
            try:
                s = get_settings()
                assert s.search_cache.enabled is False
                assert s.search_cache.ttl_seconds == 7200
                assert s.search_cache.max_entries == 5000
            finally:
                get_settings.cache_clear()
