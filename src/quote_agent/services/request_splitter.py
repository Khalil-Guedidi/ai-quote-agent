"""Multi-request splitting service — groups line items into distinct quote requests."""

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
    SplitDecision,
    SplitResult,
)

logger = logging.getLogger(__name__)

_SPLITTING_TIMEOUT = 10.0  # NFR-P3: < 10 seconds

SPLITTING_SYSTEM_PROMPT = """You are a request grouping assistant for a French B2B industrial quote processing system.

You receive a list of extracted product line items from a single email. Your task: determine if these items represent ONE quote request or MULTIPLE distinct quote requests.

Grouping rules:
- Items that would logically appear on the SAME quote belong together (same project, same delivery, related products)
- Items that are clearly for DIFFERENT purposes/projects/clients should be separate groups
- When in doubt, keep items together (prefer fewer groups over more)
- A single item is always one group
- Consider: delivery address differences, project references, product category coherence

Output the grouping as a list of groups, each containing the indices of line items that belong together.
If ALL items belong to one request, output a single group with all indices."""


async def split_requests(extraction_result: ExtractionResult) -> SplitResult:
    """Split an extraction result into one or more sub-requests.

    Short-circuits for 0 or 1 line items. Uses LLM for 2+ items.
    On LLM failure, falls back to treating all items as a single request.

    Raises:
        LLMTimeoutError: If splitting exceeds 10s (NFR-P3).
        AdapterError: If the LLM provider returns an error.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    line_items = extraction_result.request.line_items

    # Short-circuit: 0 or 1 items -> no splitting needed
    if len(line_items) <= 1:
        return SplitResult(
            requests=[extraction_result.request],
            split_count=1,
            split_rationale="Single or no line items — no splitting needed",
            split_duration_ms=0,
        )

    # LLM-based grouping for 2+ items
    adapter = get_llm_adapter()
    model = adapter.get_model("simple")
    structured_model = model.with_structured_output(SplitDecision)

    items_text = "\n".join(
        f"[{i}] {item.description} (qty: {item.quantity}, unit: {item.unit}, ref: {item.reference}, specs: {item.specifications})"
        for i, item in enumerate(line_items)
    )

    messages = [
        SystemMessage(content=SPLITTING_SYSTEM_PROMPT),
        HumanMessage(content=f"Line items to group:\n{items_text}"),
    ]

    start_s = time.monotonic()
    try:
        decision: SplitDecision = await asyncio.wait_for(
            structured_model.ainvoke(messages),
            timeout=_SPLITTING_TIMEOUT,
        )
    except TimeoutError as exc:
        raise LLMTimeoutError("Splitting timed out after 10s (NFR-P3)") from exc
    except openai.APITimeoutError as exc:
        raise LLMTimeoutError(str(exc)) from exc
    except (openai.AuthenticationError, openai.APIConnectionError, openai.RateLimitError) as exc:
        raise AdapterError(str(exc)) from exc

    duration_ms = int((time.monotonic() - start_s) * 1000)

    # Build sub-requests from LLM grouping decision
    base = extraction_result.request
    sub_requests: list[ExtractedQuoteRequest] = []
    rationale_parts: list[str] = []

    for group in decision.groups:
        grouped_items = [line_items[i] for i in group.line_item_indices if i < len(line_items)]
        sub_request = base.model_copy(update={"line_items": grouped_items})
        sub_requests.append(sub_request)
        rationale_parts.append(group.rationale)

    # Safety: if LLM returned empty groups, fall back to single request
    if not sub_requests:
        sub_requests = [base]
        rationale_parts = ["LLM returned empty groups — fallback to single request"]

    return SplitResult(
        requests=sub_requests,
        split_count=len(sub_requests),
        split_rationale="; ".join(rationale_parts),
        split_duration_ms=duration_ms,
    )
