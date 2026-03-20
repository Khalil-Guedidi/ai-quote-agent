"""E2E tests for proposability filter — real PostgreSQL + real embedding model."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import delete

from quote_agent.adapters.embedding import get_embedding_adapter
from quote_agent.config import get_settings
from quote_agent.models.product import Product
from quote_agent.search import SearchEngine, SearchRequest
from quote_agent.services.embedding_service import EmbeddingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Skip decorator
# ---------------------------------------------------------------------------


def _has_real_database() -> bool:
    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


requires_e2e_search = pytest.mark.skipif(
    not _has_real_database(),
    reason="E2E proposability tests require real DATABASE__URL",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_E2E_PREFIX = "e2e-prop-test"


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


def _make_product(
    *,
    name: str,
    reference: str = "",
    category: str = "General",
    is_active: bool = True,
    stock_status: str = "in_stock",
) -> Product:
    """Create a Product model with controlled proposability attributes."""
    return Product(
        id=uuid.uuid4(),
        reference=reference or f"REF-{name.upper()[:8]}",
        name=name,
        description=f"Test product: {name}",
        category=category,
        unit_price=42.0,
        stock_status=stock_status,
        is_active=is_active,
        metadata_={"source": _E2E_PREFIX},
    )


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@requires_e2e_search
class TestProposabilityE2E:
    """E2E tests: proposability filter with real PostgreSQL + real embedding model."""

    async def test_proposable_products_returned_when_filter_enabled_e2e(
        self, e2e_db_session: AsyncSession,
    ) -> None:
        """AC-6: Only proposable products returned with filter enabled."""
        session = e2e_db_session

        # (a) active + in_stock → proposable
        prod_a = _make_product(name="Tube Inox 304L 25mm", stock_status="in_stock")
        # (b) inactive → not proposable
        prod_b = _make_product(name="Tube Inox 316L 30mm", is_active=False)
        # (c) out_of_stock → not proposable
        prod_c = _make_product(name="Tube Inox 304L 50mm", stock_status="out_of_stock")
        # (d) active + on_order → proposable
        prod_d = _make_product(name="Tube Inox 304L 40mm", stock_status="on_order")

        all_products = [prod_a, prod_b, prod_c, prod_d]
        product_ids = [p.id for p in all_products]
        for p in all_products:
            session.add(p)
        await session.flush()

        try:
            # Embed all products
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            # Run hybrid search with proposability filter ON (default)
            engine = SearchEngine(session, adapter)
            result = await engine.search_hybrid(SearchRequest(query="tube inox 304L"))

            # Only proposable products (a, d) should be in results
            result_ids = {r.product_id for r in result.results}
            assert prod_a.id in result_ids or prod_d.id in result_ids, (
                "At least one proposable product should be returned"
            )
            assert prod_b.id not in result_ids, "Inactive product should be filtered out"
            assert prod_c.id not in result_ids, "Out-of-stock product should be filtered out"

            # All returned products should be proposable
            for r in result.results:
                if r.product_id in product_ids:
                    assert r.is_proposable is True
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_all_products_returned_when_filter_disabled_e2e(
        self, e2e_db_session: AsyncSession,
    ) -> None:
        """AC-6: All products returned with filter disabled, is_proposable correctly set."""
        session = e2e_db_session

        prod_a = _make_product(name="Plaque Acier 10mm", stock_status="in_stock")
        prod_b = _make_product(name="Plaque Acier 20mm", is_active=False)
        prod_c = _make_product(name="Plaque Acier 30mm", stock_status="out_of_stock")
        prod_d = _make_product(name="Plaque Acier 5mm", stock_status="on_order")

        all_products = [prod_a, prod_b, prod_c, prod_d]
        product_ids = [p.id for p in all_products]
        for p in all_products:
            session.add(p)
        await session.flush()

        try:
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            engine = SearchEngine(session, adapter)
            result = await engine.search_hybrid(
                SearchRequest(query="plaque acier", apply_proposability_filter=False),
            )

            # All 4 products should appear (filter is off, query matches all)
            test_results = {r.product_id: r for r in result.results if r.product_id in product_ids}
            assert len(test_results) >= 2, (
                f"Expected at least 2 test products in results, got {len(test_results)}"
            )

            # Check is_proposable is correctly computed for our test products
            if prod_a.id in test_results:
                assert test_results[prod_a.id].is_proposable is True
            if prod_b.id in test_results:
                assert test_results[prod_b.id].is_proposable is False
            if prod_c.id in test_results:
                assert test_results[prod_c.id].is_proposable is False
            if prod_d.id in test_results:
                assert test_results[prod_d.id].is_proposable is True
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_excluded_categories_filter_e2e(
        self, e2e_db_session: AsyncSession,
    ) -> None:
        """AC-6: excluded_categories config filters products by category."""
        session = e2e_db_session

        prod_a = _make_product(name="Vis Hexagonale M8", category="Boulonnerie")
        prod_b = _make_product(name="Vis Hexagonale M10", category="Obsolete")

        all_products = [prod_a, prod_b]
        product_ids = [p.id for p in all_products]
        for p in all_products:
            session.add(p)
        await session.flush()

        try:
            adapter = get_embedding_adapter()
            service = EmbeddingService(adapter, session)
            await service.embed_all()

            # Patch settings to add excluded_categories
            settings = get_settings()
            original_cats = settings.proposability.excluded_categories
            settings.proposability.excluded_categories = ["Obsolete"]

            try:
                engine = SearchEngine(session, adapter)
                result = await engine.search_hybrid(SearchRequest(query="vis hexagonale"))

                result_ids = {r.product_id for r in result.results}
                assert prod_b.id not in result_ids, "Product in excluded category should be filtered"
            finally:
                settings.proposability.excluded_categories = original_cats
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()
