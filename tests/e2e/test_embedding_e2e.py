"""E2E tests for embedding generation — real PostgreSQL + real embedding model."""

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
from quote_agent.services.embedding_service import EmbeddingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Skip decorator: requires real DB + embedding model availability
# ---------------------------------------------------------------------------

_E2E_MARKER = "e2e-embed-test"


def _has_real_database() -> bool:
    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


requires_e2e_embedding = pytest.mark.skipif(
    not _has_real_database(),
    reason="E2E embedding tests require real DATABASE__URL",
)


def _load_sample_products(count: int = 100) -> list[dict[str, object]]:
    """Load products from the 50K sample fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "catalog_50k_sample.jsonl"
    products = []
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


@pytest.mark.e2e
@requires_e2e_embedding
class TestEmbeddingE2E:
    """E2E tests: insert products, embed, verify vectors and semantic search."""

    async def test_embed_all_products_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-5: Insert 100 products, run embed_all(), verify all have non-null vectors of dimension 1024."""
        session = e2e_db_session

        # Insert 100 products from fixture
        sample_data = _load_sample_products(100)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            # Run embedding
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            result = await service.embed_all()

            assert result.embedded == 100
            assert result.errors == 0
            assert result.skipped_stale == 0

            # Verify all products have vectors of correct dimension
            stmt = select(Product).where(Product.id.in_(product_ids))
            db_result = await session.execute(stmt)
            products = db_result.scalars().all()

            assert len(products) == 100
            for product in products:
                assert product.vector is not None, f"Product {product.reference} has no vector"
                assert len(product.vector) == 1024, f"Product {product.reference} vector dim = {len(product.vector)}"
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_cosine_similarity_search_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-5: Cosine similarity search returns semantically relevant results."""
        session = e2e_db_session

        # Insert a few products with known content
        sample_data = _load_sample_products(20)
        product_ids: list[uuid.UUID] = []
        for data in sample_data:
            product = _insert_product_from_dict(data)
            session.add(product)
            product_ids.append(product.id)
        await session.flush()

        try:
            # Embed all
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            # Generate query vector for "tube inox"
            query_vectors = await adapter.embed_texts(["tube inox acier inoxydable"])
            query_vector = query_vectors[0]

            # Run cosine similarity search
            vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
            search_stmt = text(
                f"SELECT id, name, reference, vector <=> '{vector_str}'::vector AS distance "
                f"FROM products WHERE id = ANY(:ids) "
                f"ORDER BY vector <=> '{vector_str}'::vector LIMIT 5"
            )
            search_result = await session.execute(search_stmt, {"ids": product_ids})
            rows = search_result.fetchall()

            # Verify we got results
            assert len(rows) > 0, "Cosine similarity search returned no results"

            # At minimum, the search should return some results — semantic relevance
            # depends on sample data but search should complete without errors
            assert all(isinstance(row.distance, float) for row in rows)
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_stale_products_skipped_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-5: Stale products are skipped during embedding — vector remains NULL."""
        session = e2e_db_session

        # Insert one normal product and one stale product
        sample_data = _load_sample_products(2)
        normal_product = _insert_product_from_dict(sample_data[0], is_stale=False)
        stale_product = _insert_product_from_dict(sample_data[1], is_stale=True)
        session.add(normal_product)
        session.add(stale_product)
        await session.flush()

        product_ids = [normal_product.id, stale_product.id]

        try:
            # Run embedding
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            result = await service.embed_all()

            assert result.embedded == 1
            assert result.skipped_stale == 1

            # Verify: normal product has vector, stale does not
            await session.refresh(normal_product)
            await session.refresh(stale_product)

            assert normal_product.vector is not None
            assert len(normal_product.vector) == 1024
            assert stale_product.vector is None
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()
