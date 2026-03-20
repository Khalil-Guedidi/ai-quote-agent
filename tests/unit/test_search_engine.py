"""Unit tests for the hybrid search engine and RRF fusion."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.search.engine import SearchEngine, _rrf_fuse
from quote_agent.search.models import ScoredProduct, SearchRequest, SearchResult

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scored(
    *,
    name: str = "Product",
    rank: int = 1,
    score: float = 0.9,
    source: str = "semantic",
    product_id: uuid.UUID | None = None,
) -> ScoredProduct:
    return ScoredProduct(
        product_id=product_id or uuid.uuid4(),
        reference=f"REF-{name}",
        name=name,
        category="Test",
        description=None,
        unit_price=10.0,
        score=score,
        rank=rank,
        match_source=source,  # type: ignore[arg-type]
    )


def _make_embedding_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024])
    return adapter


# ---------------------------------------------------------------------------
# RRF Fusion Tests
# ---------------------------------------------------------------------------


class TestRRFFusion:
    """AC-1: RRF fusion combines two ranked lists correctly."""

    def test_rrf_fuse_overlapping_results(self) -> None:
        """AC-1: Products appearing in both lists get higher scores."""
        shared_id = uuid.uuid4()
        sem = [
            _make_scored(name="A", rank=1, source="semantic", product_id=shared_id),
            _make_scored(name="B", rank=2, source="semantic"),
        ]
        kw = [
            _make_scored(name="A", rank=1, source="keyword", product_id=shared_id),
            _make_scored(name="C", rank=2, source="keyword"),
        ]

        fused = _rrf_fuse(sem, kw, k=60)

        # Product A appears in both lists → highest score
        assert fused[0].product_id == shared_id
        assert fused[0].match_source == "hybrid"
        assert fused[0].rank == 1
        # Score = 1/(60+1) + 1/(60+1) = 2/61
        expected_score = 2.0 / 61.0
        assert abs(fused[0].score - expected_score) < 1e-10

    def test_rrf_fuse_disjoint_results(self) -> None:
        """AC-1: Disjoint results are interleaved by score."""
        sem = [_make_scored(name="A", rank=1, source="semantic")]
        kw = [_make_scored(name="B", rank=1, source="keyword")]

        fused = _rrf_fuse(sem, kw, k=60)

        assert len(fused) == 2
        # Both have same score: 1/(60+1)
        assert abs(fused[0].score - fused[1].score) < 1e-10
        assert fused[0].rank == 1
        assert fused[1].rank == 2

    def test_rrf_fuse_single_source_only(self) -> None:
        """AC-1: Single-source results still work."""
        sem = [
            _make_scored(name="A", rank=1, source="semantic"),
            _make_scored(name="B", rank=2, source="semantic"),
        ]

        fused = _rrf_fuse(sem, [], k=60)

        assert len(fused) == 2
        assert fused[0].rank == 1
        assert fused[1].rank == 2
        assert fused[0].score > fused[1].score

    def test_rrf_fuse_empty_lists(self) -> None:
        """AC-1: Empty inputs produce empty output."""
        fused = _rrf_fuse([], [])
        assert fused == []

    def test_rrf_fuse_rank_ordering(self) -> None:
        """AC-1: Fused results are sorted by score descending."""
        sem = [
            _make_scored(name="A", rank=1, source="semantic"),
            _make_scored(name="B", rank=2, source="semantic"),
            _make_scored(name="C", rank=3, source="semantic"),
        ]
        kw = [
            _make_scored(name="C", rank=1, source="keyword", product_id=sem[2].product_id),
            _make_scored(name="B", rank=2, source="keyword", product_id=sem[1].product_id),
        ]

        fused = _rrf_fuse(sem, kw, k=60)

        scores = [f.score for f in fused]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# SearchEngine Tests
# ---------------------------------------------------------------------------


class TestSearchEngineHybrid:
    """AC-1: Hybrid search orchestration."""

    @pytest.fixture()
    def engine(self) -> SearchEngine:
        session = AsyncMock()
        adapter = _make_embedding_adapter()
        with patch("quote_agent.search.engine.get_settings") as mock_settings:
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = False
            mock_settings.return_value = settings
            return SearchEngine(session, adapter)

    async def test_exact_ref_returned_first_when_reference_code_query(self, engine: SearchEngine) -> None:
        """AC-2: Reference code query returns exact match immediately."""
        exact_result = _make_scored(name="Tube", source="exact_ref", score=1.0)

        with patch("quote_agent.search.engine.is_reference_code", return_value=True), \
             patch("quote_agent.search.engine.search_exact_ref", new_callable=AsyncMock, return_value=[exact_result]):
            result = await engine.search_hybrid(SearchRequest(query="TUB-304L-025"))

        assert result.method == "exact_ref"
        assert result.results[0].score == 1.0
        assert result.results[0].match_source == "exact_ref"

    async def test_hybrid_path_when_not_reference_code(self, engine: SearchEngine) -> None:
        """AC-1: Non-reference queries go through semantic + keyword + RRF."""
        sem_result = _make_scored(name="Tube Inox", source="semantic")
        kw_result = _make_scored(name="Tube Rond", source="keyword")

        with patch("quote_agent.search.engine.is_reference_code", return_value=False), \
             patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[sem_result]), \
             patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[kw_result]):
            result = await engine.search_hybrid(SearchRequest(query="tubes inox"))

        assert result.method == "hybrid"
        assert len(result.results) > 0

    async def test_hybrid_falls_back_when_exact_ref_empty(self, engine: SearchEngine) -> None:
        """AC-2: Reference code query falls back to hybrid when no exact match."""
        sem_result = _make_scored(name="Tube", source="semantic")

        with patch("quote_agent.search.engine.is_reference_code", return_value=True), \
             patch("quote_agent.search.engine.search_exact_ref", new_callable=AsyncMock, return_value=[]), \
             patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[sem_result]), \
             patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]):
            result = await engine.search_hybrid(SearchRequest(query="TUB-UNKNOWN-999"))

        assert result.method == "hybrid"


class TestSearchEngineSemanticOnly:
    """AC-1: Semantic-only search path."""

    async def test_search_semantic_only_returns_vector_results(self) -> None:
        """AC-1: Semantic-only search uses vector search."""
        session = AsyncMock()
        adapter = _make_embedding_adapter()
        sem_result = _make_scored(name="Product", source="semantic")

        with patch("quote_agent.search.engine.get_settings") as mock_settings, \
             patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[sem_result]):
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = False
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)
            result = await engine.search_semantic_only(SearchRequest(query="tube"))

        assert result.method == "semantic"
        assert len(result.results) == 1


class TestSearchEngineKeywordOnly:
    """AC-1: Keyword-only search path."""

    async def test_search_keyword_only_returns_tsvector_results(self) -> None:
        """AC-1: Keyword-only search uses tsvector."""
        session = AsyncMock()
        adapter = _make_embedding_adapter()
        kw_result = _make_scored(name="Product", source="keyword")

        with patch("quote_agent.search.engine.get_settings") as mock_settings, \
             patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[kw_result]):
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search_cache.enabled = False
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)
            result = await engine.search_keyword_only(SearchRequest(query="tube"))

        assert result.method == "keyword"
        assert len(result.results) == 1


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestSearchEdgeCases:
    """AC-1: Edge case handling."""

    async def test_empty_query_returns_empty_results(self) -> None:
        """AC-1: Empty query produces no crash."""
        session = AsyncMock()
        adapter = _make_embedding_adapter()

        with patch("quote_agent.search.engine.get_settings") as mock_settings, \
             patch("quote_agent.search.engine.is_reference_code", return_value=False), \
             patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]), \
             patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]):
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = False
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)
            result = await engine.search_hybrid(SearchRequest(query=""))

        assert result.results == []
        assert result.total_found == 0

    def test_search_result_dto_construction(self) -> None:
        """AC-1: SearchResult DTO constructs correctly."""
        result = SearchResult(
            results=[],
            total_found=0,
            query="test",
            method="hybrid",
            duration_seconds=0.01,
        )
        assert result.query == "test"
        assert result.method == "hybrid"
        assert result.duration_seconds == 0.01

    def test_scored_product_dto_construction(self) -> None:
        """AC-1: ScoredProduct DTO constructs correctly."""
        pid = uuid.uuid4()
        sp = ScoredProduct(
            product_id=pid,
            reference="REF-001",
            name="Test Product",
            category="Cat",
            description="Desc",
            unit_price=42.0,
            score=0.95,
            rank=1,
            match_source="hybrid",
        )
        assert sp.product_id == pid
        assert sp.score == 0.95
        assert sp.match_source == "hybrid"


class TestSearchSettings:
    """AC-4: SearchSettings configuration."""

    def test_search_settings_defaults(self) -> None:
        """AC-4: SearchSettings has correct defaults."""
        from quote_agent.config import SearchSettings

        s = SearchSettings()
        assert s.default_limit == 10
        assert s.semantic_weight == 0.5
        assert s.keyword_weight == 0.5
        assert s.rrf_k == 60
        assert s.hnsw_ef_search == 100

    def test_search_settings_constructor_overrides(self) -> None:
        """AC-4: SearchSettings accepts custom values."""
        from quote_agent.config import SearchSettings

        s = SearchSettings(default_limit=20, rrf_k=100, hnsw_ef_search=200)
        assert s.default_limit == 20
        assert s.rrf_k == 100
        assert s.hnsw_ef_search == 200
