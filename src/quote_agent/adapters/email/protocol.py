"""Protocol definition for email adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.adapters.email.models import IncomingEmail
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class EmailAdapter(Protocol):
    """Interface contract for email provider adapters."""

    async def health_check(self) -> ServiceHealth:
        """Check IMAP connectivity and authentication, return health status."""
        ...

    async def fetch_new_emails(self) -> list[IncomingEmail]:
        """Fetch unread emails from the mail server."""
        ...
