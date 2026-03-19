"""Unit tests for EmbeddingService — mock adapter + mock session."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from quote_agent.models.product import Product
from quote_agent.services.embedding_service import EmbeddingService, _build_product_text


class TestBuildProductText:
    """Test _build_product_text() text building."""

    def test_full_product_text(self) -> None:
        """AC-1: Full product produces expected text format."""
        product = MagicMock(spec=Product)
        product.name = "TUBE ROND SS 304L 25x1.5 LG6000"
        product.reference = "TUB-304L-025"
        product.category = "Tubes & Tuyaux"
        product.description = "Tube rond acier inoxydable 304L"

        text = _build_product_text(product)
        expected = (
            "TUBE ROND SS 304L 25x1.5 LG6000 | Ref: TUB-304L-025 | Tubes & Tuyaux | Tube rond acier inoxydable 304L"
        )
        assert text == expected

    def test_product_without_description(self) -> None:
        """AC-1: Product without description omits that part."""
        product = MagicMock(spec=Product)
        product.name = "BOULON M8"
        product.reference = "BLN-M8"
        product.category = "Quincaillerie"
        product.description = None

        text = _build_product_text(product)
        assert text == "BOULON M8 | Ref: BLN-M8 | Quincaillerie"

    def test_product_without_reference(self) -> None:
        """AC-1: Product with empty reference omits Ref part."""
        product = MagicMock(spec=Product)
        product.name = "GENERIC ITEM"
        product.reference = ""
        product.category = "Uncategorized"
        product.description = None

        text = _build_product_text(product)
        assert text == "GENERIC ITEM | Uncategorized"

    def test_product_with_special_characters(self) -> None:
        """AC-1: Special characters in product data are preserved."""
        product = MagicMock(spec=Product)
        product.name = "JOINT Ø50 / DN40"
        product.reference = "JNT-50/40"
        product.category = "Joints & Étanchéité"
        product.description = "Joint à lèvre 50mm"

        text = _build_product_text(product)
        assert "JOINT Ø50 / DN40" in text
        assert "Joints & Étanchéité" in text


class TestEmbeddingServiceEmbedAll:
    """Test EmbeddingService.embed_all() with mocked dependencies."""

    def _make_product(
        self,
        name: str = "TEST PRODUCT",
        reference: str = "TST-001",
        category: str = "Test",
        description: str | None = "Test product",
        is_stale: bool = False,
        has_vector: bool = False,
    ) -> MagicMock:
        product = MagicMock(spec=Product)
        product.id = uuid.uuid4()
        product.name = name
        product.reference = reference
        product.category = category
        product.description = description
        product.is_stale = is_stale
        product.vector = [0.1] * 1024 if has_vector else None
        product.created_at = MagicMock()
        return product

    async def test_embed_all_basic(self) -> None:
        """AC-1: embed_all() generates embeddings for products without vectors."""
        products = [self._make_product(name=f"PRODUCT {i}") for i in range(3)]

        mock_adapter = AsyncMock()
        mock_adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024 for _ in range(3)])

        mock_session = AsyncMock()
        # First call: stale count query returns 0
        # Second call: products needing embedding
        # Third call: no more products
        stale_result = MagicMock()
        stale_result.scalar_one.return_value = 0

        products_result = MagicMock()
        products_result.scalars.return_value.all.return_value = products

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[stale_result, products_result, empty_result])

        service = EmbeddingService(mock_adapter, mock_session)
        result = await service.embed_all()

        assert result.embedded == 3
        assert result.skipped_stale == 0
        assert result.errors == 0
        mock_adapter.embed_texts.assert_called_once()

    async def test_embed_all_skips_stale_products(self) -> None:
        """AC-1: Stale products are skipped and counted."""
        mock_adapter = AsyncMock()
        mock_session = AsyncMock()

        # Stale count query returns 2
        stale_result = MagicMock()
        stale_result.scalar_one.return_value = 2

        # No non-stale products to embed
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[stale_result, empty_result])

        service = EmbeddingService(mock_adapter, mock_session)
        result = await service.embed_all()

        assert result.skipped_stale == 2
        assert result.embedded == 0
        mock_adapter.embed_texts.assert_not_called()

    async def test_embed_all_handles_adapter_error(self) -> None:
        """AC-2: Adapter errors are counted and logged."""
        products = [self._make_product(name=f"PRODUCT {i}") for i in range(3)]

        mock_adapter = AsyncMock()
        mock_adapter.embed_texts = AsyncMock(side_effect=RuntimeError("GPU OOM"))

        mock_session = AsyncMock()

        stale_result = MagicMock()
        stale_result.scalar_one.return_value = 0

        products_result = MagicMock()
        products_result.scalars.return_value.all.return_value = products

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[stale_result, products_result, empty_result])

        service = EmbeddingService(mock_adapter, mock_session)
        result = await service.embed_all()

        assert result.errors == 3
        assert result.embedded == 0


class TestEmbeddingServiceEmbedBatch:
    """Test EmbeddingService.embed_batch() with mocked dependencies."""

    def _make_product(
        self,
        name: str = "TEST PRODUCT",
        reference: str = "TST-001",
        category: str = "Test",
        description: str | None = "Test product",
    ) -> MagicMock:
        product = MagicMock(spec=Product)
        product.id = uuid.uuid4()
        product.name = name
        product.reference = reference
        product.category = category
        product.description = description
        product.is_stale = False
        product.vector = None
        return product

    async def test_embed_batch_by_ids(self) -> None:
        """AC-1: embed_batch() embeds specific products by ID."""
        products = [self._make_product(name=f"PRODUCT {i}") for i in range(3)]
        product_ids = [p.id for p in products]

        mock_adapter = AsyncMock()
        mock_adapter.embed_texts = AsyncMock(return_value=[[0.1] * 1024 for _ in range(3)])

        mock_session = AsyncMock()
        products_result = MagicMock()
        products_result.scalars.return_value.all.return_value = products
        mock_session.execute = AsyncMock(return_value=products_result)

        service = EmbeddingService(mock_adapter, mock_session)
        result = await service.embed_batch(product_ids)

        assert result.embedded == 3
        assert result.errors == 0
        mock_adapter.embed_texts.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_embed_batch_empty_ids(self) -> None:
        """AC-1: embed_batch() with no matching products returns zero counts."""
        mock_adapter = AsyncMock()
        mock_session = AsyncMock()

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=empty_result)

        service = EmbeddingService(mock_adapter, mock_session)
        result = await service.embed_batch([uuid.uuid4()])

        assert result.embedded == 0
        assert result.errors == 0
        mock_adapter.embed_texts.assert_not_called()

    async def test_embed_batch_adapter_error(self) -> None:
        """AC-2: embed_batch() counts errors when adapter fails."""
        products = [self._make_product()]
        product_ids = [products[0].id]

        mock_adapter = AsyncMock()
        mock_adapter.embed_texts = AsyncMock(side_effect=RuntimeError("GPU OOM"))

        mock_session = AsyncMock()
        products_result = MagicMock()
        products_result.scalars.return_value.all.return_value = products
        mock_session.execute = AsyncMock(return_value=products_result)

        service = EmbeddingService(mock_adapter, mock_session)
        result = await service.embed_batch(product_ids)

        assert result.errors == 1
        assert result.embedded == 0


class TestEmbeddingServiceResetEmbeddings:
    """Test EmbeddingService.reset_embeddings()."""

    async def test_reset_embeddings(self) -> None:
        """AC-4: reset_embeddings sets all vectors to NULL."""
        mock_adapter = AsyncMock()
        mock_session = AsyncMock()

        cursor_result = MagicMock()
        cursor_result.rowcount = 50
        mock_session.execute = AsyncMock(return_value=cursor_result)

        service = EmbeddingService(mock_adapter, mock_session)
        count = await service.reset_embeddings()

        assert count == 50
        mock_session.commit.assert_called_once()
