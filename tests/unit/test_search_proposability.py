"""Unit tests for proposability filter logic and integration with SearchEngine."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from quote_agent.config import ProposabilitySettings
from quote_agent.search.engine import SearchEngine
from quote_agent.search.models import ScoredProduct, SearchRequest
from quote_agent.search.proposability import build_proposability_clauses, is_product_proposable

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
    is_proposable: bool = True,
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
        match_source=source,
        is_proposable=is_proposable,
    )


def _make_embedding_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024])
    return adapter


def _make_engine() -> SearchEngine:
    session = AsyncMock()
    adapter = _make_embedding_adapter()
    with patch("quote_agent.search.engine.get_settings") as mock_settings:
        settings = MagicMock()
        settings.search.default_limit = 10
        settings.search.rrf_k = 60
        settings.search.hnsw_ef_search = 100
        settings.search_cache.enabled = False
        settings.proposability = ProposabilitySettings()
        mock_settings.return_value = settings
        return SearchEngine(session, adapter)


# ---------------------------------------------------------------------------
# ProposabilitySettings Tests
# ---------------------------------------------------------------------------


class TestProposabilitySettings:
    """AC-5: Configuration-driven proposability rules."""

    def test_defaults(self) -> None:
        """AC-5: ProposabilitySettings has correct defaults."""
        s = ProposabilitySettings()
        assert s.exclude_out_of_stock is True
        assert s.exclude_inactive is True
        assert s.excluded_categories == []

    def test_constructor_overrides(self) -> None:
        """AC-5: ProposabilitySettings accepts custom values."""
        s = ProposabilitySettings(
            exclude_out_of_stock=False,
            exclude_inactive=False,
            excluded_categories=["Obsolete", "Custom"],
        )
        assert s.exclude_out_of_stock is False
        assert s.exclude_inactive is False
        assert s.excluded_categories == ["Obsolete", "Custom"]

    def test_env_var_mapping(self) -> None:
        """AC-5: Env vars map correctly via pydantic-settings nested delimiter."""
        import os

        env = {
            "PROPOSABILITY__EXCLUDE_OUT_OF_STOCK": "false",
            "PROPOSABILITY__EXCLUDE_INACTIVE": "false",
            "PROPOSABILITY__EXCLUDED_CATEGORIES": '["Obsolete"]',
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
                assert s.proposability.exclude_out_of_stock is False
                assert s.proposability.exclude_inactive is False
                assert s.proposability.excluded_categories == ["Obsolete"]
            finally:
                get_settings.cache_clear()


# ---------------------------------------------------------------------------
# build_proposability_clauses Tests
# ---------------------------------------------------------------------------


class TestBuildProposabilityClauses:
    """AC-1, AC-5: SQL clause builder returns correct clauses per config."""

    def test_all_filters_enabled_returns_two_clauses(self) -> None:
        """AC-1: Default settings produce 2 clauses (active + stock)."""
        settings = ProposabilitySettings()
        clauses = build_proposability_clauses(settings)
        assert len(clauses) == 2

    def test_excluded_categories_adds_third_clause(self) -> None:
        """AC-5: excluded_categories setting adds a notin clause."""
        settings = ProposabilitySettings(excluded_categories=["Obsolete"])
        clauses = build_proposability_clauses(settings)
        assert len(clauses) == 3

    def test_no_filters_returns_empty(self) -> None:
        """AC-5: All filters disabled → no clauses."""
        settings = ProposabilitySettings(
            exclude_out_of_stock=False,
            exclude_inactive=False,
            excluded_categories=[],
        )
        clauses = build_proposability_clauses(settings)
        assert len(clauses) == 0

    def test_only_inactive_filter(self) -> None:
        """AC-5: Only exclude_inactive enabled → 1 clause."""
        settings = ProposabilitySettings(exclude_out_of_stock=False)
        clauses = build_proposability_clauses(settings)
        assert len(clauses) == 1

    def test_only_stock_filter(self) -> None:
        """AC-5: Only exclude_out_of_stock enabled → 1 clause."""
        settings = ProposabilitySettings(exclude_inactive=False)
        clauses = build_proposability_clauses(settings)
        assert len(clauses) == 1


# ---------------------------------------------------------------------------
# is_product_proposable Tests
# ---------------------------------------------------------------------------


class TestIsProductProposable:
    """AC-1, AC-4: Pure Python proposability check."""

    def test_active_in_stock_is_proposable(self) -> None:
        """AC-1: Active, in-stock product is proposable."""
        settings = ProposabilitySettings()
        assert is_product_proposable(True, "in_stock", "General", settings) is True

    def test_active_on_order_is_proposable(self) -> None:
        """AC-1: Active, on-order product is proposable."""
        settings = ProposabilitySettings()
        assert is_product_proposable(True, "on_order", "General", settings) is True

    def test_inactive_excluded_when_filter_enabled(self) -> None:
        """AC-1: Inactive product is not proposable when exclude_inactive=True."""
        settings = ProposabilitySettings()
        assert is_product_proposable(False, "in_stock", "General", settings) is False

    def test_out_of_stock_excluded_when_filter_enabled(self) -> None:
        """AC-1: Out-of-stock product is not proposable when exclude_out_of_stock=True."""
        settings = ProposabilitySettings()
        assert is_product_proposable(True, "out_of_stock", "General", settings) is False

    def test_excluded_category_not_proposable(self) -> None:
        """AC-5: Product in excluded category is not proposable."""
        settings = ProposabilitySettings(excluded_categories=["Obsolete"])
        assert is_product_proposable(True, "in_stock", "Obsolete", settings) is False

    def test_non_excluded_category_is_proposable(self) -> None:
        """AC-5: Product in non-excluded category is proposable."""
        settings = ProposabilitySettings(excluded_categories=["Obsolete"])
        assert is_product_proposable(True, "in_stock", "General", settings) is True

    def test_inactive_allowed_when_filter_disabled(self) -> None:
        """AC-5: Inactive product is proposable when exclude_inactive=False."""
        settings = ProposabilitySettings(exclude_inactive=False)
        assert is_product_proposable(False, "in_stock", "General", settings) is True

    def test_out_of_stock_allowed_when_filter_disabled(self) -> None:
        """AC-5: Out-of-stock product is proposable when exclude_out_of_stock=False."""
        settings = ProposabilitySettings(exclude_out_of_stock=False)
        assert is_product_proposable(True, "out_of_stock", "General", settings) is True


# ---------------------------------------------------------------------------
# SearchEngine + Proposability Filter Tests
# ---------------------------------------------------------------------------


_P = "quote_agent.search.engine"


class TestSearchEngineProposabilityFilter:
    """AC-1, AC-2, AC-4: Proposability filter integration with SearchEngine."""

    async def test_hybrid_search_passes_proposability_clauses(self) -> None:
        """AC-1: Hybrid search passes proposability clauses to sub-searches."""
        engine = _make_engine()
        sem_result = _make_scored(name="Tube", source="semantic")
        kw_result = _make_scored(name="Tube", source="keyword")

        with (
            patch(f"{_P}.is_reference_code", return_value=False),
            patch(f"{_P}.search_semantic", new_callable=AsyncMock, return_value=[sem_result]) as mock_sem,
            patch(f"{_P}.search_keyword", new_callable=AsyncMock, return_value=[kw_result]) as mock_kw,
        ):
            await engine.search_hybrid(SearchRequest(query="tubes inox"))

        # proposability_clauses should be passed (not None) when filter is on
        assert mock_sem.call_args.kwargs["proposability_clauses"] is not None
        assert mock_kw.call_args.kwargs["proposability_clauses"] is not None
        # proposability_settings should be None when filter is on (defaults are True)
        assert mock_sem.call_args.kwargs["proposability_settings"] is None
        assert mock_kw.call_args.kwargs["proposability_settings"] is None

    async def test_hybrid_search_bypasses_filter_when_disabled(self) -> None:
        """AC-4: apply_proposability_filter=False disables SQL filtering."""
        engine = _make_engine()
        sem_result = _make_scored(name="Tube", source="semantic")

        with (
            patch(f"{_P}.is_reference_code", return_value=False),
            patch(f"{_P}.search_semantic", new_callable=AsyncMock, return_value=[sem_result]) as mock_sem,
            patch(f"{_P}.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            await engine.search_hybrid(
                SearchRequest(query="tubes", apply_proposability_filter=False),
            )

        # proposability_clauses should be None when filter is off
        assert mock_sem.call_args.kwargs["proposability_clauses"] is None
        # proposability_settings should be passed when filter is off (for tagging)
        assert mock_sem.call_args.kwargs["proposability_settings"] is not None

    async def test_empty_results_when_all_filtered(self) -> None:
        """AC-2: Empty result set when all products are non-proposable."""
        engine = _make_engine()

        with (
            patch(f"{_P}.is_reference_code", return_value=False),
            patch(f"{_P}.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch(f"{_P}.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(SearchRequest(query="tubes inox"))

        assert result.results == []
        assert result.total_found == 0

    async def test_semantic_only_passes_proposability_clauses(self) -> None:
        """AC-1: Semantic-only search also applies proposability filter."""
        engine = _make_engine()

        with patch(f"{_P}.search_semantic", new_callable=AsyncMock, return_value=[]) as mock_sem:
            await engine.search_semantic_only(SearchRequest(query="tube"))

        assert mock_sem.call_args.kwargs["proposability_clauses"] is not None

    async def test_keyword_only_passes_proposability_clauses(self) -> None:
        """AC-1: Keyword-only search also applies proposability filter."""
        engine = _make_engine()

        with patch(f"{_P}.search_keyword", new_callable=AsyncMock, return_value=[]) as mock_kw:
            await engine.search_keyword_only(SearchRequest(query="tube"))

        assert mock_kw.call_args.kwargs["proposability_clauses"] is not None

    async def test_exact_ref_passes_proposability_clauses(self) -> None:
        """AC-1: Exact ref search also applies proposability filter."""
        engine = _make_engine()
        exact_result = _make_scored(name="Tube", source="exact_ref", score=1.0)

        with (
            patch(f"{_P}.is_reference_code", return_value=True),
            patch(f"{_P}.search_exact_ref", new_callable=AsyncMock, return_value=[exact_result]) as mock_exact,
        ):
            await engine.search_hybrid(SearchRequest(query="TUB-304L-025"))

        assert mock_exact.call_args.kwargs["proposability_clauses"] is not None

    async def test_is_proposable_set_when_filter_bypassed(self) -> None:
        """AC-4: When filter is bypassed, is_proposable computed via proposability_settings."""
        engine = _make_engine()
        non_prop = _make_scored(name="Inactive", source="semantic", is_proposable=False)

        with (
            patch(f"{_P}.is_reference_code", return_value=False),
            patch(f"{_P}.search_semantic", new_callable=AsyncMock, return_value=[non_prop]) as mock_sem,
            patch(f"{_P}.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(
                SearchRequest(query="tubes", apply_proposability_filter=False),
            )

        # proposability_settings is passed when filter is off
        assert mock_sem.call_args.kwargs["proposability_settings"] is not None
        assert len(result.results) == 1


# ---------------------------------------------------------------------------
# ScoredProduct.is_proposable field
# ---------------------------------------------------------------------------


class TestScoredProductProposable:
    """AC-4: ScoredProduct includes is_proposable field."""

    def test_default_is_proposable_true(self) -> None:
        """AC-4: is_proposable defaults to True."""
        sp = _make_scored()
        assert sp.is_proposable is True

    def test_is_proposable_can_be_set_false(self) -> None:
        """AC-4: is_proposable can be explicitly set to False."""
        sp = _make_scored(is_proposable=False)
        assert sp.is_proposable is False


# ---------------------------------------------------------------------------
# SearchRequest.apply_proposability_filter field
# ---------------------------------------------------------------------------


class TestSearchRequestProposability:
    """AC-4: SearchRequest includes apply_proposability_filter field."""

    def test_default_filter_enabled(self) -> None:
        """AC-4: apply_proposability_filter defaults to True."""
        req = SearchRequest(query="test")
        assert req.apply_proposability_filter is True

    def test_filter_can_be_disabled(self) -> None:
        """AC-4: apply_proposability_filter can be set to False."""
        req = SearchRequest(query="test", apply_proposability_filter=False)
        assert req.apply_proposability_filter is False
