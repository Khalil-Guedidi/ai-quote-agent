"""Security module — prompt injection defense (Layers 1 & 2) and log redaction."""

from quote_agent.security.input_isolation import (
    IsolatedInput,
    build_extraction_messages,
    isolate_input,
)
from quote_agent.security.log_redactor import (
    RedactionMatch,
    RedactionResult,
    redact,
    redact_context,
)
from quote_agent.security.sanitizer import SanitizationResult, ThreatMatch, sanitize

__all__ = [
    "IsolatedInput",
    "RedactionMatch",
    "RedactionResult",
    "SanitizationResult",
    "ThreatMatch",
    "build_extraction_messages",
    "isolate_input",
    "redact",
    "redact_context",
    "sanitize",
]
