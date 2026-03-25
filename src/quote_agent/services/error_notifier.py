"""Shared error notification helper — sends fire-and-forget error notifications."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def send_error_notification(error: str) -> None:
    """Send a fire-and-forget error notification after pipeline failure.

    This catches infrastructure failures (LLM timeout, DB down, etc.) that
    propagated through the graph as state["error"].
    """
    from quote_agent.adapters.notification import get_notification_adapter
    from quote_agent.adapters.notification.models import NotificationPayload

    payload = NotificationPayload(
        title="Erreur pipeline",
        message=f"Le pipeline a rencontré une erreur : {error}",
        card_type="escalation",
        data={
            "client": "?",
            "understood": "Erreur infrastructure détectée après exécution du pipeline",
            "uncertain": error,
            "suggested_next_steps": [
                "Vérifier les logs pour diagnostiquer l'erreur",
                "Vérifier la disponibilité des services (LLM, BDD, ERP)",
                "Relancer le traitement si transitoire",
            ],
            "confidence_pct": "0",
            "erp_url": "",
        },
    )

    try:
        adapter = get_notification_adapter()
        result = await adapter.send_notification(payload)
        if not result.success:
            logger.warning(
                "Error notification send returned failure",
                extra={"context": {"error": result.error, "status_code": result.status_code}},
            )
    except Exception:
        logger.warning("Error notification send raised an exception", exc_info=True)
