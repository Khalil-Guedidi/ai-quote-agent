"""LangGraph agent graph — wires all pipeline nodes into a compiled StateGraph."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

from quote_agent.agent.state import AgentState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from quote_agent.adapters.erp.protocol import ERPAdapter
    from quote_agent.adapters.llm.openai_compat import OpenAICompatAdapter
    from quote_agent.config import Settings
    from quote_agent.search.engine import SearchEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------


def _route_after_router(state: AgentState) -> str:
    """Decide next node after the router based on routing action.

    Fallback routes to notify_escalation (not silent END) so unexpected
    routing failures are never silently dropped.
    """
    decision = state.get("routing_decision")
    if decision is not None:
        if decision.action == "proceed_to_draft":
            return "review"
        if decision.action == "generate_proposals":
            return "notify_proposals"
        if decision.action in ("escalate", "notify_out_of_scope"):
            return "notify_escalation"
    # Fallback: no routing decision (error state or unexpected) → escalation
    logger.warning("Route fallback: routing_decision is None — routing to notify_escalation")
    return "notify_escalation"


def _route_after_compliance(state: AgentState) -> str:
    """Decide whether to proceed to draft or notify rejection based on review + compliance."""
    # Error state (e.g. compliance node exception) → reject, don't silently continue to draft
    if state.get("error"):
        return "notify_rejection"

    review_result = state.get("self_review")
    if review_result is not None and not review_result.approved:
        return "notify_rejection"

    compliance_result = state.get("compliance")
    if compliance_result is not None:
        has_block = any(f.severity == "block" for f in compliance_result.flags)
        if has_block:
            return "notify_rejection"

    return "draft"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------


def build_agent_graph(
    llm_adapter: OpenAICompatAdapter,
    session_factory: async_sessionmaker[AsyncSession],
    erp_adapter: ERPAdapter,
    settings: Settings,
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and compile the full agent pipeline graph with injected dependencies.

    Dependencies are captured via closures in each node function.
    """
    from quote_agent.adapters.erp.models import (
        UniversalQuote,
        UniversalQuoteLine,
    )
    from quote_agent.adapters.notification import get_notification_adapter
    from quote_agent.agent.nodes.classifier import classify_request
    from quote_agent.agent.nodes.compliance_checker import check_compliance
    from quote_agent.agent.nodes.confidence_scorer import score_confidence
    from quote_agent.agent.nodes.notifier import (
        notify_escalation,
        notify_multi_proposal,
        notify_quote_ready,
        notify_rejection,
    )
    from quote_agent.agent.nodes.reasoning_strategy import apply_reasoning_strategy
    from quote_agent.agent.nodes.router import route_by_confidence
    from quote_agent.agent.nodes.self_reviewer import self_review
    from quote_agent.search import get_search_engine

    # -- Node wrappers (closures over injected deps) -----------------------

    def _has_error(state: AgentState) -> bool:
        """Return True if a previous node already set an error."""
        return bool(state.get("error"))

    async def classify_node(state: AgentState) -> dict[str, Any]:
        try:
            result = await classify_request(state["raw_request"], llm_adapter)
            return {"classification": result, "current_node": "classify"}
        except Exception as exc:
            logger.error("Node classify failed", extra={"context": {"error": str(exc)}})
            return {"error": f"classify: {exc}", "current_node": "classify"}

    async def reason_node(state: AgentState) -> dict[str, Any]:
        if _has_error(state):
            return {"current_node": "reason"}
        try:
            async with session_factory() as session:
                engine: SearchEngine = get_search_engine(session)
                result = await apply_reasoning_strategy(
                    state["classification"],  # type: ignore[arg-type]
                    state["raw_request"],
                    llm_adapter,
                    engine,
                )
            return {"reasoning": result, "current_node": "reason"}
        except Exception as exc:
            logger.error("Node reason failed", extra={"context": {"error": str(exc)}})
            return {"error": f"reason: {exc}", "current_node": "reason"}

    async def score_node(state: AgentState) -> dict[str, Any]:
        if _has_error(state):
            return {"current_node": "score"}
        try:
            reasoning = state["reasoning"]
            result = await score_confidence(
                state["classification"],  # type: ignore[arg-type]
                reasoning.search_result,  # type: ignore[union-attr]
                state["raw_request"],
                llm_adapter,
            )
            return {"confidence": result, "current_node": "score"}
        except Exception as exc:
            logger.error("Node score failed", extra={"context": {"error": str(exc)}})
            return {"error": f"score: {exc}", "current_node": "score"}

    async def route_node(state: AgentState) -> dict[str, Any]:
        if _has_error(state):
            return {"current_node": "route", "final_action": "routing_fallback"}
        try:
            decision = route_by_confidence(
                state["confidence"],  # type: ignore[arg-type]
                state["classification"],  # type: ignore[arg-type]
                settings.confidence_scoring,
            )
            final = decision.action if decision.action != "proceed_to_draft" else ""
            return {
                "routing_decision": decision,
                "final_action": final,
                "current_node": "route",
            }
        except Exception as exc:
            logger.error("Node route failed", extra={"context": {"error": str(exc)}})
            return {"error": f"route: {exc}", "current_node": "route"}

    async def review_node(state: AgentState) -> dict[str, Any]:
        if _has_error(state):
            return {"current_node": "review"}
        try:
            async with session_factory() as session:
                result = await self_review(
                    state["reasoning"],  # type: ignore[arg-type]
                    state["raw_request"],
                    llm_adapter,
                    session,
                )
            update: dict[str, Any] = {"self_review": result, "current_node": "review"}
            if not result.approved:
                update["final_action"] = "review_rejected"
            return update
        except Exception as exc:
            logger.error("Node review failed", extra={"context": {"error": str(exc)}})
            return {"error": f"review: {exc}", "current_node": "review"}

    async def compliance_node(state: AgentState) -> dict[str, Any]:
        if _has_error(state):
            return {"current_node": "compliance"}
        try:
            request = state["raw_request"]
            result = await check_compliance(
                request,
                llm_adapter,
                client_name=request.client_name,
            )
            update: dict[str, Any] = {"compliance": result, "current_node": "compliance"}
            if any(f.severity == "block" for f in result.flags):
                update["final_action"] = "compliance_blocked"
            return update
        except Exception as exc:
            logger.error("Node compliance failed", extra={"context": {"error": str(exc)}})
            return {"error": f"compliance: {exc}", "current_node": "compliance"}

    async def draft_node(state: AgentState) -> dict[str, Any]:
        if _has_error(state):
            return {"current_node": "draft"}
        try:
            request = state["raw_request"]
            reasoning = state["reasoning"]
            search_result = reasoning.search_result  # type: ignore[union-attr]
            top_product = search_result.results[0]

            # Build UniversalQuote from agent state
            first_item = request.line_items[0] if request.line_items else None
            quantity = (first_item.quantity if first_item and first_item.quantity else 1.0)
            line_description = first_item.description if first_item else top_product.name

            # Resolve the Odoo product ID from the local DB before building the quote
            async with session_factory() as session:
                from sqlalchemy import select

                from quote_agent.models.product import Product

                row = await session.execute(
                    select(Product.odoo_id).where(Product.id == top_product.product_id)
                )
                odoo_id = row.scalar_one_or_none()

            if odoo_id is None:
                logger.error(
                    "Node draft failed: no odoo_id for product",
                    extra={"context": {"product_id": str(top_product.product_id)}},
                )
                return {
                    "error": f"draft: product {top_product.reference} has no odoo_id",
                    "current_node": "draft",
                }

            quote = UniversalQuote(
                client_id=request.client_identifier or request.client_name or "unknown",
                client_name=request.client_name or "unknown",
                lines=[
                    UniversalQuoteLine(
                        product_id=odoo_id,
                        product_ref=top_product.reference,
                        product_name=top_product.name,
                        quantity=quantity,
                        unit_price=top_product.unit_price,
                        description=line_description,
                    ),
                ],
            )

            result = await erp_adapter.create_draft_quote(quote)
            return {
                "draft_result": result,
                "final_action": "proceed_to_draft",
                "current_node": "draft",
            }
        except Exception as exc:
            logger.error("Node draft failed", extra={"context": {"error": str(exc)}})
            return {"error": f"draft: {exc}", "current_node": "draft"}

    # -- Throttle + batcher singletons (shared across all notify nodes) ----
    from quote_agent.services.notification_throttle import NotificationBatcher, NotificationThrottle

    throttle = NotificationThrottle(rate_limit_seconds=float(settings.notification_batch.rate_limit_seconds))
    batcher = NotificationBatcher(
        burst_threshold=settings.notification_batch.burst_threshold,
        burst_window_seconds=float(settings.notification_batch.burst_window_seconds),
    )

    async def notify_node(state: AgentState) -> dict[str, Any]:
        try:
            adapter = get_notification_adapter()
            return await notify_quote_ready(state, adapter, throttle, batcher)
        except Exception as exc:
            logger.warning("Node notify failed (non-blocking)", extra={"context": {"error": str(exc)}})
            return {"notification_result": None, "current_node": "notify"}

    async def notify_proposals_node(state: AgentState) -> dict[str, Any]:
        try:
            adapter = get_notification_adapter()
            return await notify_multi_proposal(state, adapter, throttle, batcher)
        except Exception as exc:
            logger.warning("Node notify_proposals failed (non-blocking)", extra={"context": {"error": str(exc)}})
            return {"notification_result": None, "current_node": "notify_proposals"}

    async def notify_escalation_node(state: AgentState) -> dict[str, Any]:
        try:
            adapter = get_notification_adapter()
            return await notify_escalation(state, adapter, throttle, batcher)
        except Exception as exc:
            logger.warning("Node notify_escalation failed (non-blocking)", extra={"context": {"error": str(exc)}})
            return {"notification_result": None, "current_node": "notify_escalation"}

    async def notify_rejection_node(state: AgentState) -> dict[str, Any]:
        try:
            adapter = get_notification_adapter()
            return await notify_rejection(state, adapter, throttle, batcher)
        except Exception as exc:
            logger.warning("Node notify_rejection failed (non-blocking)", extra={"context": {"error": str(exc)}})
            return {"notification_result": None, "current_node": "notify_rejection"}

    # -- Wire the graph ----------------------------------------------------

    graph: StateGraph[AgentState] = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("reason", reason_node)
    graph.add_node("score", score_node)
    graph.add_node("route", route_node)
    graph.add_node("review", review_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("draft", draft_node)
    graph.add_node("notify", notify_node)
    graph.add_node("notify_proposals", notify_proposals_node)
    graph.add_node("notify_escalation", notify_escalation_node)
    graph.add_node("notify_rejection", notify_rejection_node)

    # Linear edges: START → classify → reason → score → route
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "reason")
    graph.add_edge("reason", "score")
    graph.add_edge("score", "route")

    # Conditional: route → review (high) | notify_proposals (medium) | notify_escalation (low/out_of_scope/fallback)
    graph.add_conditional_edges(
        "route",
        _route_after_router,
        {
            "review": "review",
            "notify_proposals": "notify_proposals",
            "notify_escalation": "notify_escalation",
        },
    )

    # Linear: review → compliance
    graph.add_edge("review", "compliance")

    # Conditional: compliance → draft (approved + compliant) OR notify_rejection (rejected/blocked)
    graph.add_conditional_edges(
        "compliance",
        _route_after_compliance,
        {"draft": "draft", "notify_rejection": "notify_rejection"},
    )

    # draft → notify → END
    graph.add_edge("draft", "notify")
    graph.add_edge("notify", END)

    # notify_proposals → END (medium-confidence path)
    graph.add_edge("notify_proposals", END)

    # notify_escalation → END (low-confidence / out-of-scope path)
    graph.add_edge("notify_escalation", END)

    # notify_rejection → END (review-rejected / compliance-blocked path)
    graph.add_edge("notify_rejection", END)

    return graph.compile()


def get_agent_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
    """Convenience factory — builds the agent graph using cached singletons."""
    from quote_agent.adapters.erp import get_erp_adapter
    from quote_agent.adapters.llm import get_llm_adapter
    from quote_agent.config import get_settings
    from quote_agent.models.base import _get_session_factory

    return build_agent_graph(
        llm_adapter=get_llm_adapter(),
        session_factory=_get_session_factory(),
        erp_adapter=get_erp_adapter(),
        settings=get_settings(),
    )
