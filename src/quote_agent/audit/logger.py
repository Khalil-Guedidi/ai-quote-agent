"""Structured JSON logging setup with automatic confidential data redaction."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


class JSONLogFormatter(logging.Formatter):
    """Format log records as single-line JSON with automatic context redaction."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize log record to JSON, redacting context values."""
        from quote_agent.security.log_redactor import redact_context

        context = getattr(record, "context", {})
        component = getattr(record, "component", record.name)

        redacted_context = redact_context(context) if context else {}

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "component": component,
            "message": record.getMessage(),
            "context": redacted_context,
        }
        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure Python root logger with JSON formatter and redaction.

    Removes default handlers and installs a single StreamHandler to stdout
    using ``JSONLogFormatter``.
    """
    import sys

    root_logger = logging.getLogger()

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter())

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
