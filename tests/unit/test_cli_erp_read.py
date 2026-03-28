"""Unit tests for the CLI erp-read command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from quote_agent.adapters.erp.models import Client, ClientOrderHistory, Product
from quote_agent.cli.main import app

runner = CliRunner()

_PATCH_TARGET = "quote_agent.adapters.erp.get_erp_adapter"


def _make_client() -> Client:
    """Build a sample Client."""
    return Client(
        odoo_id=42,
        name="ArcelorMittal",
        ref="AM001",
        email="contact@arcelor.com",
        phone="+33 1 23 45 67 89",
        address="1 Boulevard Oxygène, 93200 Saint-Denis, France",
        vat="FR12345678901",
        is_active=True,
        metadata={"customer_rank": 1},
    )


def _make_product() -> Product:
    """Build a sample Product."""
    return Product(
        odoo_id=55,
        reference="BOLT-M10",
        name="Boulon M10x50",
        description="Boulon hexagonal M10x50 grade 8.8",
        category="Boulonnerie",
        unit_price=0.45,
        stock_status="in_stock",
        is_active=True,
    )


def _make_orders() -> list[ClientOrderHistory]:
    """Build sample order history."""
    return [
        ClientOrderHistory(
            order_id="SO001",
            date="2026-01-15 10:30:00",
            product_name="Boulon M10x50",
            quantity=100.0,
            unit_price=0.45,
            total=45.0,
            state="sale",
        ),
        ClientOrderHistory(
            order_id="SO001",
            date="2026-01-15 10:30:00",
            product_name="Tube acier DN50",
            quantity=10.0,
            unit_price=50.0,
            total=500.0,
            state="sale",
        ),
    ]


def _mock_adapter_with(method: str, return_value: object = None, side_effect: object = None) -> MagicMock:
    """Create a mock adapter with a specific method configured."""
    mock_adapter = MagicMock()
    mock_method = AsyncMock(return_value=return_value, side_effect=side_effect)
    setattr(mock_adapter, method, mock_method)
    return mock_adapter


class TestErpReadClient:
    """AC-6: CLI erp-read --client mode."""

    def test_formatted_output(self) -> None:
        """AC-6: Displays client data in formatted output."""
        mock_adapter = _mock_adapter_with("get_client", return_value=_make_client())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--client", "AM001"])

        assert result.exit_code == 0
        assert "ArcelorMittal" in result.output
        assert "AM001" in result.output

    def test_json_output(self) -> None:
        """AC-6: Displays client data as JSON."""
        mock_adapter = _mock_adapter_with("get_client", return_value=_make_client())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--client", "42", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["odoo_id"] == 42
        assert data["name"] == "ArcelorMittal"


class TestErpReadProduct:
    """AC-6: CLI erp-read --product mode."""

    def test_formatted_output(self) -> None:
        """AC-6: Displays product data in formatted output."""
        mock_adapter = _mock_adapter_with("get_product_by_id", return_value=_make_product())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--product", "55"])

        assert result.exit_code == 0
        assert "Boulon M10x50" in result.output
        assert "BOLT-M10" in result.output

    def test_json_output(self) -> None:
        """AC-6: Displays product data as JSON."""
        mock_adapter = _mock_adapter_with("get_product_by_id", return_value=_make_product())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--product", "55", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["odoo_id"] == 55
        assert data["reference"] == "BOLT-M10"


class TestErpReadOrders:
    """AC-6: CLI erp-read --orders mode."""

    def test_formatted_output(self) -> None:
        """AC-6: Displays order history in formatted output."""
        mock_adapter = _mock_adapter_with("get_client_orders", return_value=_make_orders())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--orders", "42"])

        assert result.exit_code == 0
        assert "SO001" in result.output
        assert "Boulon M10x50" in result.output
        assert "2 lines" in result.output

    def test_json_output(self) -> None:
        """AC-6: Displays orders as JSON."""
        mock_adapter = _mock_adapter_with("get_client_orders", return_value=_make_orders())
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--orders", "42", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["order_id"] == "SO001"

    def test_empty_orders(self) -> None:
        """AC-6: Handles empty order history gracefully."""
        mock_adapter = _mock_adapter_with("get_client_orders", return_value=[])
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--orders", "42"])

        assert result.exit_code == 0
        assert "No orders found" in result.output


class TestErpReadErrorHandling:
    """AC-6: Error handling."""

    def test_no_flags_exits_with_error(self) -> None:
        """AC-6: No flags specified exits with error."""
        result = runner.invoke(app, ["erp-read"])
        assert result.exit_code == 1
        assert "Specify" in result.output

    def test_not_found_exits_with_code_1(self) -> None:
        """AC-6: Not found exits with code 1."""
        mock_adapter = _mock_adapter_with(
            "get_client",
            side_effect=ValueError("Client not found: 999"),
        )
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--client", "999"])

        assert result.exit_code == 1
        assert "Not found" in result.output

    def test_connection_error_exits_with_code_1(self) -> None:
        """AC-6: Connection error exits with code 1."""
        mock_adapter = _mock_adapter_with(
            "get_client",
            side_effect=ConnectionRefusedError("Connection refused"),
        )
        with patch(_PATCH_TARGET, return_value=mock_adapter):
            result = runner.invoke(app, ["erp-read", "--client", "42"])

        assert result.exit_code == 1
        assert "Error" in result.output
