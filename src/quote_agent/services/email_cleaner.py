"""Email content cleaning — strips signatures, reply threads, and noise."""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled regex patterns (module-level for performance)
# ---------------------------------------------------------------------------

# RFC 3676 standard signature delimiter: "-- " followed by newline
_RFC3676_SIG_RE = re.compile(r"^-- $", re.MULTILINE)

# French common sign-offs (case-insensitive, at start of line)
_FRENCH_SIGNOFF_RE = re.compile(
    r"^(Cordialement|Bien cordialement|Cdlt|Salutations|"
    r"Bonne réception|Merci d'avance),?\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# English common sign-offs
_ENGLISH_SIGNOFF_RE = re.compile(
    r"^(Regards|Best regards|Kind regards|Thanks|Thank you|Cheers|Best),?\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Mobile device signatures
_MOBILE_SIG_RE = re.compile(
    r"^(Envoyé de mon iPhone|Envoyé de mon iPad|Sent from my iPhone|"
    r"Sent from my|Envoyé depuis).*$",
    re.MULTILINE | re.IGNORECASE,
)

# English reply header: "On ... wrote:"
_ENGLISH_REPLY_HEADER_RE = re.compile(r"^On .+ wrote:\s*$", re.MULTILINE)

# French reply header: "Le ... a écrit :"
_FRENCH_REPLY_HEADER_RE = re.compile(r"^Le .+ a écrit\s?:\s*$", re.MULTILINE)

# Outlook-style original message separator
_ORIGINAL_MSG_RE = re.compile(
    r"^-{3,}\s*(Original Message|Message d'origine)\s*-{3,}\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Forwarded message separator
_FORWARDED_MSG_RE = re.compile(
    r"^-{3,}\s*(Forwarded message|Message transféré)\s*-{3,}\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Disclaimer markers (case-insensitive)
_DISCLAIMER_RE = re.compile(
    r"(CONFIDENTIAL|CONFIDENTIALITY|AVERTISSEMENT|DISCLAIMER|"
    r"Ce message.*confidentiel|This email.*confidential|"
    r"Ce courriel.*confidentiel)",
    re.IGNORECASE,
)

# Multiple blank lines
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


# ---------------------------------------------------------------------------
# Pure cleaning functions
# ---------------------------------------------------------------------------


def _strip_reply_threads(text: str) -> str:
    """Remove reply threads: quoted lines and reply/forward headers."""
    # Find the earliest reply/forward separator and truncate
    earliest_pos = len(text)

    for pattern in (
        _ENGLISH_REPLY_HEADER_RE,
        _FRENCH_REPLY_HEADER_RE,
        _ORIGINAL_MSG_RE,
        _FORWARDED_MSG_RE,
    ):
        match = pattern.search(text)
        if match and match.start() < earliest_pos:
            earliest_pos = match.start()

    # If we found a separator, truncate there
    if earliest_pos < len(text):
        text = text[:earliest_pos]

    # Always strip standalone quoted lines (> prefix) from remaining text
    lines = text.split("\n")
    cleaned_lines = [line for line in lines if not re.match(r"^>+ ?", line)]
    text = "\n".join(cleaned_lines)

    return text


def _strip_signatures(text: str) -> str:
    """Remove signature blocks from email content.

    Scans from bottom up to find the last sign-off pattern, then truncates.
    RFC 3676 "-- " delimiter is authoritative regardless of position.
    Soft patterns (Cordialement, Regards, etc.) only match in the last 80% to
    avoid stripping content that mentions these words early on.
    """
    # RFC 3676: authoritative delimiter "-- "
    rfc_match = _RFC3676_SIG_RE.search(text)
    if rfc_match:
        return text[: rfc_match.start()]

    # Soft patterns — scan from bottom up, only in the last 80% of the email
    lines = text.split("\n")
    total_lines = len(lines)
    if total_lines == 0:
        return text

    # Minimum threshold: at least 1 line of content preserved.
    # 20% means sign-offs must be in the bottom 80% of the email.
    threshold_line = max(1, int(total_lines * 0.2))

    # Scan from bottom up to find the LAST sign-off
    for i in range(total_lines - 1, threshold_line - 1, -1):
        for pattern in (_FRENCH_SIGNOFF_RE, _ENGLISH_SIGNOFF_RE, _MOBILE_SIG_RE):
            if pattern.match(lines[i]):
                return "\n".join(lines[:i])

    return text


def _strip_disclaimers(text: str) -> str:
    """Remove legal disclaimer blocks from email content."""
    lines = text.split("\n")
    result_lines = []
    skip = False

    for line in lines:
        if not skip and _DISCLAIMER_RE.search(line):
            skip = True
            continue
        if skip:
            # Continue skipping until end — disclaimers are typically at the bottom
            continue
        result_lines.append(line)

    return "\n".join(result_lines)


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple blank lines and strip leading/trailing whitespace."""
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()


def clean(raw_content: str) -> str:
    """Clean email content by removing noise. Pure function: str in, str out.

    Pipeline order:
    1. Strip reply threads (they may contain signatures)
    2. Strip signatures
    3. Strip legal disclaimers
    4. Normalize whitespace

    Safety valve: if cleaning removes >90% of content, return original.
    """
    if not raw_content:
        return ""

    cleaned = raw_content
    cleaned = _strip_reply_threads(cleaned)
    cleaned = _strip_signatures(cleaned)
    cleaned = _strip_disclaimers(cleaned)
    cleaned = _normalize_whitespace(cleaned)

    # Safety valve: never over-strip
    if len(cleaned) < len(raw_content.strip()) * 0.1:
        return _normalize_whitespace(raw_content)

    return cleaned
