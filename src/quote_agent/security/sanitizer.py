"""Prompt injection detection and sanitization for untrusted email content."""

from __future__ import annotations

import logging
import re
import time
from typing import ClassVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ThreatMatch(BaseModel):
    """A single detected prompt injection pattern."""

    pattern_name: str
    matched_text: str
    position: int
    severity: str  # low / medium / high


class SanitizationResult(BaseModel):
    """Result of sanitizing untrusted text."""

    sanitized_text: str
    original_text: str
    threats_detected: list[ThreatMatch]
    threat_count: int
    sanitization_duration_ms: int


class _ThreatPattern(BaseModel):
    """Internal: compiled regex pattern with metadata."""

    model_config: ClassVar[dict] = {"arbitrary_types_allowed": True}

    name: str
    regex: re.Pattern[str]
    severity: str
    category: str


# ---------------------------------------------------------------------------
# Compiled threat patterns (module-level constants)
# ---------------------------------------------------------------------------

_THREAT_PATTERNS: list[_ThreatPattern] = [
    # --- Role impersonation (high) ---
    _ThreatPattern(
        name="role_impersonation_system",
        regex=re.compile(r"system\s*:", re.IGNORECASE),
        severity="high",
        category="role_impersonation",
    ),
    _ThreatPattern(
        name="role_impersonation_assistant",
        regex=re.compile(r"assistant\s*:", re.IGNORECASE),
        severity="high",
        category="role_impersonation",
    ),
    _ThreatPattern(
        name="role_impersonation_inst",
        regex=re.compile(r"\[INST\]", re.IGNORECASE),
        severity="high",
        category="role_impersonation",
    ),
    _ThreatPattern(
        name="role_impersonation_sys_tag",
        regex=re.compile(r"<<SYS>>", re.IGNORECASE),
        severity="high",
        category="role_impersonation",
    ),
    _ThreatPattern(
        name="role_impersonation_end_s",
        regex=re.compile(r"</s>"),
        severity="high",
        category="role_impersonation",
    ),
    _ThreatPattern(
        name="role_impersonation_im_start",
        regex=re.compile(r"<\|im_start\|>"),
        severity="high",
        category="role_impersonation",
    ),
    _ThreatPattern(
        name="role_impersonation_im_end",
        regex=re.compile(r"<\|im_end\|>"),
        severity="high",
        category="role_impersonation",
    ),
    # --- Instruction override (high) ---
    _ThreatPattern(
        name="instruction_override_ignore_previous",
        regex=re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
        severity="high",
        category="instruction_override",
    ),
    _ThreatPattern(
        name="instruction_override_ignore_all",
        regex=re.compile(r"ignore\s+all\s+previous", re.IGNORECASE),
        severity="high",
        category="instruction_override",
    ),
    _ThreatPattern(
        name="instruction_override_disregard",
        regex=re.compile(r"disregard\s+above", re.IGNORECASE),
        severity="high",
        category="instruction_override",
    ),
    _ThreatPattern(
        name="instruction_override_oublie",
        regex=re.compile(r"oublie\s+les\s+instructions", re.IGNORECASE),
        severity="high",
        category="instruction_override",
    ),
    _ThreatPattern(
        name="instruction_override_ignore_consignes",
        regex=re.compile(r"ignore\s+les\s+consignes", re.IGNORECASE),
        severity="high",
        category="instruction_override",
    ),
    # --- Prompt leaking (medium) ---
    _ThreatPattern(
        name="prompt_leaking_repeat",
        regex=re.compile(r"repeat\s+the\s+above", re.IGNORECASE),
        severity="medium",
        category="prompt_leaking",
    ),
    _ThreatPattern(
        name="prompt_leaking_show_prompt",
        regex=re.compile(r"show\s+me\s+your\s+prompt", re.IGNORECASE),
        severity="medium",
        category="prompt_leaking",
    ),
    _ThreatPattern(
        name="prompt_leaking_print_instructions",
        regex=re.compile(r"print\s+your\s+instructions", re.IGNORECASE),
        severity="medium",
        category="prompt_leaking",
    ),
    _ThreatPattern(
        name="prompt_leaking_affiche",
        regex=re.compile(r"affiche\s+tes\s+instructions", re.IGNORECASE),
        severity="medium",
        category="prompt_leaking",
    ),
    # --- Role switching (medium) ---
    _ThreatPattern(
        name="role_switching_you_are_now",
        regex=re.compile(r"you\s+are\s+now", re.IGNORECASE),
        severity="medium",
        category="role_switching",
    ),
    _ThreatPattern(
        name="role_switching_act_as",
        regex=re.compile(r"act\s+as", re.IGNORECASE),
        severity="medium",
        category="role_switching",
    ),
    _ThreatPattern(
        name="role_switching_pretend",
        regex=re.compile(r"pretend\s+to\s+be", re.IGNORECASE),
        severity="medium",
        category="role_switching",
    ),
    _ThreatPattern(
        name="role_switching_tu_es",
        regex=re.compile(r"tu\s+es\s+maintenant", re.IGNORECASE),
        severity="medium",
        category="role_switching",
    ),
    _ThreatPattern(
        name="role_switching_agis",
        regex=re.compile(r"agis\s+comme", re.IGNORECASE),
        severity="medium",
        category="role_switching",
    ),
    # --- Delimiter injection (medium) ---
    _ThreatPattern(
        name="delimiter_injection_hashes",
        regex=re.compile(r"###"),
        severity="medium",
        category="delimiter_injection",
    ),
    _ThreatPattern(
        name="delimiter_injection_end",
        regex=re.compile(r"---END---"),
        severity="medium",
        category="delimiter_injection",
    ),
    _ThreatPattern(
        name="delimiter_injection_equals",
        regex=re.compile(r"==="),
        severity="medium",
        category="delimiter_injection",
    ),
    _ThreatPattern(
        name="delimiter_injection_endoftext",
        regex=re.compile(r"<\|endoftext\|>"),
        severity="medium",
        category="delimiter_injection",
    ),
    _ThreatPattern(
        name="delimiter_injection_inst_close",
        regex=re.compile(r"\[/INST\]", re.IGNORECASE),
        severity="medium",
        category="delimiter_injection",
    ),
]


def sanitize(text: str) -> SanitizationResult:
    """Detect and escape prompt injection patterns in untrusted text.

    Matched patterns are replaced with ``[SANITIZED: <matched>]`` to neuter
    the injection while preserving readability for downstream extraction.
    """
    start = time.monotonic()

    threats: list[ThreatMatch] = []
    sanitized = text

    for pattern in _THREAT_PATTERNS:
        for match in pattern.regex.finditer(text):
            threats.append(
                ThreatMatch(
                    pattern_name=pattern.name,
                    matched_text=match.group(),
                    position=match.start(),
                    severity=pattern.severity,
                )
            )

    # Sort threats by position descending so replacements don't shift indices
    threats_sorted = sorted(threats, key=lambda t: t.position, reverse=True)
    for threat in threats_sorted:
        start_pos = threat.position
        end_pos = start_pos + len(threat.matched_text)
        sanitized = (
            sanitized[:start_pos]
            + f"[SANITIZED: {threat.matched_text}]"
            + sanitized[end_pos:]
        )

    # Re-sort threats by position ascending for output
    threats.sort(key=lambda t: t.position)

    duration_ms = int((time.monotonic() - start) * 1000)

    if threats:
        pattern_names = list({t.pattern_name for t in threats})
        severity_max = (
            "high"
            if any(t.severity == "high" for t in threats)
            else "medium"
            if any(t.severity == "medium" for t in threats)
            else "low"
        )
        logger.warning(
            "Prompt injection threats detected",
            extra={
                "component": "security.sanitizer",
                "context": {
                    "threat_count": len(threats),
                    "pattern_names": pattern_names,
                    "severity_max": severity_max,
                },
            },
        )

    return SanitizationResult(
        sanitized_text=sanitized,
        original_text=text,
        threats_detected=threats,
        threat_count=len(threats),
        sanitization_duration_ms=duration_ms,
    )
