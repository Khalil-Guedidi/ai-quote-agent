"""Protocol definition for notification adapters.

Design decision: ``format_card`` is intentionally NOT part of this Protocol.
Card formatting is channel-specific (Teams uses Adaptive Cards, Slack uses Block Kit,
email uses HTML, webhooks use plain JSON). Each adapter transforms the universal
``NotificationPayload`` into its channel-specific format internally via
``send_notification()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.adapters.notification.models import NotificationPayload, NotificationResult
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class NotificationAdapter(Protocol):
    """Interface contract for notification channel adapters."""

    async def health_check(self) -> ServiceHealth:
        """Check notification channel connectivity, return health status."""
        ...

    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        """Send a notification through the channel, return delivery result."""
        ...
