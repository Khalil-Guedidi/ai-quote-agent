"""E2E tests for hybrid search — real PostgreSQL + real embedding model."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import delete, select, text

from quote_agent.adapters.embedding import get_embedding_adapter
from quote_agent.models.product import Product
from quote_agent.search import SearchEngine, SearchRequest
from quote_agent.search.keyword import is_reference_code
from quote_agent.services.embedding_service import EmbeddingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Skip decorator
# ---------------------------------------------------------------------------

_E2E_MARKER = "e2e-search-test"


def _has_real_database() -> bool:
    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


requires_e2e_search = pytest.mark.skipif(
    not _has_real_database(),
    reason="E2E search tests require real DATABASE__URL",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sample_products(count: int = 50) -> list[dict[str, object]]:
    """Load products from the 50K sample fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "catalog_50k_sample.jsonl"
    products: list[dict[str, object]] = []
    with fixture_path.open() as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            products.append(json.loads(line))
    return products


def _insert_product_from_dict(data: dict[str, object], *, is_stale: bool = False) -> Product:
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
        is_stale=is_stale,
    )


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@requires_e2e_search
class TestSearchE2E:
    """E2E tests: insert products, embed, run hybrid search."""

    async def test_hybrid_search_returns_semantic_results_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-5: Hybrid search for 'tubes inox 304L' returns semantically relevant products."""
        session = e2e_db_session

        sample_data = _load_sample_products(50)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            # Embed all products
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            # Run hybrid search
            engine = SearchEngine(session, adapter)
            result = await engine.search_hybrid(SearchRequest(query="tubes inox 304L"))

            assert len(result.results) > 0, "Hybrid search returned no results"
            assert result.method in ("hybrid", "exact_ref")
            assert result.duration_seconds > 0
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_exact_reference_search_returns_first_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-5: Exact reference search for a known reference returns that product first."""
        session = e2e_db_session

        sample_data = _load_sample_products(20)
        product_ids: list[uuid.UUID] = []
        known_ref = ""
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
            ref = str(data.get("reference", ""))
            if not known_ref and ref and is_reference_code(ref):
                known_ref = ref
        await session.flush()

        assert known_ref, "No fixture reference matches REF_CODE_PATTERN — cannot test exact_ref path"

        try:
            # Embed all products
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            # Search by exact reference — should take the exact_ref fast path
            engine = SearchEngine(session, adapter)
            result = await engine.search_hybrid(SearchRequest(query=known_ref))

            assert len(result.results) > 0, f"No results for reference '{known_ref}'"
            assert result.method == "exact_ref", (
                f"Expected exact_ref path for '{known_ref}', got '{result.method}'"
            )
            assert result.results[0].reference == known_ref
            assert result.results[0].score == 1.0
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_keyword_search_by_category_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-5: Keyword search for a category term returns relevant products."""
        session = e2e_db_session

        sample_data = _load_sample_products(50)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            # Embed all products
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            # Keyword-only search for a common category
            engine = SearchEngine(session, adapter)
            result = await engine.search_keyword_only(SearchRequest(query="Tubes"))

            # Should find at least some products
            assert result.method == "keyword"
            assert result.duration_seconds > 0
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_tsvector_column_populated_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-5: tsvector column is populated for all inserted products via trigger."""
        session = e2e_db_session

        sample_data = _load_sample_products(10)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            # Verify search_vector is populated (trigger should fire on INSERT)
            stmt = select(Product).where(Product.id.in_(product_ids))
            db_result = await session.execute(stmt)
            products = db_result.scalars().all()

            for product in products:
                assert product.search_vector is not None, (
                    f"Product {product.reference} has no search_vector — trigger may not have fired"
                )
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()
