"""E2E tests for jargon query expansion — real PostgreSQL + real embedding model."""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import delete

from quote_agent.adapters.embedding import get_embedding_adapter
from quote_agent.models.product import Product
from quote_agent.search import SearchEngine, SearchRequest
from quote_agent.services.embedding_service import EmbeddingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Skip decorator
# ---------------------------------------------------------------------------

_E2E_MARKER = "e2e-jargon-test"

logger = logging.getLogger(__name__)


def _has_real_database() -> bool:
    url = os.environ.get("DATABASE__URL", "")
    return url.startswith("postgresql")


requires_e2e_search = pytest.mark.skipif(
    not _has_real_database(),
    reason="E2E jargon tests require real DATABASE__URL",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sample_products(count: int = 100) -> list[dict[str, object]]:
    """Load products from the 50K sample fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "catalog_50k_sample.jsonl"
    products: list[dict[str, object]] = []
    with fixture_path.open() as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            products.append(json.loads(line))
    return products


def _load_benchmark_queries() -> list[dict[str, object]]:
    """Load jargon benchmark test cases."""
    fixture_path = Path(__file__).parent / "fixtures" / "jargon_benchmark.json"
    with fixture_path.open() as f:
        return json.load(f)


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


def _result_matches_keywords(results: list[object], expected_keywords: list[str]) -> bool:
    """Check if ANY expected keyword appears in any top-5 result name/description/reference."""
    for result in results[:5]:
        text = f"{result.name} {result.description or ''} {result.reference}".lower()  # type: ignore[union-attr]
        for kw in expected_keywords:
            if kw.lower() in text:
                return True
    return False


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@requires_e2e_search
class TestSearchJargonE2E:
    """AC-7: E2E tests with real PostgreSQL and embedding model."""

    async def test_jargon_query_returns_relevant_products_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-7: Jargon-heavy query returns correct products with expansion enabled."""
        session = e2e_db_session

        sample_data = _load_sample_products(100)
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
            result = await engine.search_hybrid(
                SearchRequest(query="tubes inox 304L Ø25 lg 6m")
            )

            assert len(result.results) > 0, "Jargon search returned no results"
            assert result.jargon_expanded is True
            assert result.expanded_query is not None
            assert "acier inoxydable" in result.expanded_query
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_expansion_disabled_still_finds_products_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-7: With expansion disabled, semantic search still handles common jargon."""
        session = e2e_db_session

        sample_data = _load_sample_products(100)
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

            # Construct settings with expansion disabled (avoid Pydantic instance mutation)
            from unittest.mock import patch

            from quote_agent.config import JargonSettings
            from quote_agent.config import get_settings as real_get_settings

            real = real_get_settings()
            disabled_jargon = JargonSettings(expansion_enabled=False)
            patched = real.model_copy(update={"jargon": disabled_jargon})

            with patch("quote_agent.search.engine.get_settings", return_value=patched):
                engine = SearchEngine(session, adapter)
                result = await engine.search_hybrid(
                    SearchRequest(query="tubes inox 304L")
                )

            assert result.jargon_expanded is False
            assert result.expanded_query is None
            # Semantic search should still find relevant products via BGE-M3
            assert len(result.results) > 0, "Semantic search should still find products without expansion"
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_cross_language_matching_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-3: French/English mix queries return relevant results via multilingual embedding."""
        session = e2e_db_session

        sample_data = _load_sample_products(100)
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
            # Mixed French/English query
            result = await engine.search_hybrid(
                SearchRequest(query="stainless steel tube DN100")
            )

            assert len(result.results) > 0, "Cross-language query returned no results"
            assert result.method in ("hybrid", "exact_ref")
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()

    async def test_jargon_metadata_set_on_search_result_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-2: jargon_expanded=True and expanded_query set on SearchResult when expansion occurs."""
        session = e2e_db_session

        sample_data = _load_sample_products(50)
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
            result = await engine.search_hybrid(
                SearchRequest(query="clapet inox DN150 PN40")
            )

            assert result.jargon_expanded is True
            assert result.expanded_query is not None
            assert "acier inoxydable" in result.expanded_query
            assert "diamètre nominal" in result.expanded_query
            assert "pression nominale" in result.expanded_query
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()


@pytest.mark.e2e
@pytest.mark.benchmark
@requires_e2e_search
class TestJargonBenchmarkE2E:
    """AC-6: Jargon benchmark test suite — 20+ queries, >= 80% pass rate."""

    async def test_jargon_benchmark_pass_rate_e2e(self, e2e_db_session: AsyncSession) -> None:
        """AC-6: At least 80% of benchmark queries find expected product in top-5."""
        session = e2e_db_session

        # Load all products (use more for better coverage)
        sample_data = _load_sample_products(200)
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
            benchmark_queries = _load_benchmark_queries()

            assert len(benchmark_queries) >= 20, (
                f"Benchmark fixture must have 20+ queries, got {len(benchmark_queries)}"
            )

            pass_count = 0
            fail_count = 0
            results_log: list[dict[str, object]] = []

            for case in benchmark_queries:
                query = str(case["query"])
                expected_keywords: list[str] = case["expected_match_keywords"]  # type: ignore[assignment]
                category = str(case.get("category", "unknown"))

                result = await engine.search_hybrid(SearchRequest(query=query))
                matched = _result_matches_keywords(result.results, expected_keywords)

                if matched:
                    pass_count += 1
                    status = "PASS"
                else:
                    fail_count += 1
                    status = "FAIL"

                results_log.append({
                    "query": query,
                    "category": category,
                    "status": status,
                    "results_count": len(result.results),
                    "jargon_expanded": result.jargon_expanded,
                    "top_5_names": [r.name for r in result.results[:5]],
                })

            total = pass_count + fail_count
            pass_rate = pass_count / total if total > 0 else 0.0

            logger.info(
                "Jargon benchmark completed",
                extra={"context": {
                    "component": "search.jargon.benchmark",
                    "total_queries": total,
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                    "pass_rate": round(pass_rate, 4),
                    "results": results_log,
                }},
            )

            assert pass_rate >= 0.80, (
                f"Jargon benchmark pass rate {pass_rate:.1%} is below 80% threshold. "
                f"Passed: {pass_count}/{total}. "
                f"Failed queries: {[r['query'] for r in results_log if r['status'] == 'FAIL']}"
            )
        finally:
            await session.execute(delete(Product).where(Product.id.in_(product_ids)))
            await session.commit()
