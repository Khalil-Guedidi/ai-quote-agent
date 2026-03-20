"""Unit tests for the CLI classify command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from quote_agent.agent.nodes.classifier import ClassificationResult
from quote_agent.cli.main import app

runner = CliRunner()


def _make_classification_result(
    complexity: str = "simple",
    confidence: float = 0.95,
    duration_ms: int = 150,
) -> ClassificationResult:
    """Build a ClassificationResult for testing."""
    return ClassificationResult(
        complexity=complexity,  # type: ignore[arg-type]
        reasons=["Clear product reference", "Quantity specified"],
        confidence=confidence,
        classification_duration_ms=duration_ms,
    )


@pytest.fixture()
def mock_run_classify() -> AsyncMock:
    """Provide a pre-configured AsyncMock for _run_classify."""
    return AsyncMock(return_value=_make_classification_result())


class TestClassifyFormattedOutput:
    """Formatted output displays expected fields."""

    def test_displays_complexity_and_confidence_when_result_returned(self, mock_run_classify: AsyncMock) -> None:
        with patch("quote_agent.cli.classify._run_classify", mock_run_classify):
            result = runner.invoke(app, ["classify", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "simple" in result.output
        assert "0.95" in result.output

    def test_displays_duration_when_result_returned(self, mock_run_classify: AsyncMock) -> None:
        with patch("quote_agent.cli.classify._run_classify", mock_run_classify):
            result = runner.invoke(app, ["classify", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "150ms" in result.output

    def test_displays_reasons_when_result_returned(self, mock_run_classify: AsyncMock) -> None:
        with patch("quote_agent.cli.classify._run_classify", mock_run_classify):
            result = runner.invoke(app, ["classify", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        assert "Clear product reference" in result.output
        assert "Quantity specified" in result.output


class TestClassifyJsonOutput:
    """--json flag produces valid JSON."""

    def test_json_output_when_json_flag_set(self, mock_run_classify: AsyncMock) -> None:
        with patch("quote_agent.cli.classify._run_classify", mock_run_classify):
            result = runner.invoke(app, ["classify", "--json", "Tube inox 304L DN50"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["complexity"] == "simple"
        assert data["confidence"] == 0.95
        assert len(data["reasons"]) == 2
        assert data["classification_duration_ms"] == 150

    def test_json_output_matches_classification_result_schema(self, mock_run_classify: AsyncMock) -> None:
        with patch("quote_agent.cli.classify._run_classify", mock_run_classify):
            result = runner.invoke(app, ["classify", "--json", "Tube inox"])

        assert result.exit_code == 0
        parsed = ClassificationResult.model_validate_json(result.output)
        assert parsed.complexity == "simple"


class TestClassifyOptions:
    """Optional flags are passed through."""

    def test_passes_quantity_when_provided(self) -> None:
        mock = AsyncMock(return_value=_make_classification_result())
        with patch("quote_agent.cli.classify._run_classify", mock):
            result = runner.invoke(app, ["classify", "--quantity", "10", "Tube inox"])

        assert result.exit_code == 0
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs["quantity"] == 10.0

    def test_passes_reference_when_provided(self) -> None:
        mock = AsyncMock(return_value=_make_classification_result())
        with patch("quote_agent.cli.classify._run_classify", mock):
            result = runner.invoke(app, ["classify", "--reference", "REF-001", "Tube inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["reference"] == "REF-001"

    def test_passes_urgency_when_provided(self) -> None:
        mock = AsyncMock(return_value=_make_classification_result())
        with patch("quote_agent.cli.classify._run_classify", mock):
            result = runner.invoke(app, ["classify", "--urgency", "urgent", "Tube inox"])

        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["urgency"] == "urgent"


class TestClassifyErrorHandling:
    """Graceful error on failure."""

    def test_displays_error_when_exception_raised(self) -> None:
        mock = AsyncMock(side_effect=RuntimeError("Connection failed"))
        with patch("quote_agent.cli.classify._run_classify", mock):
            result = runner.invoke(app, ["classify", "Tube inox"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Connection failed" in result.output
