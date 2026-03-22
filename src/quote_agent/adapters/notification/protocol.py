"""Protocol definition for notification adapters."""

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
