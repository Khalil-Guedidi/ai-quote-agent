"""Tests for ERP adapter — client reads, order history, product by ID, retry logic, protocol compliance."""

from __future__ import annotations

import xmlrpc.client
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from quote_agent.adapters.erp.models import Client, ClientFilter, ClientOrderHistory
from quote_agent.adapters.erp.odoo import OdooAdapter, _map_odoo_client, _map_odoo_order_line
from quote_agent.adapters.erp.protocol import ERPAdapter


@pytest.fixture()
def erp_settings(env_vars: dict[str, str], _clear_settings_cache: None) -> Any:
    """Provide ERPSettings for tests."""
    from quote_agent.config import get_settings

    return get_settings().erp


@pytest.fixture()
def adapter(erp_settings: Any) -> OdooAdapter:
    """Create adapter with test settings."""
    return OdooAdapter(erp_settings)


# --- DTO Tests ---


class TestClientDTO:
    """Tests for the Client Pydantic DTO."""

    def test_client_required_fields(self) -> None:
        """Client DTO requires odoo_id and name."""
        client = Client(odoo_id=42, name="Test Corp")
        assert client.odoo_id == 42
        assert client.name == "Test Corp"
        assert client.ref is None
        assert client.email is None
        assert client.is_active is True

    def test_client_all_fields(self) -> None:
        """Client DTO accepts all optional fields."""
        client = Client(
            odoo_id=42,
            name="Test Corp",
            ref="CUST001",
            email="contact@test.com",
            phone="+33 1 23 45 67 89",
            address="1 Rue de la Paix, 75001 Paris, France",
            vat="FR12345678901",
            is_active=True,
            metadata={"customer_rank": 1},
        )
        assert client.ref == "CUST001"
        assert client.vat == "FR12345678901"


class TestClientOrderHistoryDTO:
    """Tests for the ClientOrderHistory Pydantic DTO."""

    def test_order_history_fields(self) -> None:
        """ClientOrderHistory DTO has all expected fields."""
        order = ClientOrderHistory(
            order_id="SO001",
            date="2026-01-15 10:30:00",
            product_ref="BOLT-M10",
            product_name="Boulon M10x50",
            quantity=100.0,
            unit_price=0.45,
            total=45.0,
            state="sale",
        )
        assert order.order_id == "SO001"
        assert order.quantity == 100.0

    def test_order_history_optional_product_ref(self) -> None:
        """product_ref is optional."""
        order = ClientOrderHistory(
            order_id="SO002",
            date="2026-01-10",
            product_name="Tube acier",
            quantity=10.0,
            unit_price=25.0,
            total=250.0,
            state="done",
        )
        assert order.product_ref is None


class TestClientFilterDTO:
    """Tests for the ClientFilter Pydantic DTO."""

    def test_defaults(self) -> None:
        """ClientFilter defaults are sensible."""
        f = ClientFilter()
        assert f.search_term is None
        assert f.limit == 20
        assert f.offset == 0


# --- Mapping Function Tests ---


class TestMapOdooClient:
    """Tests for _map_odoo_client helper."""

    def test_maps_full_record(self) -> None:
        """Maps a complete Odoo res.partner record."""
        record: dict[str, Any] = {
            "id": 42,
            "name": "Acme Corp",
            "ref": "CUST001",
            "email": "info@acme.com",
            "phone": "+33 1 23 45 67 89",
            "street": "10 Rue de Paris",
            "city": "Lyon",
            "zip": "69001",
            "country_id": [75, "France"],
            "vat": "FR12345678901",
            "active": True,
            "customer_rank": 1,
        }
        client = _map_odoo_client(record)
        assert client.odoo_id == 42
        assert client.name == "Acme Corp"
        assert client.ref == "CUST001"
        assert client.address == "10 Rue de Paris, 69001 Lyon, France"
        assert client.metadata == {"customer_rank": 1}

    def test_maps_record_with_false_fields(self) -> None:
        """Handles Odoo False values (common for empty fields)."""
        record: dict[str, Any] = {
            "id": 10,
            "name": "No Contact",
            "ref": False,
            "email": False,
            "phone": False,
            "street": False,
            "city": False,
            "zip": False,
            "country_id": False,
            "vat": False,
            "active": True,
            "customer_rank": 0,
        }
        client = _map_odoo_client(record)
        assert client.ref is None
        assert client.email is None
        assert client.address is None
        assert client.metadata == {}


class TestMapOdooOrderLine:
    """Tests for _map_odoo_order_line helper."""

    def test_maps_order_line(self) -> None:
        """Maps an Odoo sale.order.line record."""
        line: dict[str, Any] = {
            "id": 1,
            "product_id": [55, "Boulon M10x50"],
            "name": "Boulon M10x50 - Grade 8.8",
            "product_uom_qty": 100.0,
            "price_unit": 0.45,
            "price_subtotal": 45.0,
        }
        result = _map_odoo_order_line(line, "SO001", "2026-01-15", "sale")
        assert result.order_id == "SO001"
        assert result.product_name == "Boulon M10x50"
        assert result.quantity == 100.0
        assert result.total == 45.0
        assert result.state == "sale"

    def test_maps_order_line_missing_product(self) -> None:
        """Handles missing product_id gracefully."""
        line: dict[str, Any] = {
            "id": 2,
            "product_id": False,
            "name": "Custom item",
            "product_uom_qty": 1.0,
            "price_unit": 100.0,
            "price_subtotal": 100.0,
        }
        result = _map_odoo_order_line(line, "SO002", "2026-01-10", "done")
        assert result.product_name == "Unknown"


# --- get_client Tests ---


_SAMPLE_CLIENT_RECORD: dict[str, Any] = {
    "id": 42,
    "name": "ArcelorMittal",
    "ref": "AM001",
    "email": "contact@arcelor.com",
    "phone": "+33 1 23 45 67 89",
    "street": "1 Boulevard Oxygène",
    "city": "Saint-Denis",
    "zip": "93200",
    "country_id": [75, "France"],
    "vat": "FR12345678901",
    "active": True,
    "customer_rank": 1,
}


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_success_by_id(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """AC-2: get_client() returns Client DTO when found by numeric ID."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.return_value = [_SAMPLE_CLIENT_RECORD]

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    client = await adapter.get_client("42")
    assert isinstance(client, Client)
    assert client.odoo_id == 42
    assert client.name == "ArcelorMittal"
    assert client.ref == "AM001"


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_success_by_ref(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """AC-2: get_client() uses ref filter when client_id is not numeric."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.return_value = [_SAMPLE_CLIENT_RECORD]

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    client = await adapter.get_client("AM001")
    assert client.name == "ArcelorMittal"
    # Verify domain used ref filter — execute_kw(db, uid, api_key, model, method, [domain], {kwargs})
    call_args = mock_object.execute_kw.call_args
    domain_arg = call_args[0][5]  # 6th positional arg is the [domain] list
    assert domain_arg == [[("ref", "=", "AM001")]]


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_not_found(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """get_client() raises ValueError when client not found."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.return_value = []

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    with pytest.raises(ValueError, match="Client not found"):
        await adapter.get_client("999")


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_connection_error_retries(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """get_client() retries on ConnectionRefusedError and succeeds."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    # First call fails, second succeeds
    mock_object.execute_kw.side_effect = [
        ConnectionRefusedError("Connection refused"),
        [_SAMPLE_CLIENT_RECORD],
    ]

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    client = await adapter.get_client("42")
    assert client.name == "ArcelorMittal"
    assert mock_object.execute_kw.call_count == 2


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_timeout(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """get_client() raises TimeoutError on timeout."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()

    import asyncio

    async def slow_execute(*args: Any, **kwargs: Any) -> None:
        await asyncio.sleep(100)

    mock_object.execute_kw.side_effect = TimeoutError("timed out")

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    with pytest.raises(TimeoutError):
        await adapter.get_client("42")


# --- get_client_orders Tests ---


_SAMPLE_ORDERS: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "SO001",
        "date_order": "2026-01-15 10:30:00",
        "state": "sale",
        "amount_total": 545.0,
        "partner_id": [42, "ArcelorMittal"],
    },
]

_SAMPLE_ORDER_LINES: list[dict[str, Any]] = [
    {
        "id": 10,
        "product_id": [55, "Boulon M10x50"],
        "name": "Boulon M10x50",
        "product_uom_qty": 100.0,
        "price_unit": 0.45,
        "price_subtotal": 45.0,
        "order_id": [1, "SO001"],
    },
    {
        "id": 11,
        "product_id": [60, "Tube acier DN50"],
        "name": "Tube acier DN50",
        "product_uom_qty": 10.0,
        "price_unit": 50.0,
        "price_subtotal": 500.0,
        "order_id": [1, "SO001"],
    },
]


def _setup_orders_mock(mock_proxy_cls: MagicMock) -> MagicMock:
    """Setup proxy mocks for order-related tests."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()

    # execute_kw called 3 times: client lookup, orders, order lines
    mock_object.execute_kw.side_effect = [
        [_SAMPLE_CLIENT_RECORD],  # get_client
        _SAMPLE_ORDERS,           # sale.order
        _SAMPLE_ORDER_LINES,      # sale.order.line
    ]

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory
    return mock_object


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_orders_success(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """AC-2: get_client_orders() returns order history with line details."""
    _setup_orders_mock(mock_proxy_cls)

    orders = await adapter.get_client_orders("42")
    assert len(orders) == 2
    assert all(isinstance(o, ClientOrderHistory) for o in orders)
    assert orders[0].product_name == "Boulon M10x50"
    assert orders[1].product_name == "Tube acier DN50"
    assert orders[0].order_id == "SO001"


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_orders_empty(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """get_client_orders() returns empty list when no orders exist."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.side_effect = [
        [_SAMPLE_CLIENT_RECORD],  # get_client
        [],                       # no orders
    ]

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    orders = await adapter.get_client_orders("42")
    assert orders == []


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_client_orders_connection_error(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """get_client_orders() propagates connection errors after retries."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.side_effect = ConnectionRefusedError("Connection refused")

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    with pytest.raises(ConnectionRefusedError):
        await adapter.get_client_orders("42")


# --- get_product_by_id Tests ---


_SAMPLE_PRODUCT_RECORD: dict[str, Any] = {
    "id": 55,
    "default_code": "BOLT-M10",
    "name": "Boulon M10x50",
    "description_sale": "Boulon hexagonal M10x50 grade 8.8",
    "categ_id": [3, "Boulonnerie"],
    "list_price": 0.45,
    "active": True,
    "barcode": False,
    "type": "product",
    "sale_ok": True,
    "uom_id": [1, "Unités"],
    "weight": 0.025,
}


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_product_by_id_success(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """AC-1: get_product_by_id() returns Product DTO."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.return_value = [_SAMPLE_PRODUCT_RECORD]

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    product = await adapter.get_product_by_id(55)
    assert product.odoo_id == 55
    assert product.reference == "BOLT-M10"
    assert product.name == "Boulon M10x50"
    assert product.unit_price == 0.45


@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_get_product_by_id_not_found(
    mock_proxy_cls: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """get_product_by_id() raises ValueError when not found."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.return_value = []

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    with pytest.raises(ValueError, match="Product not found"):
        await adapter.get_product_by_id(999)


# --- Retry Logic Tests ---


@patch("quote_agent.adapters.erp.odoo.asyncio.sleep")
@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_retry_exponential_backoff_timing(
    mock_proxy_cls: MagicMock,
    mock_sleep: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """Retry uses exponential backoff: 1s, 2s, then raises."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.side_effect = [
        ConnectionRefusedError("fail 1"),
        ConnectionRefusedError("fail 2"),
        ConnectionRefusedError("fail 3"),
    ]

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    with pytest.raises(ConnectionRefusedError):
        await adapter.get_client("42")

    # Verify backoff delays: 1s, 2s (then raises on 3rd attempt)
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0][0][0] == 1.0
    assert mock_sleep.call_args_list[1][0][0] == 2.0


@patch("quote_agent.adapters.erp.odoo.asyncio.sleep")
@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_retry_max_retries_exhausted(
    mock_proxy_cls: MagicMock,
    mock_sleep: MagicMock,
    adapter: OdooAdapter,
) -> None:
    """After 3 failed retries, the original exception is raised."""
    mock_common = MagicMock()
    mock_common.authenticate.return_value = 2
    mock_object = MagicMock()
    mock_object.execute_kw.side_effect = xmlrpc.client.Fault(1, "XML-RPC error")

    def proxy_factory(url: str) -> MagicMock:
        if "common" in url:
            return mock_common
        return mock_object

    mock_proxy_cls.side_effect = proxy_factory

    with pytest.raises(xmlrpc.client.Fault):
        await adapter.get_product_by_id(1)

    # 3 attempts = 2 retries with sleep
    assert mock_sleep.call_count == 2


# --- Protocol Compliance ---


def test_adapter_conforms_to_updated_protocol(adapter: OdooAdapter) -> None:
    """AC-5: OdooAdapter satisfies updated ERPAdapter Protocol with new methods."""
    assert isinstance(adapter, ERPAdapter)
    assert hasattr(adapter, "get_client")
    assert hasattr(adapter, "get_client_orders")
    assert hasattr(adapter, "get_product_by_id")
