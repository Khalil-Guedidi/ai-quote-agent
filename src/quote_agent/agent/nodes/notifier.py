"""Notification nodes — fire-and-forget Teams cards for quote-ready and multi-proposal."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from quote_agent.adapters.notification.models import NotificationPayload

if TYPE_CHECKING:
    from quote_agent.adapters.notification.models import NotificationResult
    from quote_agent.adapters.notification.teams import TeamsAdapter
    from quote_agent.agent.state import AgentState
    from quote_agent.config import ERPSettings

logger = logging.getLogger(__name__)


async def notify_quote_ready(
    state: AgentState,
    notification_adapter: TeamsAdapter,
    erp_settings: ERPSettings,
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
    notification_adapter: TeamsAdapter,
    erp_settings: ERPSettings,
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
