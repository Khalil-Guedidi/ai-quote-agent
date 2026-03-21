"""Agent state schema — TypedDict flowing through the LangGraph pipeline.

NOTE: ``from __future__ import annotations`` is intentionally OMITTED here.
LangGraph's ``StateGraph`` calls ``get_type_hints()`` at graph-construction time
and requires all annotation names to be resolvable in the module's global scope.
Deferred annotations (PEP 563) break this resolution.
"""

from typing import Any

from typing_extensions import TypedDict

# Runtime imports — LangGraph resolves these via get_type_hints()
from quote_agent.adapters.erp.models import QuoteDraftResult
from quote_agent.agent.nodes.classifier import ClassificationResult
from quote_agent.agent.nodes.compliance_checker import ComplianceCheckResult
from quote_agent.agent.nodes.confidence_scorer import ConfidenceResult
from quote_agent.agent.nodes.reasoning_strategy import ReasoningResult
from quote_agent.agent.nodes.router import RoutingDecision
from quote_agent.agent.nodes.self_reviewer import SelfReviewResult
from quote_agent.services.extraction_models import ExtractedQuoteRequest


class AgentState(TypedDict, total=False):
    """State flowing through the LangGraph agent pipeline.

    Separated into: inputs / processing / outputs / meta.
    ``total=False`` allows partial updates from node return dicts.
    """

    # --- Inputs ---
    raw_request: ExtractedQuoteRequest

    # --- Processing ---
    classification: ClassificationResult | None
    reasoning: ReasoningResult | None
    confidence: ConfidenceResult | None
    routing_decision: RoutingDecision | None
    self_review: SelfReviewResult | None
    compliance: ComplianceCheckResult | None

    # --- Outputs ---
    draft_result: QuoteDraftResult | None

    # --- Meta ---
    error: str | None
    current_node: str
    final_action: str


def create_initial_state(request: ExtractedQuoteRequest) -> dict[str, Any]:
    """Build the initial agent state from an extracted quote request."""
    return {
        "raw_request": request,
        "classification": None,
        "reasoning": None,
        "confidence": None,
        "routing_decision": None,
        "self_review": None,
        "compliance": None,
        "draft_result": None,
        "error": None,
        "current_node": "",
        "final_action": "",
    }
