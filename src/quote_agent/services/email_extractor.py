"""LLM-based structured data extraction from quote request emails."""

from __future__ import annotations

import asyncio
import logging
import time

import openai

from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.exceptions import AdapterError, LLMTimeoutError
from quote_agent.services.extraction_models import (
    ExtractedQuoteRequest,
    ExtractionResult,
)

logger = logging.getLogger(__name__)

_EXTRACTION_TIMEOUT = 10.0  # NFR-P3: < 10 seconds

EXTRACTION_SYSTEM_PROMPT = """You are a data extraction assistant for a French B2B industrial quote processing system.

Your task: Extract structured data from a quote request email. The emails are in French (sometimes English).

Rules:
- Extract ALL requested products as separate line items
- For each product: description, quantity (number), unit (e.g., "pièces", "mètres", "kg"), specifications, reference
- Extract client identification: name, company, email, any identifier
- If a field is not mentioned in the email, set it to null — NEVER guess or hallucinate
- Product references may be codes like "REF-12345", "Art. 4567", catalog numbers
- Quantities may be written as "10 pcs", "10 unités", "une dizaine", "x10"
- French industrial terminology: "devis" = quote, "tarif" = price, "délai" = lead time, "livraison" = delivery

The email sender and subject are provided as additional context."""

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
    from langchain_core.messages import HumanMessage, SystemMessage

    if len(cleaned_content) < _MIN_CONTENT_LENGTH:
        return ExtractionResult(
            request=ExtractedQuoteRequest(raw_text=cleaned_content),
            confidence=0.0,
            missing_fields=["client_name", "client_identifier"],
            extraction_duration_ms=0,
        )

    adapter = get_llm_adapter()
    model = adapter.get_model("simple")
    structured_model = model.with_structured_output(ExtractedQuoteRequest)

    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=f"Sender: {sender}\nSubject: {subject}\n\n{cleaned_content}"),
    ]

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
