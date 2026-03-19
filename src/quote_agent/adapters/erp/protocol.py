"""Protocol definition for ERP adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.adapters.erp.models import Product, ProductFilter
    from quote_agent.api.health import ServiceHealth


@runtime_checkable
class ERPAdapter(Protocol):
    """Interface contract for ERP provider adapters."""

    async def health_check(self) -> ServiceHealth:
        """Check ERP connectivity and authentication, return health status."""
        ...

    async def get_products(self, filters: ProductFilter) -> list[Product]:
        """Fetch products from ERP with optional filtering and pagination."""
        ...
