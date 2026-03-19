"""Unit tests for Odoo field mapping in get_products (Story 3.1)."""

from __future__ import annotations

from typing import Any

from quote_agent.adapters.erp.odoo import _map_odoo_product, _odoo_str


class TestOdooStr:
    """Tests for the _odoo_str helper."""

    def test_returns_string_when_string(self) -> None:
        """AC-1: String values pass through."""
        assert _odoo_str("hello") == "hello"

    def test_returns_none_when_false(self) -> None:
        """AC-1: Odoo False → None."""
        assert _odoo_str(False) is None

    def test_returns_none_when_none(self) -> None:
        """AC-1: Python None → None."""
        assert _odoo_str(None) is None

    def test_returns_none_when_integer(self) -> None:
        """AC-1: Non-string types → None."""
        assert _odoo_str(42) is None


class TestMapOdooProduct:
    """Tests for Odoo record → Product DTO mapping."""

    def _make_odoo_record(self, **overrides: Any) -> dict[str, Any]:
        """Build a minimal Odoo product.product record."""
        record: dict[str, Any] = {
            "id": 42,
            "default_code": "TB-001",
            "name": "TUBE ACIER 50x2.0",
            "description_sale": "Tube acier rond",
            "categ_id": [5, "Tubes & Tuyaux"],
            "list_price": 12.50,
            "active": True,
            "barcode": "3760000000001",
            "type": "product",
            "sale_ok": True,
            "uom_id": [1, "Unit(s)"],
            "weight": 2.5,
        }
        record.update(overrides)
        return record

    def test_basic_field_mapping(self) -> None:
        """AC-1: Core fields mapped correctly from Odoo shape."""
        record = self._make_odoo_record()
        product = _map_odoo_product(record)

        assert product.odoo_id == 42
        assert product.reference == "TB-001"
        assert product.name == "TUBE ACIER 50x2.0"
        assert product.description == "Tube acier rond"
        assert product.category == "Tubes & Tuyaux"
        assert product.unit_price == 12.50
        assert product.is_active is True
        assert product.stock_status == "in_stock"

    def test_categ_id_tuple_extraction(self) -> None:
        """AC-1: categ_id [int, str] → extract name."""
        record = self._make_odoo_record(categ_id=[10, "Boulonnerie"])
        product = _map_odoo_product(record)
        assert product.category == "Boulonnerie"

    def test_categ_id_false_fallback(self) -> None:
        """AC-1: categ_id False → 'Uncategorized'."""
        record = self._make_odoo_record(categ_id=False)
        product = _map_odoo_product(record)
        assert product.category == "Uncategorized"

    def test_default_code_false_to_empty_string(self) -> None:
        """AC-1: Odoo False for default_code → empty string."""
        record = self._make_odoo_record(default_code=False)
        product = _map_odoo_product(record)
        assert product.reference == ""

    def test_description_sale_false_to_none(self) -> None:
        """AC-1: Odoo False for description_sale → None."""
        record = self._make_odoo_record(description_sale=False)
        product = _map_odoo_product(record)
        assert product.description is None

    def test_metadata_assembly(self) -> None:
        """AC-1: Optional fields assembled into metadata dict."""
        record = self._make_odoo_record()
        product = _map_odoo_product(record)

        assert product.metadata["barcode"] == "3760000000001"
        assert product.metadata["type"] == "product"
        assert product.metadata["sale_ok"] is True
        assert product.metadata["uom"] == "Unit(s)"
        assert product.metadata["weight_kg"] == 2.5

    def test_metadata_missing_optional_fields(self) -> None:
        """AC-1: Missing optional fields excluded from metadata."""
        record = self._make_odoo_record(barcode=False, weight=0.0, uom_id=False, type=False, sale_ok=False)
        product = _map_odoo_product(record)

        assert "barcode" not in product.metadata
        assert "weight_kg" not in product.metadata
        assert "uom" not in product.metadata
        assert "type" not in product.metadata

    def test_inactive_product(self) -> None:
        """AC-1: active=False mapped correctly."""
        record = self._make_odoo_record(active=False)
        product = _map_odoo_product(record)
        assert product.is_active is False

    def test_stock_status_always_in_stock(self) -> None:
        """AC-1: stock_status defaults to in_stock (no stock module)."""
        record = self._make_odoo_record()
        product = _map_odoo_product(record)
        assert product.stock_status == "in_stock"
