"""Tests for ERP adapter — draft quote creation, DTOs, retry logic, protocol compliance."""

from __future__ import annotations

import xmlrpc.client
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.adapters.erp.models import (
    Client,
    QuoteDraftResult,
    UniversalQuote,
    UniversalQuoteLine,
)
from quote_agent.adapters.erp.odoo import OdooAdapter
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


# --- DTO Tests (AC-4) ---


class TestUniversalQuoteLineDTO:
    """AC-4: UniversalQuoteLine DTO construction and validation."""

    def test_required_fields(self) -> None:
        """AC-4: UniversalQuoteLine requires product_id, product_name, quantity, unit_price."""
        line = UniversalQuoteLine(
            product_id=55,
            product_name="Boulon M10x50",
            quantity=100.0,
            unit_price=0.45,
        )
        assert line.product_id == 55
        assert line.product_name == "Boulon M10x50"
        assert line.quantity == 100.0
        assert line.unit_price == 0.45
        assert line.product_ref is None
        assert line.description is None

    def test_all_fields(self) -> None:
        """AC-4: UniversalQuoteLine accepts all optional fields."""
        line = UniversalQuoteLine(
            product_id=55,
            product_ref="BOLT-M10",
            product_name="Boulon M10x50",
            quantity=100.0,
            unit_price=0.45,
            description="Boulon hexagonal grade 8.8",
        )
        assert line.product_ref == "BOLT-M10"
        assert line.description == "Boulon hexagonal grade 8.8"


class TestUniversalQuoteDTO:
    """AC-4: UniversalQuote DTO construction and validation."""

    def test_required_fields(self) -> None:
        """AC-4: UniversalQuote requires client_id, client_name, lines."""
        quote = UniversalQuote(
            client_id="42",
            client_name="ArcelorMittal",
            lines=[
                UniversalQuoteLine(
                    product_id=55,
                    product_name="Boulon M10x50",
                    quantity=100.0,
                    unit_price=0.45,
                ),
            ],
        )
        assert quote.client_id == "42"
        assert quote.client_name == "ArcelorMittal"
        assert len(quote.lines) == 1
        assert quote.delivery_date is None
        assert quote.notes is None

    def test_all_fields(self) -> None:
        """AC-4: UniversalQuote accepts delivery_date and notes."""
        quote = UniversalQuote(
            client_id="42",
            client_name="ArcelorMittal",
            lines=[
                UniversalQuoteLine(
                    product_id=55,
                    product_name="Boulon M10x50",
                    quantity=100.0,
                    unit_price=0.45,
                ),
            ],
            delivery_date="2026-04-01",
            notes="Urgent delivery requested",
        )
        assert quote.delivery_date == "2026-04-01"
        assert quote.notes == "Urgent delivery requested"

    def test_multiple_lines(self) -> None:
        """AC-4: UniversalQuote supports multiple lines."""
        quote = UniversalQuote(
            client_id="42",
            client_name="Test",
            lines=[
                UniversalQuoteLine(product_id=1, product_name="A", quantity=10, unit_price=1.0),
                UniversalQuoteLine(product_id=2, product_name="B", quantity=20, unit_price=2.0),
            ],
        )
        assert len(quote.lines) == 2


class TestQuoteDraftResultDTO:
    """AC-4: QuoteDraftResult DTO construction and validation."""

    def test_required_fields(self) -> None:
        """AC-4: QuoteDraftResult requires all fields."""
        result = QuoteDraftResult(
            odoo_id=123,
            order_reference="SO042",
            state="draft",
            line_count=2,
        )
        assert result.odoo_id == 123
        assert result.order_reference == "SO042"
        assert result.state == "draft"
        assert result.line_count == 2


# --- _build_odoo_order_values Tests (AC-2) ---


class TestBuildOdooOrderValues:
    """AC-2: _build_odoo_order_values helper builds correct Odoo create values."""

    def test_basic_order_values(self) -> None:
        """AC-2: Builds correct partner_id and order_line tuples."""
        quote = UniversalQuote(
            client_id="42",
            client_name="Test",
            lines=[
                UniversalQuoteLine(
                    product_id=55,
                    product_name="Boulon M10x50",
                    quantity=100.0,
                    unit_price=0.45,
                ),
            ],
        )
        values = OdooAdapter._build_odoo_order_values(quote, partner_odoo_id=42)

        assert values["partner_id"] == 42
        assert len(values["order_line"]) == 1

        line_tuple = values["order_line"][0]
        assert line_tuple[0] == 0
        assert line_tuple[1] == 0
        assert line_tuple[2]["product_id"] == 55
        assert line_tuple[2]["product_uom_qty"] == 100.0
        assert line_tuple[2]["price_unit"] == 0.45
        assert "name" not in line_tuple[2]  # No description provided

    def test_order_values_with_description(self) -> None:
        """AC-2: Includes name field when description is provided."""
        quote = UniversalQuote(
            client_id="42",
            client_name="Test",
            lines=[
                UniversalQuoteLine(
                    product_id=55,
                    product_name="Boulon M10x50",
                    quantity=100.0,
                    unit_price=0.45,
                    description="Boulon hexagonal grade 8.8",
                ),
            ],
        )
        values = OdooAdapter._build_odoo_order_values(quote, partner_odoo_id=42)

        assert values["order_line"][0][2]["name"] == "Boulon hexagonal grade 8.8"

    def test_order_values_with_delivery_date(self) -> None:
        """AC-2: Includes commitment_date when delivery_date is set."""
        quote = UniversalQuote(
            client_id="42",
            client_name="Test",
            lines=[
                UniversalQuoteLine(product_id=55, product_name="A", quantity=10, unit_price=1.0),
            ],
            delivery_date="2026-04-01",
        )
        values = OdooAdapter._build_odoo_order_values(quote, partner_odoo_id=42)

        assert values["commitment_date"] == "2026-04-01"

    def test_order_values_without_delivery_date(self) -> None:
        """AC-2: Omits commitment_date when delivery_date is None."""
        quote = UniversalQuote(
            client_id="42",
            client_name="Test",
            lines=[
                UniversalQuoteLine(product_id=55, product_name="A", quantity=10, unit_price=1.0),
            ],
        )
        values = OdooAdapter._build_odoo_order_values(quote, partner_odoo_id=42)

        assert "commitment_date" not in values

    def test_multiple_lines(self) -> None:
        """AC-2: Builds multiple order_line tuples."""
        quote = UniversalQuote(
            client_id="42",
            client_name="Test",
            lines=[
                UniversalQuoteLine(product_id=1, product_name="A", quantity=10, unit_price=1.0),
                UniversalQuoteLine(product_id=2, product_name="B", quantity=20, unit_price=2.0),
            ],
        )
        values = OdooAdapter._build_odoo_order_values(quote, partner_odoo_id=42)

        assert len(values["order_line"]) == 2
        assert values["order_line"][0][2]["product_id"] == 1
        assert values["order_line"][1][2]["product_id"] == 2


# --- create_draft_quote Tests (AC-1, AC-3) ---


def _sample_quote() -> UniversalQuote:
    """Build a sample UniversalQuote for tests."""
    return UniversalQuote(
        client_id="42",
        client_name="ArcelorMittal",
        lines=[
            UniversalQuoteLine(
                product_id=55,
                product_name="Boulon M10x50",
                quantity=100.0,
                unit_price=0.45,
            ),
        ],
    )


def _sample_client() -> Client:
    """Build a sample Client."""
    return Client(odoo_id=42, name="ArcelorMittal", ref="AM001")


class TestCreateDraftQuote:
    """AC-1, AC-3: create_draft_quote with mocked XML-RPC calls."""

    async def test_success(self, adapter: OdooAdapter) -> None:
        """AC-1: Creates a draft sale.order and returns QuoteDraftResult."""
        mock_proxy = MagicMock()
        # Mock: get_client_impl returns client
        # Mock: execute_kw for create returns order ID
        # Mock: execute_kw for read returns order data
        mock_proxy.execute_kw.side_effect = [
            # get_client_impl search_read
            [{"id": 42, "name": "ArcelorMittal", "ref": "AM001", "email": False,
              "phone": False, "street": False, "city": False, "zip": False,
              "country_id": False, "vat": False, "active": True, "customer_rank": 1}],
            # create sale.order
            123,
            # read back order
            [{"name": "SO042", "state": "draft", "order_line": [1]}],
        ]
        mock_proxy.authenticate.return_value = 1

        with patch("xmlrpc.client.ServerProxy", return_value=mock_proxy):
            result = await adapter.create_draft_quote(_sample_quote())

        assert result.odoo_id == 123
        assert result.order_reference == "SO042"
        assert result.state == "draft"
        assert result.line_count == 1

    async def test_client_not_found(self, adapter: OdooAdapter) -> None:
        """AC-1: Raises ValueError when client is not found."""
        mock_proxy = MagicMock()
        mock_proxy.execute_kw.return_value = []  # No client found
        mock_proxy.authenticate.return_value = 1

        with (
            patch("xmlrpc.client.ServerProxy", return_value=mock_proxy),
            pytest.raises(ValueError, match="Client not found"),
        ):
            await adapter.create_draft_quote(_sample_quote())

    async def test_connection_error_raises(self, adapter: OdooAdapter) -> None:
        """AC-3: ConnectionRefusedError propagates after retries."""
        mock_proxy = MagicMock()
        mock_proxy.authenticate.return_value = 1
        mock_proxy.execute_kw.side_effect = ConnectionRefusedError("Connection refused")

        with (
            patch("xmlrpc.client.ServerProxy", return_value=mock_proxy),
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(ConnectionRefusedError),
        ):
            await adapter.create_draft_quote(_sample_quote())

    async def test_timeout_raises(self, adapter: OdooAdapter) -> None:
        """AC-3: TimeoutError when ERP is too slow."""
        mock_proxy = MagicMock()
        mock_proxy.authenticate.return_value = 1
        # Client resolves fine, but create times out
        mock_proxy.execute_kw.side_effect = [
            # get_client_impl
            [{"id": 42, "name": "ArcelorMittal", "ref": "AM001", "email": False,
              "phone": False, "street": False, "city": False, "zip": False,
              "country_id": False, "vat": False, "active": True, "customer_rank": 1}],
            # create call times out
            TimeoutError("Timed out"),
        ]

        with (
            patch("xmlrpc.client.ServerProxy", return_value=mock_proxy),
            pytest.raises(TimeoutError),
        ):
            await adapter.create_draft_quote(_sample_quote())


# --- Retry Logic Tests (AC-3) ---


class TestCreateDraftRetry:
    """AC-3: Retry with exponential backoff on transient failures."""

    async def test_retry_on_transient_failure(self, adapter: OdooAdapter) -> None:
        """AC-3: Retries on xmlrpc.client.Error, succeeds on 2nd attempt."""
        mock_proxy = MagicMock()
        mock_proxy.authenticate.return_value = 1

        call_count = 0

        def side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt: transient failure
                raise xmlrpc.client.Error("Temporary failure")
            if call_count == 2:
                # Second attempt: client found
                return [{"id": 42, "name": "ArcelorMittal", "ref": "AM001", "email": False,
                         "phone": False, "street": False, "city": False, "zip": False,
                         "country_id": False, "vat": False, "active": True, "customer_rank": 1}]
            if call_count == 3:
                # create
                return 123
            # read back
            return [{"name": "SO042", "state": "draft", "order_line": [1]}]

        mock_proxy.execute_kw.side_effect = side_effect

        with (
            patch("xmlrpc.client.ServerProxy", return_value=mock_proxy),
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            result = await adapter.create_draft_quote(_sample_quote())

        assert result.odoo_id == 123
        mock_sleep.assert_awaited_once()

    async def test_retries_exhausted(self, adapter: OdooAdapter) -> None:
        """AC-3: Returns structured error after all retries exhausted."""
        mock_proxy = MagicMock()
        mock_proxy.authenticate.return_value = 1
        mock_proxy.execute_kw.side_effect = OSError("Network unreachable")

        with (
            patch("xmlrpc.client.ServerProxy", return_value=mock_proxy),
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(OSError, match="Network unreachable"),
        ):
            await adapter.create_draft_quote(_sample_quote())


# --- Protocol Compliance (AC-5) ---


class TestProtocolCompliance:
    """AC-5: OdooAdapter satisfies ERPAdapter Protocol with create_draft_quote."""

    def test_odoo_adapter_is_erp_adapter(self, adapter: OdooAdapter) -> None:
        """AC-5: OdooAdapter is recognized as ERPAdapter Protocol implementation."""
        assert isinstance(adapter, ERPAdapter)

    def test_create_draft_quote_in_protocol(self) -> None:
        """AC-5: create_draft_quote is defined in ERPAdapter Protocol."""
        assert hasattr(ERPAdapter, "create_draft_quote")
