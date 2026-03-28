"""Tests for batch notification CLI commands — batch-summary, weekly-report, manager-stats."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from quote_agent.adapters.notification.models import NotificationResult

runner = CliRunner()


def _success_result() -> NotificationResult:
    """Build a successful NotificationResult."""
    return NotificationResult(
        success=True,
        status_code=200,
        timestamp=datetime.now(tz=UTC),
    )


def _mock_adapter(result: NotificationResult | None = None) -> MagicMock:
    """Create a mock adapter with send_notification returning the given result."""
    adapter = MagicMock()
    adapter.hostname = "test.webhook.office.com"
    adapter.send_notification = AsyncMock(return_value=result or _success_result())
    return adapter


# --- batch-summary CLI Tests ---


@patch("quote_agent.cli.batch_notify._run_batch_summary")
def test_cli_batch_summary_success(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-1: CLI batch-summary displays success status."""
    from quote_agent.cli.main import app

    mock_run.return_value = (_success_result(), "test.webhook.office.com")

    result = runner.invoke(app, ["batch-summary"])

    assert result.exit_code == 0
    assert "success" in result.output.lower()


@patch("quote_agent.cli.batch_notify._run_batch_summary")
def test_cli_batch_summary_skipped(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-1: CLI batch-summary shows skipped when no data."""
    from quote_agent.cli.main import app

    mock_run.return_value = (None, "test.webhook.office.com")

    result = runner.invoke(app, ["batch-summary"])

    assert result.exit_code == 0
    assert "skip" in result.output.lower() or "no data" in result.output.lower()


@patch("quote_agent.cli.batch_notify._run_batch_summary")
def test_cli_batch_summary_json_output(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-1: CLI batch-summary --json produces valid JSON."""
    from quote_agent.cli.main import app

    mock_run.return_value = (_success_result(), "test.webhook.office.com")

    result = runner.invoke(app, ["batch-summary", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["webhook_hostname"] == "test.webhook.office.com"


@patch("quote_agent.cli.batch_notify._run_batch_summary")
def test_cli_batch_summary_json_skipped(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-1: CLI batch-summary --json shows skipped JSON."""
    from quote_agent.cli.main import app

    mock_run.return_value = (None, "test.webhook.office.com")

    result = runner.invoke(app, ["batch-summary", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["skipped"] is True


# --- weekly-report CLI Tests ---


@patch("quote_agent.cli.batch_notify._run_weekly_report")
def test_cli_weekly_report_success(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-2: CLI weekly-report displays success status."""
    from quote_agent.cli.main import app

    mock_run.return_value = (_success_result(), "test.webhook.office.com")

    result = runner.invoke(app, ["weekly-report"])

    assert result.exit_code == 0
    assert "success" in result.output.lower()


@patch("quote_agent.cli.batch_notify._run_weekly_report")
def test_cli_weekly_report_json_output(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-2: CLI weekly-report --json produces valid JSON."""
    from quote_agent.cli.main import app

    mock_run.return_value = (_success_result(), "test.webhook.office.com")

    result = runner.invoke(app, ["weekly-report", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True


# --- manager-stats CLI Tests ---


@patch("quote_agent.cli.batch_notify._run_manager_stats")
def test_cli_manager_stats_success(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-3: CLI manager-stats displays success status."""
    from quote_agent.cli.main import app

    mock_run.return_value = (_success_result(), "test.webhook.office.com")

    result = runner.invoke(app, ["manager-stats"])

    assert result.exit_code == 0
    assert "success" in result.output.lower()


@patch("quote_agent.cli.batch_notify._run_manager_stats")
def test_cli_manager_stats_json_output(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-3: CLI manager-stats --json produces valid JSON."""
    from quote_agent.cli.main import app

    mock_run.return_value = (_success_result(), "test.webhook.office.com")

    result = runner.invoke(app, ["manager-stats", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True


@patch("quote_agent.cli.batch_notify._run_manager_stats")
def test_cli_manager_stats_failure(
    mock_run: MagicMock,
    env_vars: dict[str, str],
    _clear_settings_cache: None,
) -> None:
    """AC-3: CLI manager-stats exits with code 1 on failure."""
    from quote_agent.cli.main import app

    fail_result = NotificationResult(
        success=False,
        error="Connection refused",
        timestamp=datetime.now(tz=UTC),
    )
    mock_run.return_value = (fail_result, "test.webhook.office.com")

    result = runner.invoke(app, ["manager-stats"])

    assert result.exit_code == 1
    assert "failure" in result.output.lower()
