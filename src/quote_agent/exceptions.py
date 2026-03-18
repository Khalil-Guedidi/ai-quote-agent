"""Exception hierarchy for the quote agent system."""


class QuoteAgentError(Exception):
    """Base exception for all quote agent errors."""


class AdapterError(QuoteAgentError):
    """Base exception for external adapter failures."""


class ERPConnectionError(AdapterError):
    """Failed to connect to or communicate with the ERP system."""


class LLMTimeoutError(AdapterError):
    """LLM request timed out."""


class EmailConnectionError(AdapterError):
    """Failed to connect to the email server."""


class NotificationError(AdapterError):
    """Failed to send a notification."""


class ValidationError(QuoteAgentError):
    """Data validation failure."""


class SecurityError(QuoteAgentError):
    """Security policy violation."""


class ConfigurationError(QuoteAgentError):
    """Invalid or missing configuration."""
