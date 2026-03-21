"""Unit tests for the CLI score command."""

import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from quote_agent.agent.nodes.confidence_scorer import ConfidenceResult, ProductConfidence
from quote_agent.agent.nodes.router import EscalationContext, RoutingDecision
from quote_agent.cli.main import app

runner = CliRunner()


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


def _make_mock_run_score(
    confidence: ConfidenceResult | None = None,
    decision: RoutingDecision | None = None,
) -> AsyncMock:
    """Create a pre-configured AsyncMock for _run_score."""
    conf = confidence or _make_confidence_result()
    dec = decision or _make_routing_decision()
    return AsyncMock(return_value=(conf, dec))


class TestScoreFormattedOutput:
    """Formatted output displays expected fields."""

    def test_displays_confidence_and_tier_when_result_returned(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "0.90" in result.output
        assert "high" in result.output

    def test_displays_action_when_result_returned(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "proceed_to_draft" in result.output

    def test_displays_product_scores_when_present(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "REF-001" in result.output
        assert "Tube inox 304L DN50 6m" in result.output

    def test_displays_reasoning_when_result_returned(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "exact reference match" in result.output

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
        mock = _make_mock_run_score(
            confidence=_make_confidence_result(overall=0.30, tier="low"),
            decision=decision,
        )
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "Tube quelconque"])

        assert result.exit_code == 0
        assert "Escalation Context" in result.output
        assert "industrial tubing" in result.output
        assert "Clarify specs" in result.output


class TestScoreJsonOutput:
    """--json flag produces valid JSON."""

    def test_json_output_when_json_flag_set(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "--json", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["confidence"]["overall_confidence"] == 0.90
        assert data["routing"]["action"] == "proceed_to_draft"
        assert data["routing"]["tier"] == "high"


class TestScoreOptions:
    """Optional flags are passed through."""

    def test_passes_quantity_when_provided(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "--quantity", "10", "Tube inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["quantity"] == 10.0

    def test_passes_reference_when_provided(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "--reference", "REF-001", "Tube inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["reference"] == "REF-001"

    def test_passes_limit_when_provided(self) -> None:
        mock = _make_mock_run_score()
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "--limit", "3", "Tube inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["limit"] == 3


class TestScoreErrorHandling:
    """Graceful error on failure."""

    def test_displays_error_when_exception_raised(self) -> None:
        mock = AsyncMock(side_effect=RuntimeError("Connection failed"))
        with patch("quote_agent.cli.score._run_score", mock):
            result = runner.invoke(app, ["score", "Tube inox"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Connection failed" in result.output
