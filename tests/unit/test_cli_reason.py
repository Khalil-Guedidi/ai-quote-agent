"""Unit tests for the CLI reason command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from quote_agent.agent.nodes.confidence_scorer import ConfidenceResult, ProductConfidence
from quote_agent.agent.nodes.reasoning_strategy import ReasoningResult, ReasoningStep
from quote_agent.agent.nodes.router import EscalationContext, RoutingDecision
from quote_agent.cli.main import app
from quote_agent.search.models import ScoredProduct, SearchResult

runner = CliRunner()


def _make_search_result() -> SearchResult:
    """Build a minimal SearchResult for testing."""
    return SearchResult(
        results=[
            ScoredProduct(
                product_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
                reference="REF-001",
                name="Tube inox 304L DN50 6m",
                category="Tubes",
                unit_price=45.0,
                score=0.92,
                rank=1,
                match_source="hybrid",
            ),
        ],
        total_found=1,
        query="Tube inox 304L DN50",
        method="hybrid",
        duration_seconds=0.15,
    )


def _make_reasoning_result(
    strategy: str = "direct_match",
) -> ReasoningResult:
    """Build a ReasoningResult for testing."""
    return ReasoningResult(
        strategy=strategy,  # type: ignore[arg-type]
        steps=[
            ReasoningStep(
                step_name="search",
                description="Direct hybrid search with limit=5",
                duration_ms=150,
                outcome="2 results found",
            ),
        ],
        search_result=_make_search_result(),
        reasoning_duration_ms=200,
    )


def _make_confidence_result(
    overall: float = 0.90,
    tier: str = "high",
) -> ConfidenceResult:
    """Build a ConfidenceResult for testing."""
    return ConfidenceResult(
        overall_confidence=overall,
        tier=tier,  # type: ignore[arg-type]
        product_scores=[
            ProductConfidence(
                product_id="00000000-0000-0000-0000-000000000001",
                reference="REF-001",
                name="Tube inox 304L DN50 6m",
                confidence=0.92,
                match_quality="Exact reference match",
                rank=1,
            ),
        ],
        reasoning=["High confidence: exact reference match"],
        scoring_duration_ms=200,
    )


def _make_routing_decision(
    action: str = "proceed_to_draft",
    tier: str = "high",
    confidence: float = 0.90,
) -> RoutingDecision:
    """Build a RoutingDecision for testing."""
    return RoutingDecision(
        action=action,  # type: ignore[arg-type]
        tier=tier,  # type: ignore[arg-type]
        confidence=confidence,
    )


def _make_mock_run_reason(
    reasoning: ReasoningResult | None = None,
    confidence: ConfidenceResult | None = None,
    decision: RoutingDecision | None = None,
) -> AsyncMock:
    """Create a pre-configured AsyncMock for _run_reason."""
    r = reasoning or _make_reasoning_result()
    c = confidence or _make_confidence_result()
    d = decision or _make_routing_decision()
    return AsyncMock(return_value=(r, c, d))


class TestReasonFormattedOutput:
    """Formatted output displays expected fields."""

    def test_displays_strategy_when_result_returned(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "direct_match" in result.output

    def test_displays_reasoning_steps_when_result_returned(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "search" in result.output
        assert "150ms" in result.output

    def test_displays_confidence_and_tier_when_result_returned(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "0.90" in result.output
        assert "high" in result.output

    def test_displays_action_when_result_returned(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "proceed_to_draft" in result.output

    def test_displays_product_scores_when_present(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "REF-001" in result.output

    def test_displays_escalation_context_when_escalated(self) -> None:
        decision = RoutingDecision(
            action="escalate",
            tier="low",
            confidence=0.30,
            escalation_context=EscalationContext(
                understood="Request for industrial tubing",
                uncertain="Exact specifications unclear",
                suggested_next_steps=["Clarify specs with client"],
            ),
        )
        mock = _make_mock_run_reason(
            confidence=_make_confidence_result(overall=0.30, tier="low"),
            decision=decision,
        )
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "Tube quelconque"])

        assert result.exit_code == 0
        assert "Escalation Context" in result.output
        assert "Clarify specs" in result.output


class TestReasonJsonOutput:
    """--json flag produces valid JSON."""

    def test_json_output_when_json_flag_set(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "--json", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["reasoning"]["strategy"] == "direct_match"
        assert data["confidence"]["overall_confidence"] == 0.90
        assert data["routing"]["action"] == "proceed_to_draft"

    def test_json_output_contains_reasoning_steps(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "--json", "Tube inox 304L DN50"])

        data = json.loads(result.output)
        assert len(data["reasoning"]["steps"]) == 1
        assert data["reasoning"]["steps"][0]["step_name"] == "search"


class TestReasonOptions:
    """Optional flags are passed through."""

    def test_passes_quantity_when_provided(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "--quantity", "10", "Tube inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["quantity"] == 10.0

    def test_passes_reference_when_provided(self) -> None:
        mock = _make_mock_run_reason()
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "--reference", "REF-001", "Tube inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["reference"] == "REF-001"


class TestReasonErrorHandling:
    """Graceful error on failure."""

    def test_displays_error_when_exception_raised(self) -> None:
        mock = AsyncMock(side_effect=RuntimeError("Connection failed"))
        with patch("quote_agent.cli.reason._run_reason", mock):
            result = runner.invoke(app, ["reason", "Tube inox"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Connection failed" in result.output
