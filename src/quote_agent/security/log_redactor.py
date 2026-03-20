"""Confidential data redaction for log output — regex-based pattern detection."""

from __future__ import annotations

import re

from pydantic import BaseModel


class RedactionMatch(BaseModel):
    """A single redacted item with category and position."""

    category: str
    matched_text: str
    replacement: str
    position: int


class RedactionResult(BaseModel):
    """Result of redacting confidential data from text."""

    redacted_text: str
    original_text: str
    redactions_applied: list[RedactionMatch]
    redaction_count: int


# ---------------------------------------------------------------------------
# Compiled regex patterns for confidential data detection
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_FR_RE = re.compile(
    r"(?:\+33\s*\(?\d\)?\s*(?:\d[\s.-]?){8})"  # +33 formats
    r"|(?:0[1-6]\s*(?:\d{2}[\s.-]?){4})"  # 01-06 formats
)
_PRICE_RE = re.compile(
    r"\d[\d\s.,]*\s*(?:€|EUR\b)"  # 500€, 1 500 EUR
    r"|(?:prix|tarif|remise|réduction|escompte)\s*[:=]?\s*\d[\d\s.,]*(?:\s*%)?",  # prix: 250, remise 10%
    re.IGNORECASE,
)
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[\s]?[\dA-Z]{4}[\s]?(?:[\dA-Z]{4}[\s]?){2,7}[\dA-Z]{1,4}\b")

_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (_EMAIL_RE, "email", "[REDACTED_EMAIL]"),
    (_PHONE_FR_RE, "phone", "[REDACTED_PHONE]"),
    (_PRICE_RE, "price", "[REDACTED_PRICE]"),
    (_IBAN_RE, "iban", "[REDACTED_IBAN]"),
]


def redact(text: str | None) -> RedactionResult:
    """Detect confidential patterns in text and replace with category-labeled placeholders."""
    if not text:
        return RedactionResult(
            redacted_text=text or "",
            original_text=text or "",
            redactions_applied=[],
            redaction_count=0,
        )

    matches: list[RedactionMatch] = []

    for pattern, category, replacement in _PATTERNS:
        for m in pattern.finditer(text):
            matches.append(
                RedactionMatch(
                    category=category,
                    matched_text=m.group(),
                    replacement=replacement,
                    position=m.start(),
                )
            )

    # Sort by position descending to replace without shifting indices
    matches_sorted = sorted(matches, key=lambda r: r.position, reverse=True)
    redacted = text
    for match in matches_sorted:
        start = match.position
        end = start + len(match.matched_text)
        redacted = redacted[:start] + match.replacement + redacted[end:]

    # Re-sort ascending for output
    matches.sort(key=lambda r: r.position)

    return RedactionResult(
        redacted_text=redacted,
        original_text=text,
        redactions_applied=matches,
        redaction_count=len(matches),
    )


def redact_context(context: dict[str, object]) -> dict[str, object]:
    """Recursively redact string values in a dict for structured log context.

    Non-string values pass through unchanged. Nested dicts are walked recursively.
    """
    result: dict[str, object] = {}
    for key, value in context.items():
        if isinstance(value, str):
            result[key] = redact(value).redacted_text
        elif isinstance(value, dict):
            result[key] = redact_context(value)
        elif isinstance(value, list):
            result[key] = [redact(item).redacted_text if isinstance(item, str) else item for item in value]
        else:
            result[key] = value
    return result
