"""Odoo ERP adapter implementation using XML-RPC."""

from __future__ import annotations

import asyncio
import logging
import time
import xmlrpc.client
from typing import TYPE_CHECKING, Any

from quote_agent.adapters.erp.models import Product, ProductFilter
from quote_agent.api.health import ServiceHealth

if TYPE_CHECKING:
    from quote_agent.config import ERPSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0
_GET_PRODUCTS_TIMEOUT = 30.0

_ODOO_FIELDS = [
    "id",
    "default_code",
    "name",
    "description_sale",
    "categ_id",
    "list_price",
    "active",
    "barcode",
    "type",
    "sale_ok",
    "uom_id",
    "weight",
]


def _odoo_str(val: Any) -> str | None:
    """Convert Odoo False to None, keep strings."""
    return val if isinstance(val, str) else None


def _map_odoo_product(record: dict[str, Any]) -> Product:
    """Map an Odoo product.product record dict to a Product DTO."""
    odoo_id: int = record["id"]

    reference = _odoo_str(record.get("default_code")) or ""
    name: str = record.get("name", "")
    description = _odoo_str(record.get("description_sale"))

    categ = record.get("categ_id")
    category = categ[1] if isinstance(categ, (list, tuple)) and len(categ) > 1 else "Uncategorized"

    unit_price: float = float(record.get("list_price", 0.0))
    is_active: bool = bool(record.get("active", True))
    stock_status = "in_stock"  # stock module not available in Community base

    # Build metadata from optional fields
    metadata: dict[str, Any] = {}
    barcode = _odoo_str(record.get("barcode"))
    if barcode:
        metadata["barcode"] = barcode
    product_type = _odoo_str(record.get("type"))
    if product_type:
        metadata["type"] = product_type
    sale_ok = record.get("sale_ok")
    if sale_ok is not False:
        metadata["sale_ok"] = bool(sale_ok)
    uom = record.get("uom_id")
    if isinstance(uom, (list, tuple)) and len(uom) > 1:
        metadata["uom"] = uom[1]
    weight = record.get("weight")
    if isinstance(weight, (int, float)) and weight:
        metadata["weight_kg"] = float(weight)

    return Product(
        odoo_id=odoo_id,
        reference=reference,
        name=name,
        description=description,
        category=category,
        unit_price=unit_price,
        stock_status=stock_status,
        is_active=is_active,
        metadata=metadata,
    )


class OdooAdapter:
    """ERP adapter for Odoo via XML-RPC."""

    def __init__(self, settings: ERPSettings) -> None:
        self._settings = settings
        self._last_health: ServiceHealth | None = None
        self._last_health_time: float = 0.0
        self._uid: int | None = None

    async def health_check(self) -> ServiceHealth:
        """Check Odoo connectivity and authentication with 30s caching."""
        now = time.monotonic()
        if self._last_health and (now - self._last_health_time) < _HEALTH_CACHE_TTL:
            return self._last_health

        try:
            health = await asyncio.wait_for(
                self._perform_health_check(),
                timeout=_HEALTH_CHECK_TIMEOUT,
            )
        except TimeoutError:
            health = ServiceHealth(status="unhealthy", error="Health check timed out")
        except (ConnectionRefusedError, OSError, xmlrpc.client.Error) as exc:
            logger.warning("ERP health check failed: %s", exc)
            health = ServiceHealth(status="unhealthy", error=str(exc))

        self._last_health = health
        self._last_health_time = time.monotonic()
        return health

    async def _perform_health_check(self) -> ServiceHealth:
        """Execute XML-RPC version + authenticate calls."""
        url = self._settings.url
        proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")

        # Step 1: Check connectivity (no auth needed)
        await asyncio.to_thread(proxy.version)

        # Step 2: Verify credentials
        uid = await asyncio.to_thread(
            proxy.authenticate,
            self._settings.database,
            self._settings.username,
            self._settings.api_key.get_secret_value(),
            {},
        )

        if not uid:
            return ServiceHealth(
                status="unhealthy",
                error="Authentication failed: invalid credentials",
            )

        return ServiceHealth(status="healthy")

    async def _ensure_uid(self) -> int:
        """Authenticate and cache the Odoo uid. Reuses cached uid across calls."""
        if self._uid is not None:
            return self._uid

        url = self._settings.url
        common_proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = await asyncio.to_thread(
            common_proxy.authenticate,
            self._settings.database,
            self._settings.username,
            self._settings.api_key.get_secret_value(),
            {},
        )
        if not uid or not isinstance(uid, int):
            msg = "Odoo authentication failed"
            raise RuntimeError(msg)

        self._uid = uid
        return self._uid

    async def get_products(self, filters: ProductFilter) -> list[Product]:
        """Fetch products from Odoo via XML-RPC search_read with pagination."""
        uid = await self._ensure_uid()

        url = self._settings.url
        proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        db = self._settings.database
        api_key = self._settings.api_key.get_secret_value()

        # Build domain filter
        domain: list[Any] = []
        if filters.active_only:
            domain.append(("active", "=", True))
        if filters.category:
            domain.append(("categ_id.name", "=", filters.category))

        # Include archived products when not filtering by active_only
        context: dict[str, Any] = {}
        if not filters.active_only:
            context["active_test"] = False

        records: list[dict[str, Any]] = await asyncio.wait_for(
            asyncio.to_thread(
                proxy.execute_kw,  # type: ignore[arg-type]
                db,
                uid,
                api_key,
                "product.product",
                "search_read",
                [domain],
                {
                    "fields": _ODOO_FIELDS,
                    "limit": filters.limit,
                    "offset": filters.offset,
                    "order": "id asc",
                    "context": context,
                },
            ),
            timeout=_GET_PRODUCTS_TIMEOUT,
        )

        return [_map_odoo_product(record) for record in records]
