"""Tier routing node — deterministic routing based on confidence thresholds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from quote_agent.agent.nodes.confidence_scorer import ProductConfidence  # noqa: TC001 — Pydantic needs runtime access

if TYPE_CHECKING:
    from quote_agent.agent.nodes.classifier import ClassificationResult
    from quote_agent.agent.nodes.confidence_scorer import ConfidenceResult
    from quote_agent.config import ConfidenceScoringSettings

RoutingAction = Literal["proceed_to_draft", "generate_proposals", "escalate", "notify_out_of_scope"]
RoutingTier = Literal["high", "medium", "low", "out_of_scope"]


class EscalationContext(BaseModel):
    """Context provided to sales rep when a request is escalated."""

    understood: str
    uncertain: str
    suggested_next_steps: list[str] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    """Result of the tier-based routing decision."""

    action: RoutingAction
    tier: RoutingTier
    confidence: float
    proposals: list[ProductConfidence] = Field(default_factory=list)
    escalation_context: EscalationContext | None = None


def route_by_confidence(
    confidence_result: ConfidenceResult,
    classification: ClassificationResult,
    settings: ConfidenceScoringSettings,
) -> RoutingDecision:
    """Route a scored request based on confidence thresholds — pure deterministic function.

    Routing rules:
    - out_of_scope classification → notify_out_of_scope (regardless of confidence)
    - overall_confidence > high_threshold → proceed_to_draft
    - overall_confidence >= low_threshold → generate_proposals (top 2-5 products)
    - overall_confidence < low_threshold → escalate
    """
    # Out-of-scope takes priority regardless of confidence
    if classification.complexity == "out_of_scope":
        return RoutingDecision(
            action="notify_out_of_scope",
            tier="out_of_scope",
            confidence=confidence_result.overall_confidence,
        )

    overall = confidence_result.overall_confidence

    # High confidence → proceed to draft
    if overall > settings.high_threshold:
        return RoutingDecision(
            action="proceed_to_draft",
            tier="high",
            confidence=overall,
        )

    # Medium confidence → generate proposals
    if overall >= settings.low_threshold:
        # Select top products with confidence > 0.0, sorted descending
        candidates = sorted(
            [p for p in confidence_result.product_scores if p.confidence > 0.0],
            key=lambda p: p.confidence,
            reverse=True,
        )
        proposals = candidates[: settings.max_proposals]
        # If fewer than min_proposals available, include all candidates
        if len(proposals) < settings.min_proposals:
            proposals = candidates

        return RoutingDecision(
            action="generate_proposals",
            tier="medium",
            confidence=overall,
            proposals=proposals,
        )

    # Low confidence → escalate
    # Build escalation context from classification + scoring reasoning
    understood_parts: list[str] = []
    uncertain_parts: list[str] = []
    for reason in classification.reasons:
        understood_parts.append(reason)
    for reason in confidence_result.reasoning:
        uncertain_parts.append(reason)

    escalation = EscalationContext(
        understood="; ".join(understood_parts) if understood_parts else "No clear understanding of the request",
        uncertain="; ".join(uncertain_parts) if uncertain_parts else "Overall match quality too low",
        suggested_next_steps=[
            "Demander des precisions au client sur les produits souhaites",
            "Verifier les references produit avec le client",
            "Proposer un appel pour clarifier les besoins",
        ],
    )

    return RoutingDecision(
        action="escalate",
        tier="low",
        confidence=overall,
        escalation_context=escalation,
    )
