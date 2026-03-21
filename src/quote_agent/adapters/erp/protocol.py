"""Protocol definition for ERP adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quote_agent.adapters.erp.models import Client, ClientOrderHistory, Product, ProductFilter
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

    async def get_client(self, client_id: str) -> Client:
        """Fetch a single client by ID or ref from ERP."""
        ...

    async def get_client_orders(self, client_id: str, limit: int = 20) -> list[ClientOrderHistory]:
        """Fetch recent order history for a client."""
        ...

    async def get_product_by_id(self, product_id: int) -> Product:
        """Fetch a single product by its Odoo ID."""
        ...
