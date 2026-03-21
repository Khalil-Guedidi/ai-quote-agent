"""Odoo ERP adapter implementation using XML-RPC."""

from __future__ import annotations

import asyncio
import logging
import time
import xmlrpc.client
from typing import TYPE_CHECKING, Any, TypeVar

from quote_agent.adapters.erp.models import (
    Client,
    ClientOrderHistory,
    Product,
    ProductFilter,
    QuoteDraftResult,
    UniversalQuote,
)
from quote_agent.api.health import ServiceHealth

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from quote_agent.config import ERPSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0
_GET_PRODUCTS_TIMEOUT = 30.0
_GET_CLIENT_TIMEOUT = 30.0
_GET_ORDERS_TIMEOUT = 30.0
_GET_PRODUCT_BY_ID_TIMEOUT = 30.0
_CREATE_DRAFT_TIMEOUT = 30.0

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0
_RETRY_MAX_DELAY = 8.0

_T = TypeVar("_T")

_CLIENT_FIELDS = [
    "id",
    "name",
    "ref",
    "email",
    "phone",
    "street",
    "city",
    "zip",
    "country_id",
    "vat",
    "active",
    "customer_rank",
]

_ORDER_FIELDS = [
    "id",
    "name",
    "date_order",
    "state",
    "amount_total",
    "partner_id",
]

_ORDER_LINE_FIELDS = [
    "id",
    "product_id",
    "name",
    "product_uom_qty",
    "price_unit",
    "price_subtotal",
]

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


def _map_odoo_client(record: dict[str, Any]) -> Client:
    """Map an Odoo res.partner record dict to a Client DTO."""
    odoo_id: int = record["id"]
    name: str = record.get("name", "")
    ref = _odoo_str(record.get("ref"))
    email = _odoo_str(record.get("email"))
    phone = _odoo_str(record.get("phone"))

    # Build address from street, city, zip, country
    address_parts: list[str] = []
    street = _odoo_str(record.get("street"))
    if street:
        address_parts.append(street)
    city = _odoo_str(record.get("city"))
    zip_code = _odoo_str(record.get("zip"))
    if city and zip_code:
        address_parts.append(f"{zip_code} {city}")
    elif city:
        address_parts.append(city)
    country = record.get("country_id")
    if isinstance(country, (list, tuple)) and len(country) > 1:
        address_parts.append(str(country[1]))
    address = ", ".join(address_parts) if address_parts else None

    vat = _odoo_str(record.get("vat"))
    is_active: bool = bool(record.get("active", True))

    metadata: dict[str, Any] = {}
    customer_rank = record.get("customer_rank", 0)
    if isinstance(customer_rank, int) and customer_rank > 0:
        metadata["customer_rank"] = customer_rank

    return Client(
        odoo_id=odoo_id,
        name=name,
        ref=ref,
        email=email,
        phone=phone,
        address=address,
        vat=vat,
        is_active=is_active,
        metadata=metadata,
    )


def _map_odoo_order_line(
    line: dict[str, Any], order_name: str, order_date: str, order_state: str,
) -> ClientOrderHistory:
    """Map an Odoo sale.order.line record to a ClientOrderHistory DTO."""
    product = line.get("product_id")
    product_name = product[1] if isinstance(product, (list, tuple)) and len(product) > 1 else "Unknown"

    return ClientOrderHistory(
        order_id=order_name,
        date=order_date,
        product_ref=None,  # Not available on order line directly
        product_name=product_name,
        quantity=float(line.get("product_uom_qty", 0)),
        unit_price=float(line.get("price_unit", 0)),
        total=float(line.get("price_subtotal", 0)),
        state=order_state,
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

    async def _retry_with_backoff(
        self,
        operation: Callable[..., Coroutine[Any, Any, _T]],
        *args: Any,
    ) -> _T:
        """Retry an async operation with exponential backoff."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await operation(*args)
            except (ConnectionRefusedError, OSError, xmlrpc.client.Error) as exc:
                if attempt == _MAX_RETRIES:
                    logger.error(
                        "ERP operation failed after %d retries — queuing for later retry: %s",
                        _MAX_RETRIES,
                        exc,
                        extra={
                            "context": {
                                "component": "adapters.erp.odoo",
                                "operation": operation.__name__,
                                "retries_exhausted": True,
                                "max_retries": _MAX_RETRIES,
                            },
                        },
                    )
                    raise
                delay = min(_RETRY_BASE_DELAY * (2 ** (attempt - 1)), _RETRY_MAX_DELAY)
                logger.warning(
                    "ERP retry %d/%d after %.1fs: %s",
                    attempt,
                    _MAX_RETRIES,
                    delay,
                    exc,
                    extra={"context": {"component": "adapters.erp.odoo", "attempt": attempt, "delay": delay}},
                )
                await asyncio.sleep(delay)
        msg = "Unreachable"  # pragma: no cover
        raise RuntimeError(msg)  # pragma: no cover

    async def get_client(self, client_id: str) -> Client:
        """Fetch a single client by ID or ref from Odoo with retry."""
        return await self._retry_with_backoff(self._get_client_impl, client_id)

    async def _get_client_impl(self, client_id: str) -> Client:
        """Execute the XML-RPC call to fetch a client."""
        start = time.monotonic()
        uid = await self._ensure_uid()
        url = self._settings.url
        proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        db = self._settings.database
        api_key = self._settings.api_key.get_secret_value()

        # Support both numeric ID and string ref
        try:
            numeric_id = int(client_id)
            domain: list[Any] = [("id", "=", numeric_id)]
        except ValueError:
            domain = [("ref", "=", client_id)]

        records: list[dict[str, Any]] = await asyncio.wait_for(
            asyncio.to_thread(
                proxy.execute_kw,  # type: ignore[arg-type]
                db,
                uid,
                api_key,
                "res.partner",
                "search_read",
                [domain],
                {"fields": _CLIENT_FIELDS, "limit": 1},
            ),
            timeout=_GET_CLIENT_TIMEOUT,
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        ctx = {
            "component": "adapters.erp.odoo",
            "operation": "get_client",
            "client_id": client_id,
            "duration_ms": duration_ms,
        }
        if not records:
            logger.info("Client not found: %s", client_id, extra={"context": ctx})
            msg = f"Client not found: {client_id}"
            raise ValueError(msg)

        logger.info("Client fetched successfully", extra={"context": ctx})
        return _map_odoo_client(records[0])

    async def get_client_orders(self, client_id: str, limit: int = 20) -> list[ClientOrderHistory]:
        """Fetch recent order history for a client with retry."""
        return await self._retry_with_backoff(self._get_client_orders_impl, client_id, limit)

    async def _get_client_orders_impl(self, client_id: str, limit: int) -> list[ClientOrderHistory]:
        """Execute the XML-RPC calls to fetch client order history."""
        start = time.monotonic()
        # First resolve client to get the numeric partner ID
        client = await self._get_client_impl(client_id)
        partner_odoo_id = client.odoo_id

        uid = await self._ensure_uid()
        url = self._settings.url
        proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        db = self._settings.database
        api_key = self._settings.api_key.get_secret_value()

        # Fetch orders (sale + done states only)
        order_domain: list[Any] = [
            ("partner_id", "=", partner_odoo_id),
            ("state", "in", ["sale", "done"]),
        ]

        orders: list[dict[str, Any]] = await asyncio.wait_for(
            asyncio.to_thread(
                proxy.execute_kw,  # type: ignore[arg-type]
                db,
                uid,
                api_key,
                "sale.order",
                "search_read",
                [order_domain],
                {
                    "fields": _ORDER_FIELDS,
                    "limit": limit,
                    "order": "date_order desc",
                },
            ),
            timeout=_GET_ORDERS_TIMEOUT,
        )

        if not orders:
            duration_ms = int((time.monotonic() - start) * 1000)
            ctx = {
                "component": "adapters.erp.odoo",
                "operation": "get_client_orders",
                "client_id": client_id,
                "duration_ms": duration_ms,
            }
            logger.info("No orders found for client", extra={"context": ctx})
            return []

        # Fetch order lines
        order_ids = [o["id"] for o in orders]
        lines: list[dict[str, Any]] = await asyncio.wait_for(
            asyncio.to_thread(
                proxy.execute_kw,  # type: ignore[arg-type]
                db,
                uid,
                api_key,
                "sale.order.line",
                "search_read",
                [[("order_id", "in", order_ids)]],
                {"fields": _ORDER_LINE_FIELDS},
            ),
            timeout=_GET_ORDERS_TIMEOUT,
        )

        # Build order lookup: order_id -> (name, date, state)
        order_lookup: dict[int, tuple[str, str, str]] = {}
        for order in orders:
            order_id: int = order["id"]
            order_name: str = order.get("name", f"SO{order_id}")
            date_str = str(order.get("date_order", ""))
            state: str = order.get("state", "unknown")
            order_lookup[order_id] = (order_name, date_str, state)

        # Map lines to DTOs
        result: list[ClientOrderHistory] = []
        for line in lines:
            line_order_id = line.get("order_id")
            if isinstance(line_order_id, (list, tuple)):
                line_order_id = line_order_id[0]
            if line_order_id in order_lookup:
                order_name, date_str, state = order_lookup[line_order_id]
                result.append(_map_odoo_order_line(line, order_name, date_str, state))

        duration_ms = int((time.monotonic() - start) * 1000)
        ctx = {
            "component": "adapters.erp.odoo",
            "operation": "get_client_orders",
            "client_id": client_id,
            "order_count": len(orders),
            "line_count": len(result),
            "duration_ms": duration_ms,
        }
        logger.info("Client orders fetched successfully", extra={"context": ctx})
        return result

    async def get_product_by_id(self, product_id: int) -> Product:
        """Fetch a single product by its Odoo ID with retry."""
        return await self._retry_with_backoff(self._get_product_by_id_impl, product_id)

    async def _get_product_by_id_impl(self, product_id: int) -> Product:
        """Execute the XML-RPC call to fetch a single product."""
        start = time.monotonic()
        uid = await self._ensure_uid()
        url = self._settings.url
        proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        db = self._settings.database
        api_key = self._settings.api_key.get_secret_value()

        records: list[dict[str, Any]] = await asyncio.wait_for(
            asyncio.to_thread(
                proxy.execute_kw,  # type: ignore[arg-type]
                db,
                uid,
                api_key,
                "product.product",
                "search_read",
                [[("id", "=", product_id)]],
                {"fields": _ODOO_FIELDS, "limit": 1},
            ),
            timeout=_GET_PRODUCT_BY_ID_TIMEOUT,
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        ctx = {
            "component": "adapters.erp.odoo",
            "operation": "get_product_by_id",
            "product_id": product_id,
            "duration_ms": duration_ms,
        }
        if not records:
            logger.info("Product not found: %d", product_id, extra={"context": ctx})
            msg = f"Product not found: {product_id}"
            raise ValueError(msg)

        logger.info("Product fetched successfully", extra={"context": ctx},
        )
        return _map_odoo_product(records[0])

    async def create_draft_quote(self, quote: UniversalQuote) -> QuoteDraftResult:
        """Create a draft quotation in Odoo with retry."""
        return await self._retry_with_backoff(self._create_draft_quote_impl, quote)

    @staticmethod
    def _build_odoo_order_values(quote: UniversalQuote, partner_odoo_id: int) -> dict[str, Any]:
        """Build the Odoo sale.order create values dict."""
        order_lines: list[list[Any]] = []
        for line in quote.lines:
            line_vals: dict[str, Any] = {
                "product_id": line.product_id,
                "product_uom_qty": line.quantity,
                "price_unit": line.unit_price,
            }
            if line.description:
                line_vals["name"] = line.description
            order_lines.append([0, 0, line_vals])

        values: dict[str, Any] = {
            "partner_id": partner_odoo_id,
            "order_line": order_lines,
        }
        if quote.delivery_date:
            values["commitment_date"] = quote.delivery_date

        return values

    async def _create_draft_quote_impl(self, quote: UniversalQuote) -> QuoteDraftResult:
        """Execute the XML-RPC calls to create a draft quote in Odoo."""
        start = time.monotonic()

        # Resolve client to get Odoo integer ID
        client = await self._get_client_impl(quote.client_id)
        partner_odoo_id = client.odoo_id

        uid = await self._ensure_uid()
        url = self._settings.url
        proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        db = self._settings.database
        api_key = self._settings.api_key.get_secret_value()

        # Build order values
        values = self._build_odoo_order_values(quote, partner_odoo_id)

        # Create the sale.order
        order_id: int = await asyncio.wait_for(
            asyncio.to_thread(
                proxy.execute_kw,  # type: ignore[arg-type]
                db,
                uid,
                api_key,
                "sale.order",
                "create",
                [values],
            ),
            timeout=_CREATE_DRAFT_TIMEOUT,
        )

        # Read back to get order reference
        order_data: list[dict[str, Any]] = await asyncio.wait_for(
            asyncio.to_thread(
                proxy.execute_kw,  # type: ignore[arg-type]
                db,
                uid,
                api_key,
                "sale.order",
                "read",
                [order_id],
                {"fields": ["name", "state", "order_line"]},
            ),
            timeout=_CREATE_DRAFT_TIMEOUT,
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        order_ref = order_data[0]["name"] if order_data else f"SO{order_id}"
        order_state = order_data[0].get("state", "draft") if order_data else "draft"
        order_lines_ids = order_data[0].get("order_line", []) if order_data else []

        ctx = {
            "component": "adapters.erp.odoo",
            "operation": "create_draft_quote",
            "partner_id": partner_odoo_id,
            "product_count": len(quote.lines),
            "draft_id": order_id,
            "duration_ms": duration_ms,
        }
        logger.info("Draft quote created successfully", extra={"context": ctx})

        return QuoteDraftResult(
            odoo_id=order_id,
            order_reference=order_ref,
            state=order_state,
            line_count=len(order_lines_ids),
        )
