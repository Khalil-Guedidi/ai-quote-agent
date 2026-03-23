"""Tests for the CLI process command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from quote_agent.cli.main import app

runner = CliRunner()


def _mock_result() -> dict[str, object]:
    """Build a mock final state dict."""
    classification = MagicMock()
    classification.complexity = "simple"
    classification.confidence = 0.95

    reasoning = MagicMock()
    reasoning.strategy = "direct_match"
    reasoning.reasoning_duration_ms = 150
    reasoning.search_result.results = [MagicMock()]

    confidence = MagicMock()
    confidence.overall_confidence = 0.92

    routing = MagicMock()
    routing.action = "proceed_to_draft"
    routing.tier = "high"

    review = MagicMock()
    review.approved = True

    compliance = MagicMock()
    compliance.is_compliant = True
    compliance.flags = []

    draft = MagicMock()
    draft.odoo_id = 42
    draft.order_reference = "SO042"

    return {
        "raw_request": MagicMock(),
        "classification": classification,
        "reasoning": reasoning,
        "confidence": confidence,
        "routing_decision": routing,
        "self_review": review,
        "compliance": compliance,
        "draft_result": draft,
        "error": None,
        "current_node": "draft",
        "final_action": "proceed_to_draft",
    }


class TestProcessCommand:
    """AC-7: CLI process command."""

    def test_process_success_formatted(self) -> None:
        """AC-7: Process command displays formatted output."""
        with patch("quote_agent.cli.process._run_process", new_callable=AsyncMock, return_value=_mock_result()):
            result = runner.invoke(app, ["process", "tubes inox 304L", "--client", "ACME"])

        assert result.exit_code == 0
        assert "simple" in result.output
        assert "direct_match" in result.output
        assert "proceed_to_draft" in result.output
        assert "APPROVED" in result.output
        assert "COMPLIANT" in result.output
        assert "SO042" in result.output

    def test_process_json_output(self) -> None:
        """AC-7: Process command supports --json flag."""
        mock_state = _mock_result()
        # Replace Pydantic-like mocks with simple dicts for JSON serialization
        for key in ["classification", "reasoning", "confidence", "routing_decision",
                     "self_review", "compliance", "draft_result", "raw_request"]:
            m = mock_state[key]
            if m is not None:
                m.model_dump_json = MagicMock(return_value='{"mock": true}')

        with patch("quote_agent.cli.process._run_process", new_callable=AsyncMock, return_value=mock_state):
            result = runner.invoke(app, ["process", "tubes inox 304L", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "classification" in output
        assert "reasoning" in output

    def test_process_with_optional_flags(self) -> None:
        """AC-7: Process supports --quantity, --reference, --urgency."""
        mock_state = _mock_result()
        with patch("quote_agent.cli.process._run_process", new_callable=AsyncMock, return_value=mock_state) as mock_run:
            result = runner.invoke(app, [
                "process", "tubes inox",
                "--client", "ACME",
                "--quantity", "100",
                "--reference", "REF-001",
                "--urgency", "high",
            ])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        # Check args were passed through
        assert call_kwargs[1]["client"] == "ACME"
        assert call_kwargs[1]["quantity"] == 100.0
        assert call_kwargs[1]["reference"] == "REF-001"
        assert call_kwargs[1]["urgency"] == "high"

    def test_process_error_displays_message(self) -> None:
        """AC-7: Process command handles errors gracefully."""
        with patch(
            "quote_agent.cli.process._run_process",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connection refused"),
        ):
            result = runner.invoke(app, ["process", "test request"])

        assert result.exit_code == 1
        assert "Connection refused" in result.output

    def test_process_with_error_in_state(self) -> None:
        """AC-7: Process displays error from state when a node failed."""
        mock_state = _mock_result()
        mock_state["error"] = "classify: LLM timeout"
        mock_state["draft_result"] = None

        with patch("quote_agent.cli.process._run_process", new_callable=AsyncMock, return_value=mock_state):
            result = runner.invoke(app, ["process", "test request"])

        assert result.exit_code == 0
        assert "classify: LLM timeout" in result.output

    def test_process_sends_error_notification_when_error_in_state(self) -> None:
        """AC-4 (5.5.5): Post-pipeline error check sends error notification."""
        mock_state = _mock_result()
        mock_state["error"] = "classify: LLM timeout"
        mock_state["draft_result"] = None

        with (
            patch("quote_agent.cli.process._run_process", new_callable=AsyncMock, return_value=mock_state),
            patch("quote_agent.cli.process._send_error_notification", new_callable=AsyncMock) as mock_notify,
        ):
            result = runner.invoke(app, ["process", "test request"])

        assert result.exit_code == 0
        mock_notify.assert_called_once_with("classify: LLM timeout")

    def test_process_no_error_notification_when_no_error(self) -> None:
        """AC-4 (5.5.5): No error notification when pipeline succeeds."""
        mock_state = _mock_result()

        with (
            patch("quote_agent.cli.process._run_process", new_callable=AsyncMock, return_value=mock_state),
            patch("quote_agent.cli.process._send_error_notification", new_callable=AsyncMock) as mock_notify,
        ):
            result = runner.invoke(app, ["process", "tubes inox 304L", "--client", "ACME"])

        assert result.exit_code == 0
        mock_notify.assert_not_called()

    def test_process_no_draft_when_proposals(self) -> None:
        """AC-7: Process shows final_action but no draft for non-draft paths."""
        mock_state = _mock_result()
        mock_state["routing_decision"].action = "generate_proposals"
        mock_state["routing_decision"].tier = "medium"
        mock_state["self_review"] = None
        mock_state["compliance"] = None
        mock_state["draft_result"] = None
        mock_state["final_action"] = "generate_proposals"

        with patch("quote_agent.cli.process._run_process", new_callable=AsyncMock, return_value=mock_state):
            result = runner.invoke(app, ["process", "vague request"])

        assert result.exit_code == 0
        assert "generate_proposals" in result.output
        assert "SO042" not in result.output
