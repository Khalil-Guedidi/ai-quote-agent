"""Unit tests for CatalogService (Story 3.1)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from quote_agent.adapters.erp.models import Product as ProductDTO
from quote_agent.services.catalog_service import CatalogService, _product_hash


class TestProductHash:
    """Tests for the change-detection hash function."""

    def test_same_data_same_hash(self) -> None:
        """AC-3: Identical products produce identical hashes."""
        dto = ProductDTO(
            odoo_id=1, reference="A", name="B", category="C",
            unit_price=1.0, stock_status="in_stock", is_active=True,
        )
        assert _product_hash(dto) == _product_hash(dto)

    def test_different_data_different_hash(self) -> None:
        """AC-3: Changed products produce different hashes."""
        dto1 = ProductDTO(
            odoo_id=1, reference="A", name="B", category="C",
            unit_price=1.0, stock_status="in_stock", is_active=True,
        )
        dto2 = ProductDTO(
            odoo_id=1, reference="A", name="B-updated", category="C",
            unit_price=1.0, stock_status="in_stock", is_active=True,
        )
        assert _product_hash(dto1) != _product_hash(dto2)


class TestCatalogServiceIngestFull:
    """Tests for CatalogService.ingest_full() with mocked adapter and session."""

    def _make_product_dto(self, odoo_id: int, name: str = "Product", **kwargs: Any) -> ProductDTO:
        return ProductDTO(
            odoo_id=odoo_id,
            reference=f"REF-{odoo_id}",
            name=name,
            category="Test",
            unit_price=10.0,
            stock_status="in_stock",
            is_active=True,
            **kwargs,
        )

    def _make_db_product(self, odoo_id: int, name: str = "Product") -> MagicMock:
        """Create a mock that looks like a ProductModel row."""
        mock = MagicMock()
        mock.odoo_id = odoo_id
        mock.reference = f"REF-{odoo_id}"
        mock.name = name
        mock.description = None
        mock.category = "Test"
        mock.unit_price = 10.0
        mock.stock_status = "in_stock"
        mock.is_active = True
        mock.metadata_ = {}
        mock.is_stale = False
        return mock

    @pytest.fixture()
    def mock_adapter(self) -> AsyncMock:
        return AsyncMock()

    @staticmethod
    def _cache_invalidate_result() -> MagicMock:
        """Mock result for the search cache invalidate_all() DELETE call."""
        r = MagicMock()
        r.rowcount = 0
        return r

    @pytest.fixture()
    def mock_session(self) -> AsyncMock:
        session = AsyncMock()
        # Default: execute returns empty scalars for existing products lookup
        result_mock = MagicMock()
        result_mock.scalars.return_value = []
        session.execute.return_value = result_mock
        # rowcount for stale detection
        stale_result = MagicMock()
        stale_result.rowcount = 0
        session.execute.return_value = stale_result
        return session

    async def test_products_inserted_when_new_catalog(
        self, mock_adapter: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """AC-1: New products are inserted into PostgreSQL."""
        products = [self._make_product_dto(1), self._make_product_dto(2)]
        mock_adapter.get_products.side_effect = [products, []]

        # First execute: select returns empty (no existing), second: stale update, third: cache invalidation
        select_result = MagicMock()
        select_result.scalars.return_value = []
        stale_result = MagicMock()
        stale_result.rowcount = 0
        mock_session.execute.side_effect = [select_result, stale_result, self._cache_invalidate_result()]

        service = CatalogService(mock_adapter, mock_session)
        result = await service.ingest_full()

        assert result.inserted == 2
        assert result.updated == 0
        assert result.unchanged == 0
        assert mock_session.add.call_count == 2

    async def test_products_updated_when_changed(
        self, mock_adapter: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """AC-3: Changed products are updated (not duplicated)."""
        # Adapter returns product with updated name
        updated_dto = self._make_product_dto(1, name="Updated Name")
        mock_adapter.get_products.side_effect = [[updated_dto], []]

        # DB has existing product with old name
        existing = self._make_db_product(1, name="Old Name")
        select_result = MagicMock()
        select_result.scalars.return_value = [existing]
        stale_result = MagicMock()
        stale_result.rowcount = 0
        mock_session.execute.side_effect = [select_result, stale_result, self._cache_invalidate_result()]

        service = CatalogService(mock_adapter, mock_session)
        result = await service.ingest_full()

        assert result.updated == 1
        assert result.inserted == 0
        assert existing.name == "Updated Name"

    async def test_products_unchanged_when_identical(
        self, mock_adapter: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """AC-3: Identical products are skipped (unchanged)."""
        dto = self._make_product_dto(1)
        mock_adapter.get_products.side_effect = [[dto], []]

        existing = self._make_db_product(1)
        select_result = MagicMock()
        select_result.scalars.return_value = [existing]
        stale_result = MagicMock()
        stale_result.rowcount = 0
        mock_session.execute.side_effect = [select_result, stale_result, self._cache_invalidate_result()]

        service = CatalogService(mock_adapter, mock_session)
        result = await service.ingest_full()

        assert result.unchanged == 1
        assert result.inserted == 0
        assert result.updated == 0

    async def test_pagination_terminates_when_last_batch_smaller(
        self, mock_adapter: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """AC-2: Pagination stops when batch size < limit."""
        # Return 2 products (less than _BATCH_SIZE=500), so pagination stops
        products = [self._make_product_dto(i) for i in range(2)]
        mock_adapter.get_products.side_effect = [products]

        select_result = MagicMock()
        select_result.scalars.return_value = []
        stale_result = MagicMock()
        stale_result.rowcount = 0
        mock_session.execute.side_effect = [select_result, stale_result, self._cache_invalidate_result()]

        service = CatalogService(mock_adapter, mock_session)
        result = await service.ingest_full()

        # get_products called once (batch < 500, so loop breaks)
        assert mock_adapter.get_products.call_count == 1
        assert result.inserted == 2

    async def test_stale_products_flagged(
        self, mock_adapter: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """AC-3: Products not in fetched set are flagged stale."""
        products = [self._make_product_dto(1)]
        mock_adapter.get_products.side_effect = [products, []]

        select_result = MagicMock()
        select_result.scalars.return_value = []
        stale_result = MagicMock()
        stale_result.rowcount = 3  # 3 products flagged stale
        mock_session.execute.side_effect = [select_result, stale_result, self._cache_invalidate_result()]

        service = CatalogService(mock_adapter, mock_session)
        result = await service.ingest_full()

        assert result.stale == 3

    async def test_ingestion_result_has_duration(
        self, mock_adapter: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """AC-2: IngestionResult includes duration_seconds."""
        mock_adapter.get_products.side_effect = [[]]

        stale_result = MagicMock()
        stale_result.rowcount = 0
        mock_session.execute.return_value = stale_result

        service = CatalogService(mock_adapter, mock_session)
        result = await service.ingest_full()

        assert result.duration_seconds >= 0.0

    async def test_structured_logging_on_batch(
        self, mock_adapter: AsyncMock, mock_session: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC-2: Structured JSON logging for batch progress."""
        products = [self._make_product_dto(1)]
        mock_adapter.get_products.side_effect = [products, []]

        select_result = MagicMock()
        select_result.scalars.return_value = []
        stale_result = MagicMock()
        stale_result.rowcount = 0
        mock_session.execute.side_effect = [select_result, stale_result, self._cache_invalidate_result()]

        import logging
        with caplog.at_level(logging.INFO, logger="quote_agent.services.catalog_service"):
            service = CatalogService(mock_adapter, mock_session)
            await service.ingest_full()

        assert any("Catalog batch ingested" in r.message for r in caplog.records)
        assert any("Catalog ingestion complete" in r.message for r in caplog.records)
