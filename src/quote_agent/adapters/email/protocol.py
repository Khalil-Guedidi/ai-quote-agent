"""Protocol definition for email adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class EmailAdapter(Protocol):
    """Interface contract for email provider adapters."""

    async def health_check(self) -> ServiceHealth:
        """Check IMAP connectivity and authentication, return health status."""
        ...

    # Future methods (Story 2.1):
    # async def fetch_emails(...) -> list[IncomingEmail]
