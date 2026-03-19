"""Security module — prompt injection defense (Layers 1 & 2)."""

from quote_agent.security.input_isolation import (
    IsolatedInput,
    build_extraction_messages,
    isolate_input,
)
from quote_agent.security.sanitizer import SanitizationResult, ThreatMatch, sanitize

__all__ = [
    "IsolatedInput",
    "SanitizationResult",
    "ThreatMatch",
    "build_extraction_messages",
    "isolate_input",
    "sanitize",
]
