"""Query expansion for industrial jargon and abbreviations."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JargonExpansionResult:
    """Result of query expansion — preserves original, adds expansions."""

    original_query: str
    expanded_query: str
    expansions_applied: list[str] = field(default_factory=list)
    was_expanded: bool = False


def expand_query(query: str, abbreviations: dict[str, str]) -> JargonExpansionResult:
    """Expand known abbreviations in a query by appending full forms.

    Expansion is additive — original tokens are never replaced or removed.
    Abbreviations inside reference codes (e.g., REF-DN100) are NOT expanded.
    Word boundary matching is case-insensitive.
    """
    expansions: list[str] = []
    extra_terms: list[str] = []

    for abbrev, full_form in abbreviations.items():
        # Word boundary match, case-insensitive, NOT inside reference codes.
        # Use ASCII-only check: non-ASCII symbols like Ø need special handling
        # since \b treats them as word characters in Python's Unicode-aware regex.
        is_ascii_word = abbrev.isascii() and bool(re.fullmatch(r"[A-Za-z0-9]+", abbrev))
        if is_ascii_word:
            # Standard word-boundary match, NOT inside reference codes (hyphen/underscore prefix).
            pattern = rf"(?<![A-Za-z0-9_-])\b{re.escape(abbrev)}\b(?![A-Za-z0-9_-])"
        else:
            # Non-ASCII symbols (e.g., Ø) — match preceded by whitespace/start.
            pattern = rf"(?:^|(?<=\s)){re.escape(abbrev)}"
        if re.search(pattern, query, re.IGNORECASE):
            extra_terms.append(full_form)
            expansions.append(f"{abbrev} → {full_form}")

    if not expansions:
        return JargonExpansionResult(
            original_query=query,
            expanded_query=query,
            expansions_applied=[],
            was_expanded=False,
        )

    expanded = f"{query} {' '.join(extra_terms)}"

    logger.info(
        "Query expanded",
        extra={
            "context": {
                "component": "search.jargon",
                "original": query,
                "expanded": expanded,
                "expansions_count": len(expansions),
                "expansions": expansions,
            }
        },
    )

    return JargonExpansionResult(
        original_query=query,
        expanded_query=expanded,
        expansions_applied=expansions,
        was_expanded=True,
    )
