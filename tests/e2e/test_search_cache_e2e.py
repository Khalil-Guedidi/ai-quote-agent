"""E2E tests for search result cache — real PostgreSQL + real embedding model."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from sqlalchemy import delete

from quote_agent.adapters.embedding import get_embedding_adapter
from quote_agent.models.product import Product
from quote_agent.models.search_cache import SearchCache
from quote_agent.search import SearchEngine, SearchRequest
from quote_agent.search.cache import invalidate_all
from quote_agent.services.embedding_service import EmbeddingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Skip decorator
# ---------------------------------------------------------------------------


def _has_real_database() -> bool:
    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


requires_e2e_cache = pytest.mark.skipif(
    not _has_real_database(),
    reason="E2E cache tests require real DATABASE__URL",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sample_products(count: int = 20) -> list[dict[str, object]]:
    """Load products from the 50K sample fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "catalog_50k_sample.jsonl"
    products: list[dict[str, object]] = []
    with fixture_path.open() as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            products.append(json.loads(line))
    return products


def _insert_product_from_dict(data: dict[str, object]) -> Product:
    """Create a Product model from fixture dict data."""
    return Product(
        id=uuid.uuid4(),
        reference=str(data.get("reference", "")),
        name=str(data["name"]),
        description=data.get("description"),  # type: ignore[arg-type]
        category=str(data.get("category", "Uncategorized")),
        unit_price=float(data.get("unit_price", 0.0)),
        stock_status=str(data.get("stock_status", "in_stock")),
        is_active=bool(data.get("is_active", True)),
        metadata_=data.get("metadata"),  # type: ignore[arg-type]
        is_stale=False,
    )


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@requires_e2e_cache
class TestSearchCacheE2E:
    """AC-7: E2E tests for search cache with real PostgreSQL."""

    async def test_second_search_returns_from_cache_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-7: Second identical query returns from_cache=True with duration < 1s."""
        session = e2e_db_session

        # Insert and embed test products
        sample_data = _load_sample_products(20)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            engine = SearchEngine(session, adapter)
            request = SearchRequest(query="tubes inox 304L")

            # First search — cache miss
            result1 = await engine.search_hybrid(request)
            assert result1.from_cache is False

            # Second search — cache hit
            result2 = await engine.search_hybrid(request)
            assert result2.from_cache is True
            assert result2.duration_seconds < 1.0

        finally:
            await session.execute(delete(SearchCache))
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_invalidate_all_clears_cache_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-7: After invalidate_all(), next query is a cache miss."""
        session = e2e_db_session

        sample_data = _load_sample_products(20)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            engine = SearchEngine(session, adapter)
            request = SearchRequest(query="tubes inox 304L")

            # Populate cache
            await engine.search_hybrid(request)
            result_cached = await engine.search_hybrid(request)
            assert result_cached.from_cache is True

            # Invalidate
            count = await invalidate_all(session)
            assert count >= 1

            # After invalidation — cache miss
            result_after = await engine.search_hybrid(request)
            assert result_after.from_cache is False

        finally:
            await session.execute(delete(SearchCache))
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_cache_disabled_no_interaction_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-7: With enabled=False, from_cache is always False."""
        session = e2e_db_session

        sample_data = _load_sample_products(20)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            # Create engine with cache disabled
            with patch("quote_agent.search.engine.get_settings") as mock_settings:
                from quote_agent.config import get_settings

                real_settings = get_settings()
                mock_s = real_settings.model_copy(
                    update={"search_cache": real_settings.search_cache.model_copy(update={"enabled": False})}
                )
                mock_settings.return_value = mock_s
                engine = SearchEngine(session, adapter)

            request = SearchRequest(query="tubes inox 304L")

            result1 = await engine.search_hybrid(request)
            assert result1.from_cache is False

            result2 = await engine.search_hybrid(request)
            assert result2.from_cache is False

        finally:
            await session.execute(delete(SearchCache))
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()
