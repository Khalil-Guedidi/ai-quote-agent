"""Notification nodes — fire-and-forget notifications for quote-ready, multi-proposal, and escalation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from quote_agent.adapters.notification.models import NotificationPayload

if TYPE_CHECKING:
    from quote_agent.adapters.notification.models import NotificationResult
    from quote_agent.adapters.notification.protocol import NotificationAdapter
    from quote_agent.agent.state import AgentState
    from quote_agent.config import ERPSettings
    from quote_agent.services.notification_throttle import NotificationBatcher, NotificationThrottle

logger = logging.getLogger(__name__)


async def notify_quote_ready(
    state: AgentState,
    notification_adapter: NotificationAdapter,
    erp_settings: ERPSettings,
    throttle: NotificationThrottle | None = None,
    batcher: NotificationBatcher | None = None,
) -> dict[str, object]:
    """Send a quote-ready notification after successful draft creation.

    This node is fire-and-forget: notification failures are logged but never
    propagate as pipeline errors.
    """
    draft_result = state.get("draft_result")
    if draft_result is None:
        logger.warning("notify_quote_ready: no draft_result in state, skipping notification")
        return {"notification_result": None, "current_node": "notify"}

    raw_request = state["raw_request"]
    confidence = state.get("confidence")
    confidence_pct = str(round(confidence.overall_confidence * 100)) if confidence else "?"

    client_name = raw_request.client_name or "?"
    first_item = raw_request.line_items[0] if raw_request.line_items else None
    product_name = first_item.description if first_item else "?"
    quantity = str(first_item.quantity) if first_item and first_item.quantity else "?"

    erp_url = f"{erp_settings.url}/web#id={draft_result.odoo_id}&model=sale.order&view_type=form"

    payload = NotificationPayload(
        title="Devis prêt",
        message=f"Salut ! Devis pour {client_name} prêt. Check quand t'as le temps.",
        card_type="quote-ready",
        data={
            "client": client_name,
            "product": product_name,
            "quantity": quantity,
            "confidence_pct": confidence_pct,
            "erp_url": erp_url,
        },
    )

    result: NotificationResult | None = None
    if throttle is not None and batcher is not None:
        from quote_agent.services.notification_dispatcher import dispatch_quote_notification

        dispatch_result = await dispatch_quote_notification(
            payload=payload, adapter=notification_adapter, throttle=throttle, batcher=batcher
        )
        result = dispatch_result.get("notification_result")  # type: ignore[assignment]
    else:
        try:
            result = await notification_adapter.send_notification(payload)
            if not result.success:
                logger.warning(
                    "Notification send returned failure",
                    extra={"context": {"error": result.error, "status_code": result.status_code}},
                )
        except Exception:
            logger.warning("Notification send raised an exception", exc_info=True)

    return {"notification_result": result, "current_node": "notify"}


async def notify_multi_proposal(
    state: AgentState,
    notification_adapter: NotificationAdapter,
    erp_settings: ERPSettings,
    throttle: NotificationThrottle | None = None,
    batcher: NotificationBatcher | None = None,
) -> dict[str, object]:
    """Send a multi-proposal notification when the agent is uncertain.

    This node is fire-and-forget: notification failures are logged but never
    propagate as pipeline errors.
    """
    routing_decision = state.get("routing_decision")
    if routing_decision is None:
        logger.warning("notify_multi_proposal: no routing_decision in state, skipping notification")
        return {"notification_result": None, "current_node": "notify_proposals"}

    raw_request = state["raw_request"]
    client_name = raw_request.client_name or "?"
    proposals = routing_decision.proposals

    erp_url = f"{erp_settings.url}/web#model=sale.order&view_type=list"

    payload = NotificationPayload(
        title="Propositions",
        message=f"Pas sûr à 100% sur le produit. Voici mes {len(proposals)} options",
        card_type="multi-proposal",
        data={
            "client": client_name,
            "proposals": [
                {
                    "name": p.name,
                    "reference": p.reference,
                    "confidence_pct": str(round(p.confidence * 100)),
                    "match_quality": p.match_quality,
                }
                for p in proposals
            ],
            "erp_url": erp_url,
        },
    )

    result: NotificationResult | None = None
    if throttle is not None and batcher is not None:
        from quote_agent.services.notification_dispatcher import dispatch_quote_notification

        dispatch_result = await dispatch_quote_notification(
            payload=payload, adapter=notification_adapter, throttle=throttle, batcher=batcher
        )
        result = dispatch_result.get("notification_result")  # type: ignore[assignment]
    else:
        try:
            result = await notification_adapter.send_notification(payload)
            if not result.success:
                logger.warning(
                    "Notification send returned failure",
                    extra={"context": {"error": result.error, "status_code": result.status_code}},
                )
        except Exception:
            logger.warning("Notification send raised an exception", exc_info=True)

    return {"notification_result": result, "current_node": "notify_proposals"}


async def notify_escalation(
    state: AgentState,
    notification_adapter: NotificationAdapter,
    erp_settings: ERPSettings,
    throttle: NotificationThrottle | None = None,
    batcher: NotificationBatcher | None = None,
) -> dict[str, object]:
    """Send an escalation notification when the agent cannot process a request.

    This node is fire-and-forget: notification failures are logged but never
    propagate as pipeline errors.
    """
    routing_decision = state.get("routing_decision")
    if routing_decision is None:
        logger.warning("notify_escalation: no routing_decision in state, skipping notification")
        return {"notification_result": None, "current_node": "notify_escalation"}

    raw_request = state["raw_request"]
    client_name = raw_request.client_name or "?"

    escalation_ctx = routing_decision.escalation_context
    if escalation_ctx is not None:
        understood = escalation_ctx.understood
        uncertain = escalation_ctx.uncertain
        steps = escalation_ctx.suggested_next_steps
    else:
        # Fallback for out_of_scope — build context from classification
        classification = state.get("classification")
        understood = "; ".join(classification.reasons) if classification else "Demande classée hors périmètre"
        uncertain = "Cette demande ne correspond pas au périmètre de l'agent (pas un produit catalogue)"
        steps = ["Traiter la demande manuellement", "Vérifier si le client a besoin d'un autre service"]

    confidence_pct = str(round(routing_decision.confidence * 100))
    erp_url = f"{erp_settings.url}/web#model=sale.order&view_type=list"

    payload = NotificationPayload(
        title="Escalade",
        message=f"Celui-là est compliqué. {client_name} demande quelque chose que je ne suis pas sûr de comprendre.",
        card_type="escalation",
        data={
            "client": client_name,
            "understood": understood,
            "uncertain": uncertain,
            "suggested_next_steps": steps,
            "confidence_pct": confidence_pct,
            "erp_url": erp_url,
        },
    )

    result: NotificationResult | None = None
    if throttle is not None and batcher is not None:
        from quote_agent.services.notification_dispatcher import dispatch_quote_notification

        dispatch_result = await dispatch_quote_notification(
            payload=payload, adapter=notification_adapter, throttle=throttle, batcher=batcher
        )
        result = dispatch_result.get("notification_result")  # type: ignore[assignment]
    else:
        try:
            result = await notification_adapter.send_notification(payload)
            if not result.success:
                logger.warning(
                    "Notification send returned failure",
                    extra={"context": {"error": result.error, "status_code": result.status_code}},
                )
        except Exception:
            logger.warning("Notification send raised an exception", exc_info=True)

    return {"notification_result": result, "current_node": "notify_escalation"}
