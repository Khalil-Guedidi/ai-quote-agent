"""Tests for CLI commands — status, logs, and help."""

from __future__ import annotations

import json
from http.client import HTTPResponse
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from quote_agent.cli.main import app

runner = CliRunner()


def test_cli_help_shows_commands() -> None:
    """Verify --help lists status and logs commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "logs" in result.output


def _make_health_response(
    overall: str = "healthy",
    services: dict[str, dict[str, str | None]] | None = None,
) -> bytes:
    """Build a JSON health response body."""
    if services is None:
        services = {
            "database": {"status": "healthy", "error": None},
            "llm": {"status": "healthy", "error": None},
            "erp": {"status": "healthy", "error": None},
            "email": {"status": "healthy", "error": None},
            "notification": {"status": "healthy", "error": None},
        }
    body = {
        "data": {"status": overall, "services": services},
        "meta": {"timestamp": "2026-03-18T10:00:00Z"},
    }
    return json.dumps(body).encode()


def _mock_urlopen(data: bytes) -> MagicMock:
    """Create a mock for urllib.request.urlopen returning given data."""
    mock_response = MagicMock(spec=HTTPResponse)
    mock_response.read.return_value = data
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestStatusCommand:
    """Tests for `agent status`."""

    def test_status_command_healthy(self) -> None:
        """All services healthy displays overall healthy."""
        data = _make_health_response()
        mock_resp = _mock_urlopen(data)
        with patch("quote_agent.cli.status.urlopen", return_value=mock_resp):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "healthy" in result.output
        assert "database" in result.output
        assert "llm" in result.output

    def test_status_command_degraded(self) -> None:
        """One unhealthy service shows degraded status and error."""
        services = {
            "database": {"status": "healthy", "error": None},
            "llm": {"status": "healthy", "error": None},
            "erp": {"status": "unhealthy", "error": "Connection refused"},
            "email": {"status": "healthy", "error": None},
            "notification": {"status": "healthy", "error": None},
        }
        data = _make_health_response(overall="degraded", services=services)
        mock_resp = _mock_urlopen(data)
        with patch("quote_agent.cli.status.urlopen", return_value=mock_resp):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "degraded" in result.output
        assert "unhealthy" in result.output
        assert "Connection refused" in result.output

    def test_status_command_connection_error(self) -> None:
        """Connection failure shows clear error message."""
        from urllib.error import URLError

        with patch("quote_agent.cli.status.urlopen", side_effect=URLError("Connection refused")):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "Could not connect" in result.output


class TestLogsCommand:
    """Tests for `agent logs`."""

    def test_logs_command_default(self) -> None:
        """Default invocation calls docker logs --tail 100."""
        mock_result = MagicMock(returncode=0)
        with patch("quote_agent.cli.logs.subprocess.run", return_value=mock_result) as mock_run:
            runner.invoke(app, ["logs"])
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "docker" in cmd
        assert "--tail" in cmd
        assert "100" in cmd
        assert "quote-agent-app" in cmd

    def test_logs_command_follow(self) -> None:
        """--follow flag is passed to docker logs."""
        mock_result = MagicMock(returncode=0)
        with patch("quote_agent.cli.logs.subprocess.run", return_value=mock_result) as mock_run:
            runner.invoke(app, ["logs", "--follow"])
        cmd = mock_run.call_args[0][0]
        assert "--follow" in cmd

    def test_logs_command_custom_lines(self) -> None:
        """--lines flag controls --tail value."""
        mock_result = MagicMock(returncode=0)
        with patch("quote_agent.cli.logs.subprocess.run", return_value=mock_result) as mock_run:
            runner.invoke(app, ["logs", "--lines", "50"])
        cmd = mock_run.call_args[0][0]
        assert "50" in cmd

    def test_logs_command_docker_not_found(self) -> None:
        """Missing docker binary shows clear error message."""
        with patch("quote_agent.cli.logs.subprocess.run", side_effect=FileNotFoundError):
            result = runner.invoke(app, ["logs"])
        assert result.exit_code == 1
        assert "docker is not installed" in result.output
