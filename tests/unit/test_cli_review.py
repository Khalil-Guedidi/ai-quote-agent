"""Unit tests for the CLI review command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from quote_agent.agent.nodes.compliance_checker import ComplianceCheckResult, ComplianceFlag
from quote_agent.agent.nodes.self_reviewer import SelfReviewResult, ValidationStep
from quote_agent.cli.main import app

runner = CliRunner()


def _make_review_result(
    approved: bool = True,
    failure_reasons: list[str] | None = None,
    anomaly_flags: list[str] | None = None,
) -> SelfReviewResult:
    """Build a SelfReviewResult for testing."""
    steps = [
        ValidationStep(
            step_name="catalog_validation", passed=True,
            detail="All 2 product IDs verified in catalog", duration_ms=5,
        ),
        ValidationStep(
            step_name="quantity_plausibility", passed=True,
            detail="All quantities within plausible range", duration_ms=0,
        ),
        ValidationStep(
            step_name="coherence_validation", passed=approved,
            detail="Products coherent with request" if approved else "Incoherence detected: mismatch",
            duration_ms=120,
        ),
        ValidationStep(
            step_name="output_integrity", passed=True,
            detail="Output integrity verified", duration_ms=100,
        ),
    ]
    return SelfReviewResult(
        approved=approved,
        steps=steps,
        failure_reasons=failure_reasons or [],
        review_duration_ms=225,
        anomaly_flags=anomaly_flags or [],
    )


def _make_compliant_result() -> ComplianceCheckResult:
    """Build a compliant ComplianceCheckResult."""
    return ComplianceCheckResult(is_compliant=True, flags=[], check_duration_ms=100)


def _make_blocked_compliance_result() -> ComplianceCheckResult:
    """Build a blocked ComplianceCheckResult."""
    return ComplianceCheckResult(
        is_compliant=False,
        flags=[
            ComplianceFlag(
                flag_type="sanctioned_entity",
                severity="block",
                detail="Entity 'DPRK Trading Corp' matches OFAC SDN",
                matched_term="DPRK Trading",
            ),
        ],
        check_duration_ms=500,
    )


class TestReviewFormattedOutputApproved:
    """Formatted output for approved case."""

    def test_displays_approved_verdict(self) -> None:
        review = _make_review_result(approved=True)
        compliance = _make_compliant_result()
        mock = AsyncMock(return_value=(review, compliance))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "APPROVED" in result.output

    def test_displays_validation_steps(self) -> None:
        review = _make_review_result(approved=True)
        compliance = _make_compliant_result()
        mock = AsyncMock(return_value=(review, compliance))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "catalog_validation" in result.output
        assert "quantity_plausibility" in result.output
        assert "coherence_validation" in result.output
        assert "output_integrity" in result.output
        assert "PASS" in result.output


class TestReviewFormattedOutputRejected:
    """Formatted output for rejected case with failure reasons."""

    def test_displays_rejected_verdict(self) -> None:
        review = _make_review_result(
            approved=False,
            failure_reasons=["Incoherence detected: Product 1 is a valve, not a tube"],
        )
        compliance = _make_compliant_result()
        mock = AsyncMock(return_value=(review, compliance))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "REJECTED" in result.output
        assert "Failure Reasons" in result.output
        assert "valve" in result.output

    def test_displays_anomaly_flags_when_present(self) -> None:
        review = _make_review_result(
            approved=False,
            failure_reasons=["Anomalies detected"],
            anomaly_flags=["Suspicious product name pattern"],
        )
        compliance = _make_compliant_result()
        mock = AsyncMock(return_value=(review, compliance))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "Anomaly Flags" in result.output
        assert "Suspicious" in result.output


class TestReviewJsonOutput:
    """--json flag produces valid JSON."""

    def test_json_output_when_json_flag_set(self) -> None:
        review = _make_review_result(approved=True)
        compliance = _make_compliant_result()
        mock = AsyncMock(return_value=(review, compliance))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "--json", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["review"]["approved"] is True
        assert len(data["review"]["steps"]) == 4
        assert data["review"]["review_duration_ms"] == 225
        assert data["compliance"]["is_compliant"] is True


class TestReviewErrorHandling:
    """Graceful error on failure."""

    def test_displays_error_when_exception_raised(self) -> None:
        mock = AsyncMock(side_effect=RuntimeError("Connection failed"))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "Tube inox"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Connection failed" in result.output


class TestReviewPipelineIncludesCompliance:
    """AC-8: Review pipeline includes compliance step."""

    def test_review_pipeline_includes_compliance_step(self) -> None:
        """AC-8: Review output includes compliance section."""
        review = _make_review_result(approved=True)
        compliance = _make_compliant_result()
        mock = AsyncMock(return_value=(review, compliance))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "Compliance" in result.output
        assert "COMPLIANT" in result.output

    def test_compliance_block_overrides_self_review_approved(self) -> None:
        """AC-8: Compliance block overrides self-review approved."""
        review = _make_review_result(approved=True)
        compliance = _make_blocked_compliance_result()
        mock = AsyncMock(return_value=(review, compliance))
        with patch("quote_agent.cli.review._run_review", mock):
            result = runner.invoke(app, ["review", "Steel plates", "--client", "DPRK Corp"])

        assert result.exit_code == 0
        assert "APPROVED" in result.output  # self-review approved
        assert "BLOCKED" in result.output  # but compliance blocks
        assert "cannot be auto-processed" in result.output
