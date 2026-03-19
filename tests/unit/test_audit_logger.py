"""Unit tests for audit.logger — structured JSON logging with redaction."""

from __future__ import annotations

import json
import logging
from datetime import datetime

import pytest

from quote_agent.audit.logger import JSONLogFormatter, setup_logging


@pytest.fixture
def _clean_root_logger():
    """Save and restore root logger state around the test."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)


@pytest.mark.usefixtures("_clean_root_logger")
def test_setup_logging_configures_root_logger() -> None:
    """setup_logging() configures root logger with JSON formatter."""
    setup_logging("DEBUG")
    root = logging.getLogger()

    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JSONLogFormatter)
    assert root.level == logging.DEBUG


def test_json_formatter_outputs_valid_json(capfd: object) -> None:
    """JSONLogFormatter outputs valid single-line JSON."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)

    parsed = json.loads(output)
    assert isinstance(parsed, dict)
    assert "\n" not in output


def test_json_output_contains_required_fields() -> None:
    """JSON output contains required fields: timestamp, level, component, message, context."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test.module",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="Something happened",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert "timestamp" in parsed
    assert "level" in parsed
    assert "component" in parsed
    assert "message" in parsed
    assert "context" in parsed


def test_component_extracted_from_extra() -> None:
    """component extracted from extra['component']."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="fallback_name",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test",
        args=None,
        exc_info=None,
    )
    record.component = "services.email_poller"  # type: ignore[attr-defined]
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["component"] == "services.email_poller"


def test_context_extracted_from_extra() -> None:
    """context extracted from extra['context']."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test",
        args=None,
        exc_info=None,
    )
    record.context = {"key": "value", "count": 42}  # type: ignore[attr-defined]
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["context"]["key"] == "value"
    assert parsed["context"]["count"] == 42


def test_missing_component_defaults_to_logger_name() -> None:
    """Missing component defaults to logger name."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="my.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["component"] == "my.logger"


def test_missing_context_defaults_to_empty_dict() -> None:
    """Missing context defaults to empty dict."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["context"] == {}


def test_context_values_are_redacted() -> None:
    """Context values are redacted (email addresses in context dict)."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test",
        args=None,
        exc_info=None,
    )
    record.context = {"sender": "dupont@acme.fr", "count": 3}  # type: ignore[attr-defined]
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["context"]["sender"] == "[REDACTED_EMAIL]"
    assert parsed["context"]["count"] == 3


def test_timestamp_is_iso8601_utc() -> None:
    """Timestamp is ISO 8601 UTC format."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    ts = parsed["timestamp"]
    # Should be parseable as ISO 8601
    dt = datetime.fromisoformat(ts)
    assert dt is not None
    # Should contain UTC indicator
    assert "+00:00" in ts or "Z" in ts
