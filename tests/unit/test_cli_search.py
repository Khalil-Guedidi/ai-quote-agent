"""Unit tests for the CLI search command."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from quote_agent.cli.main import app
from quote_agent.search.models import ScoredProduct, SearchResult

runner = CliRunner()


def _make_search_result(
    *,
    query: str = "tubes inox",
    method: str = "hybrid",
    n_results: int = 2,
    from_cache: bool = False,
) -> SearchResult:
    """Build a SearchResult with N ScoredProducts for testing."""
    products = [
        ScoredProduct(
            product_id=uuid.uuid4(),
            reference=f"REF-{i:03d}",
            name=f"Product {i}",
            category="Tubes",
            unit_price=10.0 * i,
            score=0.0300 - i * 0.001,
            rank=i + 1,
            match_source="hybrid",
            is_proposable=i % 2 == 0,
        )
        for i in range(n_results)
    ]
    return SearchResult(
        results=products,
        total_found=n_results,
        query=query,
        method=method,
        duration_seconds=0.1234,
        from_cache=from_cache,
    )


@pytest.fixture()
def mock_run_search() -> AsyncMock:
    """Provide a pre-configured AsyncMock for _run_search."""
    return AsyncMock(return_value=_make_search_result())


class TestSearchFormattedOutput:
    """AC-1: Formatted output displays expected fields."""

    def test_displays_query_and_metadata_when_results_returned(self, mock_run_search: AsyncMock) -> None:
        with patch("quote_agent.cli.search._run_search", mock_run_search):
            result = runner.invoke(app, ["search", "tubes inox"])

        assert result.exit_code == 0
        assert 'Search: "tubes inox"' in result.output
        assert "Method: hybrid" in result.output
        assert "Results: 2 / 2" in result.output
        assert "Duration: 0.1234s" in result.output

    def test_displays_product_fields_when_results_returned(self, mock_run_search: AsyncMock) -> None:
        with patch("quote_agent.cli.search._run_search", mock_run_search):
            result = runner.invoke(app, ["search", "tubes inox"])

        assert result.exit_code == 0
        assert "REF-000" in result.output
        assert "Product 0" in result.output
        assert "Tubes" in result.output
        assert "0.0300" in result.output

    def test_displays_proposable_indicators_when_results_returned(self, mock_run_search: AsyncMock) -> None:
        with patch("quote_agent.cli.search._run_search", mock_run_search):
            result = runner.invoke(app, ["search", "tubes inox"])

        assert result.exit_code == 0
        # Product 0 is proposable (✓), Product 1 is not (✗)
        assert "✓" in result.output
        assert "✗" in result.output

    def test_displays_cached_indicator_when_from_cache(self) -> None:
        sr = _make_search_result(from_cache=True)
        mock = AsyncMock(return_value=sr)
        with patch("quote_agent.cli.search._run_search", mock):
            result = runner.invoke(app, ["search", "tubes inox"])

        assert result.exit_code == 0
        assert "(cached)" in result.output


class TestSearchJsonOutput:
    """AC-1: --json flag produces valid JSON matching SearchResult schema."""

    def test_json_output_when_json_flag_set(self, mock_run_search: AsyncMock) -> None:
        with patch("quote_agent.cli.search._run_search", mock_run_search):
            result = runner.invoke(app, ["search", "--json", "tubes inox"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["query"] == "tubes inox"
        assert data["method"] == "hybrid"
        assert len(data["results"]) == 2
        assert "reference" in data["results"][0]
        assert "score" in data["results"][0]
        assert "is_proposable" in data["results"][0]

    def test_json_output_matches_search_result_schema(self, mock_run_search: AsyncMock) -> None:
        with patch("quote_agent.cli.search._run_search", mock_run_search):
            result = runner.invoke(app, ["search", "--json", "tubes inox"])

        assert result.exit_code == 0
        # Validate the output can be parsed back into a SearchResult
        parsed = SearchResult.model_validate_json(result.output)
        assert parsed.query == "tubes inox"
        assert len(parsed.results) == 2


class TestSearchMethodDispatch:
    """AC-1: --method option dispatches to correct SearchEngine method."""

    def test_dispatches_hybrid_when_default_method(self) -> None:
        mock = AsyncMock(return_value=_make_search_result(method="hybrid"))
        with patch("quote_agent.cli.search._run_search", mock):
            result = runner.invoke(app, ["search", "tubes inox"])

        assert result.exit_code == 0
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs["method"] == "hybrid"

    def test_dispatches_semantic_when_semantic_method(self) -> None:
        mock = AsyncMock(return_value=_make_search_result(method="semantic"))
        with patch("quote_agent.cli.search._run_search", mock):
            result = runner.invoke(app, ["search", "--method", "semantic", "tubes inox"])

        assert result.exit_code == 0
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs["method"] == "semantic"

    def test_dispatches_keyword_when_keyword_method(self) -> None:
        mock = AsyncMock(return_value=_make_search_result(method="keyword"))
        with patch("quote_agent.cli.search._run_search", mock):
            result = runner.invoke(app, ["search", "--method", "keyword", "tubes inox"])

        assert result.exit_code == 0
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs["method"] == "keyword"

    def test_exits_with_error_when_invalid_method(self) -> None:
        result = runner.invoke(app, ["search", "--method", "invalid", "tubes inox"])
        assert result.exit_code == 1
        assert "Invalid method" in result.output


class TestSearchNoFilter:
    """AC-1: --no-filter sets apply_proposability_filter=False on SearchRequest."""

    def test_no_filter_passes_flag_when_set(self) -> None:
        mock = AsyncMock(return_value=_make_search_result())
        with patch("quote_agent.cli.search._run_search", mock):
            result = runner.invoke(app, ["search", "--no-filter", "tubes inox"])

        assert result.exit_code == 0
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs["no_filter"] is True

    def test_filter_enabled_by_default_when_no_flag(self) -> None:
        mock = AsyncMock(return_value=_make_search_result())
        with patch("quote_agent.cli.search._run_search", mock):
            result = runner.invoke(app, ["search", "tubes inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["no_filter"] is False


class TestSearchErrorHandling:
    """AC-1: Graceful error when DB is unreachable."""

    def test_displays_error_when_db_unreachable(self) -> None:
        mock = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))
        with patch("quote_agent.cli.search._run_search", mock):
            result = runner.invoke(app, ["search", "tubes inox"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Connection refused" in result.output
