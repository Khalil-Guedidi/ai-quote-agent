"""Tests for the exception hierarchy."""

from __future__ import annotations

from quote_agent.exceptions import (
    AdapterError,
    ConfigurationError,
    EmailConnectionError,
    ERPConnectionError,
    LLMTimeoutError,
    NotificationError,
    QuoteAgentError,
    SecurityError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Verify exception inheritance chain."""

    def test_all_exceptions_inherit_from_quote_agent_error(self) -> None:
        for exc_cls in [
            AdapterError,
            ERPConnectionError,
            LLMTimeoutError,
            EmailConnectionError,
            NotificationError,
            ValidationError,
            SecurityError,
            ConfigurationError,
        ]:
            assert issubclass(exc_cls, QuoteAgentError)

    def test_adapter_errors_inherit_from_adapter_error(self) -> None:
        for exc_cls in [
            ERPConnectionError,
            LLMTimeoutError,
            EmailConnectionError,
            NotificationError,
        ]:
            assert issubclass(exc_cls, AdapterError)

    def test_adapter_error_not_parent_of_non_adapter_exceptions(self) -> None:
        for exc_cls in [ValidationError, SecurityError, ConfigurationError]:
            assert not issubclass(exc_cls, AdapterError)

    def test_exceptions_are_catchable(self) -> None:
        with __import__("pytest").raises(QuoteAgentError):
            raise ERPConnectionError("connection failed")
