"""Protocol definition for notification adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class NotificationAdapter(Protocol):
    """Interface contract for notification channel adapters."""

    async def health_check(self) -> ServiceHealth:
        """Check notification channel connectivity, return health status."""
        ...

    # Future methods (Epic 5):
    # async def send_notification(...) -> NotificationResult
