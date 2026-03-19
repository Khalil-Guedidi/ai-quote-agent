"""Audit module — structured JSON logging with automatic redaction."""

from quote_agent.audit.logger import JSONLogFormatter, setup_logging

__all__ = [
    "JSONLogFormatter",
    "setup_logging",
]
