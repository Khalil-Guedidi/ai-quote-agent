"""Unit tests for jargon query expansion (Story 3.6)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.config import JargonSettings
from quote_agent.search.jargon import expand_query
from quote_agent.search.models import SearchRequest

# ---------------------------------------------------------------------------
# Default abbreviations for tests
# ---------------------------------------------------------------------------

_DEFAULT_ABBREVS: dict[str, str] = {
    "inox": "acier inoxydable stainless steel",
    "Ø": "diamètre diameter",
    "lg": "longueur length",
    "DN": "diamètre nominal nominal diameter",
    "PN": "pression nominale nominal pressure",
    "HM": "hexagonal mâle",
    "BLN": "boulon bolt",
    "RD": "rond round",
    "TB": "tube",
    "ml": "mètres linéaires linear meters",
}


# ---------------------------------------------------------------------------
# expand_query() tests
# ---------------------------------------------------------------------------


class TestExpandQuery:
    """AC-4: Query expansion logic."""

    def test_expansion_applies_when_abbreviation_found(self) -> None:
        """AC-4: Known abbreviation triggers expansion with full form appended."""
        result = expand_query("tubes inox 304L", _DEFAULT_ABBREVS)

        assert result.was_expanded is True
        assert "acier inoxydable stainless steel" in result.expanded_query
        assert result.original_query == "tubes inox 304L"
        assert any("inox" in e for e in result.expansions_applied)

    def test_expansion_preserves_original_tokens(self) -> None:
        """AC-4: Original query tokens are never replaced — expansion is additive."""
        result = expand_query("tubes inox 304L", _DEFAULT_ABBREVS)

        assert result.expanded_query.startswith("tubes inox 304L")

    def test_no_expansion_when_no_abbreviation_found(self) -> None:
        """AC-4: Query without abbreviations returns unchanged, was_expanded=False."""
        result = expand_query("acier carbone standard", _DEFAULT_ABBREVS)

        assert result.was_expanded is False
        assert result.expanded_query == "acier carbone standard"
        assert result.expansions_applied == []

    def test_case_insensitive_matching(self) -> None:
        """AC-4: Both 'INOX' and 'inox' trigger expansion."""
        result_upper = expand_query("tubes INOX 304L", _DEFAULT_ABBREVS)
        result_lower = expand_query("tubes inox 304L", _DEFAULT_ABBREVS)

        assert result_upper.was_expanded is True
        assert result_lower.was_expanded is True
        assert "acier inoxydable stainless steel" in result_upper.expanded_query
        assert "acier inoxydable stainless steel" in result_lower.expanded_query

    def test_no_expansion_inside_reference_code(self) -> None:
        """AC-4: Abbreviations inside reference codes (e.g., REF-DN100) are NOT expanded."""
        result = expand_query("REF-DN100", _DEFAULT_ABBREVS)

        assert result.was_expanded is False
        assert result.expanded_query == "REF-DN100"

    def test_unicode_diameter_symbol_expanded(self) -> None:
        """AC-4: 'Ø' Unicode character is matched and expanded correctly."""
        result = expand_query("tube Ø25", _DEFAULT_ABBREVS)

        assert result.was_expanded is True
        assert "diamètre diameter" in result.expanded_query

    def test_word_boundary_lg_not_in_belonging(self) -> None:
        """AC-4: 'lg' inside 'belonging' is NOT expanded."""
        result = expand_query("belonging to category", _DEFAULT_ABBREVS)

        # "lg" should not match inside "belonging"
        assert result.was_expanded is False

    def test_multiple_abbreviations_in_single_query(self) -> None:
        """AC-4: Multiple abbreviations in one query are all expanded."""
        result = expand_query("tubes inox 304L Ø25 lg 6m", _DEFAULT_ABBREVS)

        assert result.was_expanded is True
        assert "acier inoxydable stainless steel" in result.expanded_query
        assert "diamètre diameter" in result.expanded_query
        assert "longueur length" in result.expanded_query
        assert len(result.expansions_applied) >= 3

    def test_expansion_result_dataclass_frozen(self) -> None:
        """AC-4: JargonExpansionResult is immutable."""
        result = expand_query("tubes inox", _DEFAULT_ABBREVS)

        with pytest.raises(AttributeError):
            result.was_expanded = False  # type: ignore[misc]

    def test_dn_standalone_expanded(self) -> None:
        """AC-4: Standalone 'DN' (e.g., 'DN 100') is expanded."""
        result = expand_query("vanne DN 100", _DEFAULT_ABBREVS)

        assert result.was_expanded is True
        assert "diamètre nominal nominal diameter" in result.expanded_query

    def test_empty_query_returns_unchanged(self) -> None:
        """AC-4: Empty query returns empty, no crash."""
        result = expand_query("", _DEFAULT_ABBREVS)

        assert result.was_expanded is False
        assert result.expanded_query == ""

    def test_empty_abbreviations_dict(self) -> None:
        """AC-4: Empty abbreviation dict means no expansion."""
        result = expand_query("tubes inox 304L", {})

        assert result.was_expanded is False
        assert result.expanded_query == "tubes inox 304L"


# ---------------------------------------------------------------------------
# JargonSettings tests
# ---------------------------------------------------------------------------


class TestJargonSettings:
    """AC-5: JargonSettings configuration defaults and overrides."""

    def test_jargon_settings_defaults(self) -> None:
        """AC-5: JargonSettings has expansion_enabled=True and default abbreviations."""
        s = JargonSettings()

        assert s.expansion_enabled is True
        assert "inox" in s.abbreviations
        assert "Ø" in s.abbreviations
        assert len(s.abbreviations) == 10

    def test_jargon_settings_expansion_disabled(self) -> None:
        """AC-5: expansion_enabled can be set to False."""
        s = JargonSettings(expansion_enabled=False)

        assert s.expansion_enabled is False

    def test_jargon_settings_custom_abbreviations(self) -> None:
        """AC-5: Custom abbreviations override defaults."""
        s = JargonSettings(abbreviations={"foo": "bar baz"})

        assert s.abbreviations == {"foo": "bar baz"}

    def test_jargon_env_var_mapping(self) -> None:
        """AC-5: JARGON__EXPANSION_ENABLED env var maps correctly."""
        with patch.dict(
            "os.environ",
            {
                "DATABASE__URL": "postgresql://localhost/test",
                "LLM__API_KEY": "test-key",
                "ERP__URL": "http://localhost",
                "ERP__DATABASE": "test",
                "ERP__USERNAME": "admin",
                "ERP__API_KEY": "test",
                "EMAIL__IMAP_SERVER": "localhost",
                "EMAIL__USERNAME": "test",
                "EMAIL__PASSWORD": "test",
                "JARGON__EXPANSION_ENABLED": "false",
            },
        ):
            from quote_agent.config import Settings

            s = Settings()
            assert s.jargon.expansion_enabled is False


# ---------------------------------------------------------------------------
# SearchEngine integration tests (mocked)
# ---------------------------------------------------------------------------


class TestSearchEngineJargonIntegration:
    """AC-1, 2, 4, 5: SearchEngine integration with jargon expansion."""

    def _make_engine(self, *, expansion_enabled: bool = True) -> MagicMock:
        """Create a SearchEngine with mocked settings."""
        from quote_agent.search.engine import SearchEngine

        session = AsyncMock()
        adapter = MagicMock()
        adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024])

        with patch("quote_agent.search.engine.get_settings") as mock_settings:
            settings = MagicMock()
            settings.search.default_limit = 10
            settings.search.rrf_k = 60
            settings.search.hnsw_ef_search = 100
            settings.search_cache.enabled = False
            settings.proposability.exclude_out_of_stock = True
            settings.proposability.exclude_inactive = True
            settings.proposability.excluded_categories = []
            settings.jargon.expansion_enabled = expansion_enabled
            settings.jargon.abbreviations = _DEFAULT_ABBREVS
            mock_settings.return_value = settings
            engine = SearchEngine(session, adapter)

        return engine  # type: ignore[return-value]

    async def test_expanded_query_sent_to_embedding_when_enabled(self) -> None:
        """AC-4: When expansion enabled, expanded query is sent to embedding."""
        engine = self._make_engine(expansion_enabled=True)

        with (
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            await engine.search_hybrid(SearchRequest(query="tubes inox 304L"))

        # Verify expanded query was sent to embedding
        call_args = engine._embedding.embed_texts.call_args[0][0]
        assert "acier inoxydable stainless steel" in call_args[0]

    async def test_no_expansion_when_disabled(self) -> None:
        """AC-5: When expansion_enabled=False, no expansion occurs."""
        engine = self._make_engine(expansion_enabled=False)

        with (
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(SearchRequest(query="tubes inox 304L"))

        # Verify original query was sent to embedding (no expansion)
        call_args = engine._embedding.embed_texts.call_args[0][0]
        assert call_args[0] == "tubes inox 304L"
        assert result.jargon_expanded is False
        assert result.expanded_query is None

    async def test_jargon_expanded_metadata_set_on_result(self) -> None:
        """AC-2: jargon_expanded and expanded_query metadata set correctly on SearchResult."""
        engine = self._make_engine(expansion_enabled=True)

        with (
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(SearchRequest(query="tubes inox 304L"))

        assert result.jargon_expanded is True
        assert result.expanded_query is not None
        assert "acier inoxydable stainless steel" in result.expanded_query

    async def test_cache_key_uses_original_query(self) -> None:
        """AC-4: Cache key uses original query, not expanded query."""
        from quote_agent.search.cache import compute_cache_key

        request = SearchRequest(query="tubes inox 304L")

        key1 = compute_cache_key(request, "hybrid")

        # The cache key should be deterministic based on the original request
        key2 = compute_cache_key(request, "hybrid")
        assert key1 == key2

        # Different query should have different key
        request2 = SearchRequest(query="tubes inox 304L acier inoxydable stainless steel")
        key3 = compute_cache_key(request2, "hybrid")
        assert key1 != key3

    async def test_semantic_only_applies_jargon_expansion(self) -> None:
        """AC-4: Semantic-only search also applies jargon expansion."""
        engine = self._make_engine(expansion_enabled=True)

        with patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]):
            result = await engine.search_semantic_only(SearchRequest(query="tubes inox"))

        call_args = engine._embedding.embed_texts.call_args[0][0]
        assert "acier inoxydable stainless steel" in call_args[0]
        assert result.jargon_expanded is True

    async def test_keyword_only_applies_jargon_expansion(self) -> None:
        """AC-4: Keyword-only search also applies jargon expansion."""
        engine = self._make_engine(expansion_enabled=True)

        with patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]):
            result = await engine.search_keyword_only(SearchRequest(query="tubes inox"))

        # Verify keyword search result has jargon metadata
        assert result.jargon_expanded is True
        assert result.expanded_query is not None
        assert "acier inoxydable stainless steel" in result.expanded_query

    async def test_no_jargon_metadata_when_query_has_no_abbreviations(self) -> None:
        """AC-2: No jargon metadata when query has no abbreviations to expand."""
        engine = self._make_engine(expansion_enabled=True)

        with (
            patch("quote_agent.search.engine.is_reference_code", return_value=False),
            patch("quote_agent.search.engine.search_semantic", new_callable=AsyncMock, return_value=[]),
            patch("quote_agent.search.engine.search_keyword", new_callable=AsyncMock, return_value=[]),
        ):
            result = await engine.search_hybrid(SearchRequest(query="acier carbone standard"))

        assert result.jargon_expanded is False
        assert result.expanded_query is None
