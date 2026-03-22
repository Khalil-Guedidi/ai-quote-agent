"""Log-based notification adapter — writes notifications to structured logs.

Useful for dev/test environments where a Teams webhook is unavailable.
Proves adapter pattern extensibility without requiring external services.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from quote_agent.adapters.notification.models import NotificationPayload, NotificationResult
from quote_agent.api.health import ServiceHealth

logger = logging.getLogger(__name__)


class LogAdapter:
    """Notification adapter that logs payloads instead of sending to a channel."""

    @property
    def hostname(self) -> str:
        """Channel identifier for throttle/batcher recipient tracking."""
        return "log://local"

    async def health_check(self) -> ServiceHealth:
        """Always healthy — no external dependency."""
        return ServiceHealth(status="healthy")

    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        """Log the notification payload and return a success result."""
        logger.info(
            "Notification sent via log adapter",
            extra={
                "context": {
                    "card_type": payload.card_type,
                    "title": payload.title,
                    "message": payload.message,
                }
            },
        )
        return NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
