"""Notification dispatcher — coordination layer between pipeline nodes and adapter.

Sits between LangGraph notifier nodes and the TeamsAdapter. Nodes determine
WHICH notification to send; the dispatcher controls WHEN and WHETHER to send it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quote_agent.adapters.notification.models import NotificationPayload
    from quote_agent.adapters.notification.teams import TeamsAdapter
    from quote_agent.services.notification_throttle import NotificationBatcher, NotificationThrottle

logger = logging.getLogger(__name__)


async def dispatch_quote_notification(
    *,
    payload: NotificationPayload | None,
    adapter: TeamsAdapter,
    throttle: NotificationThrottle,
    batcher: NotificationBatcher,
) -> dict[str, object]:
    """Dispatch a notification through throttle + batcher checks.

    Returns a dict with ``sent`` (bool), ``reason`` (str), and optionally
    ``notification_result``.

    Flow:
        1. If no payload → silence (AC-3)
        2. Record event for burst detection
        3. If bursting → defer to batch summary
        4. If rate-limited → defer
        5. Otherwise → send immediately + record send
    """
    if payload is None:
        return {"sent": False, "reason": "no-payload", "notification_result": None}

    recipient = adapter.hostname

    # Always record the event for burst detection
    batcher.record_event(recipient)

    # Check burst threshold first
    if batcher.should_batch(recipient):
        logger.info(
            "Notification batched (burst threshold exceeded)",
            extra={"context": {"recipient": recipient, "pending": batcher.get_pending_count(recipient)}},
        )
        return {"sent": False, "reason": "batched", "notification_result": None}

    # Check rate limiter
    if not throttle.can_send(recipient):
        remaining = throttle.time_until_allowed(recipient)
        logger.info(
            "Notification deferred (rate-limited)",
            extra={"context": {"recipient": recipient, "seconds_remaining": remaining}},
        )
        return {"sent": False, "reason": "rate-limited", "notification_result": None}

    # Send the notification
    try:
        result = await adapter.send_notification(payload)
        throttle.record_send(recipient)
        if not result.success:
            logger.warning(
                "Notification send returned failure",
                extra={"context": {"error": result.error, "status_code": result.status_code}},
            )
        return {"sent": True, "reason": "sent", "notification_result": result}
    except Exception:
        logger.warning("Notification dispatch raised an exception", exc_info=True)
        return {"sent": False, "reason": "error", "notification_result": None}
