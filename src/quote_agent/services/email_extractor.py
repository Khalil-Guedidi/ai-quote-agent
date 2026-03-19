"""LLM-based structured data extraction from quote request emails."""

from __future__ import annotations

import asyncio
import logging
import time

import openai

from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.exceptions import AdapterError, LLMTimeoutError
from quote_agent.security.input_isolation import EXTRACTION_SYSTEM_PROMPT
from quote_agent.services.extraction_models import (
    ExtractedQuoteRequest,
    ExtractionResult,
)

logger = logging.getLogger(__name__)

_EXTRACTION_TIMEOUT = 10.0  # NFR-P3: < 10 seconds

_MIN_CONTENT_LENGTH = 10


def _compute_missing_fields(request: ExtractedQuoteRequest) -> list[str]:
    """Identify fields that are absent (None) in the extraction result."""
    missing: list[str] = []
    if request.client_name is None:
        missing.append("client_name")
    if request.client_identifier is None:
        missing.append("client_identifier")
    for i, item in enumerate(request.line_items):
        if item.quantity is None:
            missing.append(f"line_items[{i}].quantity")
        if item.reference is None:
            missing.append(f"line_items[{i}].reference")
    return missing


async def extract(
    cleaned_content: str,
    sender: str,
    subject: str,
) -> ExtractionResult:
    """Extract structured quote request data from cleaned email content via LLM.

    Raises:
        LLMTimeoutError: If extraction exceeds 10s (NFR-P3).
        AdapterError: If the LLM provider returns an error.
    """
    from quote_agent.security.input_isolation import (
        build_extraction_messages,
        isolate_input,
    )

    if len(cleaned_content) < _MIN_CONTENT_LENGTH:
        return ExtractionResult(
            request=ExtractedQuoteRequest(raw_text=cleaned_content),
            confidence=0.0,
            missing_fields=["client_name", "client_identifier"],
            extraction_duration_ms=0,
        )

    isolated = isolate_input(cleaned_content, sender=sender, subject=subject)
    if isolated.sanitization_result.threat_count > 0:
        logger.warning(
            "Prompt injection threats detected in email",
            extra={
                "component": "security.sanitizer",
                "context": {
                    "threat_count": isolated.sanitization_result.threat_count,
                    "pattern_names": [
                        t.pattern_name
                        for t in isolated.sanitization_result.threats_detected
                    ],
                    "severity_max": (
                        "high"
                        if any(
                            t.severity == "high"
                            for t in isolated.sanitization_result.threats_detected
                        )
                        else "medium"
                        if any(
                            t.severity == "medium"
                            for t in isolated.sanitization_result.threats_detected
                        )
                        else "low"
                    ),
                },
            },
        )

    adapter = get_llm_adapter()
    model = adapter.get_model("simple")
    structured_model = model.with_structured_output(ExtractedQuoteRequest)

    messages = build_extraction_messages(isolated)

    start_s = time.monotonic()
    try:
        result: ExtractedQuoteRequest = await asyncio.wait_for(
            structured_model.ainvoke(messages),
            timeout=_EXTRACTION_TIMEOUT,
        )
    except TimeoutError as exc:
        raise LLMTimeoutError("Extraction timed out after 10s (NFR-P3)") from exc
    except openai.APITimeoutError as exc:
        raise LLMTimeoutError(str(exc)) from exc
    except (openai.AuthenticationError, openai.APIConnectionError, openai.RateLimitError) as exc:
        raise AdapterError(str(exc)) from exc

    duration_ms = int((time.monotonic() - start_s) * 1000)

    result = result.model_copy(update={"raw_text": cleaned_content})
    missing_fields = _compute_missing_fields(result)

    # Placeholder heuristic — proper confidence scoring comes in Epic 4
    confidence = 1.0
    if missing_fields:
        confidence = max(0.0, 1.0 - len(missing_fields) * 0.1)
    if not result.line_items:
        confidence = max(0.0, confidence - 0.3)

    return ExtractionResult(
        request=result,
        confidence=round(confidence, 2),
        missing_fields=missing_fields,
        extraction_duration_ms=duration_ms,
    )
