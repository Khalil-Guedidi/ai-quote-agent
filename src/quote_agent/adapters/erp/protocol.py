"""Protocol definition for ERP adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class ERPAdapter(Protocol):
    """Interface contract for ERP provider adapters."""

    async def health_check(self) -> ServiceHealth:
        """Check ERP connectivity and authentication, return health status."""
        ...

    # Future methods (Epic 3/4):
    # async def create_draft_quote(...) -> UniversalQuote
    # async def get_products(...) -> list[Product]
    # async def get_client(...) -> Client
