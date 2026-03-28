"""Unit tests for the CLI compliance command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from quote_agent.agent.nodes.compliance_checker import (
    ComplianceCheckResult,
    ComplianceFlag,
)
from quote_agent.cli.main import app

runner = CliRunner()


def _make_compliant_result() -> ComplianceCheckResult:
    """Build a compliant ComplianceCheckResult."""
    return ComplianceCheckResult(
        is_compliant=True,
        flags=[],
        check_duration_ms=150,
    )


def _make_flagged_result() -> ComplianceCheckResult:
    """Build a flagged (export control) ComplianceCheckResult."""
    return ComplianceCheckResult(
        is_compliant=False,
        flags=[
            ComplianceFlag(
                flag_type="export_control",
                severity="warning",
                detail="[nuclear] Zirconium tubes are controlled under EU Dual-Use Regulation",
                matched_term="zirconium grade nucléaire",
            ),
        ],
        check_duration_ms=1842,
    )


def _make_blocked_result() -> ComplianceCheckResult:
    """Build a blocked (sanctioned entity) ComplianceCheckResult."""
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
        check_duration_ms=980,
    )


class TestComplianceFormattedOutputCompliant:
    """AC-8: Formatted output for compliant case."""

    def test_displays_compliant_verdict(self) -> None:
        """AC-8: Compliant result displays COMPLIANT verdict."""
        mock = AsyncMock(return_value=_make_compliant_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "COMPLIANT" in result.output
        assert "150ms" in result.output

    def test_displays_no_flags_message(self) -> None:
        """AC-8: Compliant result shows no flags message."""
        mock = AsyncMock(return_value=_make_compliant_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "Tube inox 304L DN50"])

        assert "No compliance flags detected" in result.output


class TestComplianceFormattedOutputFlagged:
    """AC-8: Formatted output for flagged case with export control."""

    def test_displays_flagged_verdict(self) -> None:
        """AC-8: Flagged result displays FLAGGED verdict."""
        mock = AsyncMock(return_value=_make_flagged_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "tubes zirconium grade nucléaire"])

        assert result.exit_code == 0
        assert "FLAGGED" in result.output

    def test_displays_export_control_flag_details(self) -> None:
        """AC-8: Export control flag shows type, severity, detail, matched term."""
        mock = AsyncMock(return_value=_make_flagged_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "tubes zirconium grade nucléaire"])

        assert "export_control" in result.output
        assert "WARNING" in result.output
        assert "nuclear" in result.output
        assert "zirconium grade nucléaire" in result.output


class TestComplianceFormattedOutputBlocked:
    """AC-8: Formatted output for blocked case with sanctioned entity."""

    def test_displays_blocked_verdict(self) -> None:
        """AC-8: Blocked result displays BLOCKED verdict."""
        mock = AsyncMock(return_value=_make_blocked_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "Steel plates", "--client", "DPRK Trading Corp"])

        assert result.exit_code == 0
        assert "BLOCKED" in result.output

    def test_displays_sanctioned_entity_flag_details(self) -> None:
        """AC-8: Sanctioned entity flag shows type, severity, detail."""
        mock = AsyncMock(return_value=_make_blocked_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "Steel plates", "--client", "DPRK Trading Corp"])

        assert "sanctioned_entity" in result.output
        assert "BLOCK" in result.output
        assert "DPRK Trading Corp" in result.output
        assert "OFAC SDN" in result.output


class TestComplianceJsonOutput:
    """AC-8: JSON output flag."""

    def test_json_output_compliant(self) -> None:
        """AC-8: JSON output for compliant result."""
        mock = AsyncMock(return_value=_make_compliant_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "Tube inox", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["is_compliant"] is True
        assert data["flags"] == []
        assert data["check_duration_ms"] == 150

    def test_json_output_flagged(self) -> None:
        """AC-8: JSON output for flagged result."""
        mock = AsyncMock(return_value=_make_flagged_result())
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "uranium tubes", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["is_compliant"] is False
        assert len(data["flags"]) == 1
        assert data["flags"][0]["flag_type"] == "export_control"


class TestComplianceErrorHandling:
    """AC-8: Error handling."""

    def test_error_exits_with_code_1(self) -> None:
        """AC-8: Exception during compliance check exits with code 1."""
        mock = AsyncMock(side_effect=RuntimeError("Connection failed"))
        with patch("quote_agent.cli.compliance._run_compliance", mock):
            result = runner.invoke(app, ["compliance", "test"])

        assert result.exit_code == 1
        assert "Error" in result.output
