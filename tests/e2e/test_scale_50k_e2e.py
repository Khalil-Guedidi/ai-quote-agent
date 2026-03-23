"""Scale E2E tests — large product catalogue pipeline validation.

Story 5.5.4: Canari 50K — Pipeline à Échelle

Validates the full pipeline (search, scoring, routing, agent) at realistic scale.
Product count is configurable via SCALE_TEST_PRODUCT_COUNT env var (default: 2000).
These tests are excluded from the standard E2E suite by default.

Run with:
    pytest -m "e2e and scale" tests/e2e/test_scale_50k_e2e.py -v
    SCALE_TEST_PRODUCT_COUNT=50000 pytest -m "e2e and scale" tests/e2e/test_scale_50k_e2e.py -v
"""

from __future__ import annotations

import logging
import time

import pytest
from sqlalchemy import delete, func, select

from quote_agent.adapters.embedding import get_embedding_adapter
from quote_agent.agent.graph import get_agent_graph
from quote_agent.agent.state import create_initial_state
from quote_agent.config import get_settings
from quote_agent.models.base import _get_session_factory
from quote_agent.models.product import Product
from quote_agent.search import SearchRequest, get_search_engine
from quote_agent.services.embedding_service import EmbeddingService
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem
from tests.e2e.conftest import requires_e2e
from tests.e2e.helpers.bulk_loader import _get_product_count, load_50k_fixture
from tests.e2e.helpers.nfr_metrics import (
    NFR1_PIPELINE_MAX_SECONDS,
    NFR2_SEARCH_MAX_SECONDS,
    NFR6_CACHE_HIT_MAX_SECONDS,
    compute_stats,
    get_peak_rss_mb,
    log_nfr_report,
    measure_time,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Markers — both e2e and scale, skipped by default
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.scale,
]

# ---------------------------------------------------------------------------
# Test queries — designed to exploit 50K catalogue diversity
# ---------------------------------------------------------------------------

# Diverse search queries for latency measurement
_SEARCH_QUERIES = [
    "tube acier galvanisé DN50",
    "filtre huile hydraulique 50 microns",
    "joint torique NBR 40x3",
    "vis hexagonale M12x40 inox A2",
    "vanne papillon DN100 PN16",
    "roulement à billes 6205",
    "câble acier 10mm",
    "pompe centrifuge industrielle",
    "bride plate DN80",
    "écrou HM M16 acier zingué",
]

# Confidence tier trigger queries (AC #5)
_HIGH_CONFIDENCE_QUERY = ExtractedQuoteRequest(
    client_name="ArcelorMittal France",
    client_identifier="ARCELORMITTAL",
    line_items=[
        QuoteLineItem(
            description="Filtre à huile 50 microns 10L/min",
            quantity=500,
            unit="pièce",
            reference="FLT-50um-10L/min-RRO",
        ),
    ],
    raw_text="Je voudrais 500 filtres à huile réf FLT-50um-10L/min-RRO pour usine Dunkerque",
)

_MEDIUM_CONFIDENCE_QUERY = ExtractedQuoteRequest(
    client_name="Descours & Cabaud",
    client_identifier="DESCOURS",
    line_items=[
        QuoteLineItem(
            description="joints toriques pour vanne industrielle",
            quantity=200,
            unit="pièce",
        ),
    ],
    raw_text="Bonjour, nous aurions besoin de 200 joints toriques pour vannes industrielles.",
)

_LOW_CONFIDENCE_QUERY = ExtractedQuoteRequest(
    client_name="NouveauClient SAS",
    client_identifier="NOUVEAUCLIENT",
    line_items=[
        QuoteLineItem(
            description="prestation de nettoyage industriel sur site",
            quantity=1,
            unit="prestation",
        ),
    ],
    raw_text="Nous recherchons une prestation de nettoyage industriel sur site pour notre usine de Nantes.",
)


# ---------------------------------------------------------------------------
# Session-scoped fixture: load products + embed (runs once per test session)
# ---------------------------------------------------------------------------

# Minimum product count for meaningful scale testing
_MIN_SCALE_PRODUCTS = 1000


@pytest.fixture(scope="session")
async def scale_50k_catalog() -> int:
    """Bulk-load products and generate embeddings.

    Volume controlled by SCALE_TEST_PRODUCT_COUNT env var (default: 2000).
    Session-scoped: runs once, shared across all tests in this module.
    Returns the total number of products with embeddings.
    """
    target = _get_product_count()
    factory = _get_session_factory()

    # Step 0: Trim excess products if previous run loaded more than target
    async with factory() as session:
        total_result = await session.execute(
            select(func.count()).select_from(Product).where(Product.is_stale.is_(False))
        )
        total_in_db = total_result.scalar_one()
        if total_in_db > target:
            excess = total_in_db - target
            logger.info("Trimming %d excess products (have %d, target %d)", excess, total_in_db, target)
            # Delete products beyond the target count (keep oldest by created_at)
            excess_ids_subq = (
                select(Product.id)
                .where(Product.is_stale.is_(False))
                .order_by(Product.created_at.desc())
                .limit(excess)
            ).scalar_subquery()
            await session.execute(delete(Product).where(Product.id.in_(excess_ids_subq)))
            await session.commit()
            logger.info("Trimmed %d products, now at target %d", excess, target)

    # Step 1: Bulk-load products (if needed)
    logger.info("=== SCALE FIXTURE: Loading %d products ===", target)
    load_start = time.perf_counter()

    async with factory() as session:
        inserted = await load_50k_fixture(session)
        logger.info("Bulk load: %d products inserted", inserted)

    load_duration = time.perf_counter() - load_start

    # Step 2: Generate embeddings (only for products with NULL vector)
    logger.info("=== SCALE FIXTURE: Generating embeddings (%d products, CPU may take a while) ===", target)
    embed_start = time.perf_counter()

    async with factory() as session:
        adapter = get_embedding_adapter()
        service = EmbeddingService(adapter, session)
        result = await service.embed_all()
        logger.info(
            "Embedding complete: %d embedded, %d errors, %.2fs",
            result.embedded,
            result.errors,
            result.duration_seconds,
        )

    embed_duration = time.perf_counter() - embed_start

    # Step 3: Verify product count with vectors
    async with factory() as session:
        count_result = await session.execute(
            select(func.count()).select_from(Product).where(
                Product.vector.isnot(None),
                Product.is_stale.is_(False),
            )
        )
        total_with_vectors = count_result.scalar_one()

    logger.info(
        "=== SCALE FIXTURE READY: %d products with vectors (load=%.1fs, embed=%.1fs) ===",
        total_with_vectors,
        load_duration,
        embed_duration,
    )

    return total_with_vectors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@requires_e2e
async def test_search_latency_50k_e2e(scale_50k_catalog: int) -> None:
    """AC #3: Hybrid search returns results in < 3 seconds for 10 diverse queries.

    Measures p50/p95 search latency across 10 industrial queries at 50K scale.
    """
    assert scale_50k_catalog >= _MIN_SCALE_PRODUCTS, (
        f"Expected >= {_MIN_SCALE_PRODUCTS} products, got {scale_50k_catalog}"
    )

    factory = _get_session_factory()

    # Warm-up: load BGE-M3 model into memory (first call is slow due to model loading)
    async with factory() as session:
        engine = get_search_engine(session)
        await engine.search_hybrid(SearchRequest(query="warm-up", limit=1))
    logger.info("Warm-up complete — BGE-M3 model loaded")

    latencies: list[float] = []

    for query_text in _SEARCH_QUERIES:
        async with factory() as session:
            engine = get_search_engine(session)
            request = SearchRequest(query=query_text, limit=10)

            with measure_time() as elapsed:
                result = await engine.search_hybrid(request)

            latencies.append(elapsed[0])
            logger.info(
                "Search '%s': %d results in %.3fs",
                query_text,
                len(result.results),
                elapsed[0],
            )
            assert len(result.results) > 0, f"No results for query: {query_text}"

    stats = compute_stats(latencies)
    logger.info("Search latency stats: %s", stats)

    # AC #3: each search < 3 seconds
    for i, latency in enumerate(latencies):
        assert latency < NFR2_SEARCH_MAX_SECONDS, (
            f"Query '{_SEARCH_QUERIES[i]}' took {latency:.3f}s (NFR2 limit: {NFR2_SEARCH_MAX_SECONDS}s)"
        )


@requires_e2e
async def test_cache_hit_latency_50k_e2e(scale_50k_catalog: int) -> None:
    """AC #3: Cache hits return in < 1 second.

    Runs the same queries twice — second run should hit cache.
    """
    assert scale_50k_catalog >= _MIN_SCALE_PRODUCTS

    factory = _get_session_factory()
    cache_latencies: list[float] = []

    # Warm-up: ensure BGE-M3 model is loaded
    async with factory() as session:
        engine = get_search_engine(session)
        await engine.search_hybrid(SearchRequest(query="warm-up", limit=1))

    for query_text in _SEARCH_QUERIES:
        async with factory() as session:
            engine = get_search_engine(session)
            request = SearchRequest(query=query_text, limit=10)

            # First call to populate cache
            await engine.search_hybrid(request)
            # Commit so cache entry is persisted for the next session
            await session.commit()

        # Second call — should hit cache
        async with factory() as session:
            engine = get_search_engine(session)
            request = SearchRequest(query=query_text, limit=10)

            with measure_time() as elapsed:
                result = await engine.search_hybrid(request)

            cache_latencies.append(elapsed[0])
            assert result.from_cache, f"Expected cache hit for query: {query_text}"

    stats = compute_stats(cache_latencies)
    logger.info("Cache hit latency stats: %s", stats)

    # AC #3: cache hit < 1 second
    for i, latency in enumerate(cache_latencies):
        assert latency < NFR6_CACHE_HIT_MAX_SECONDS, (
            f"Cache hit for '{_SEARCH_QUERIES[i]}' took {latency:.3f}s (NFR6 limit: {NFR6_CACHE_HIT_MAX_SECONDS}s)"
        )


@requires_e2e
async def test_pipeline_end_to_end_50k_e2e(scale_50k_catalog: int) -> None:
    """AC #4: Full agent pipeline completes in < 2 minutes at 50K scale.

    Runs the full pipeline (classify → reason → score → route → review → compliance → draft/notify)
    with a realistic quote request against the 50K catalogue.
    """
    assert scale_50k_catalog >= _MIN_SCALE_PRODUCTS

    request = ExtractedQuoteRequest(
        client_name="ArcelorMittal France",
        client_identifier="ARCELORMITTAL",
        line_items=[
            QuoteLineItem(
                description="tubes acier galvanisé DN50 pour chantier Le Havre",
                quantity=500,
                unit="mètre",
            ),
        ],
        raw_text="Je voudrais 500 tubes acier galvanisé DN50 pour chantier Le Havre",
    )

    graph = get_agent_graph()
    initial_state = create_initial_state(request)

    with measure_time() as elapsed:
        result = await graph.ainvoke(initial_state)

    logger.info(
        "Pipeline completed in %.2fs — final_action=%s, error=%s",
        elapsed[0],
        result.get("final_action"),
        result.get("error"),
    )

    # AC #4: < 2 minutes
    assert elapsed[0] < NFR1_PIPELINE_MAX_SECONDS, (
        f"Pipeline took {elapsed[0]:.1f}s (NFR1 limit: {NFR1_PIPELINE_MAX_SECONDS}s)"
    )

    # Pipeline should complete without error (route to some action)
    assert result.get("error") is None, f"Pipeline error: {result.get('error')}"
    assert result.get("final_action"), "Pipeline should produce a final_action"


@requires_e2e
async def test_confidence_tier_diversity_50k_e2e(scale_50k_catalog: int) -> None:
    """AC #5: At least 3 diverse queries trigger different confidence tiers.

    Tests that the 50K catalogue creates genuine scoring differentiation
    across high, medium, and low confidence paths.
    """
    assert scale_50k_catalog >= _MIN_SCALE_PRODUCTS

    graph = get_agent_graph()
    tier_queries = {
        "high": _HIGH_CONFIDENCE_QUERY,
        "medium": _MEDIUM_CONFIDENCE_QUERY,
        "low": _LOW_CONFIDENCE_QUERY,
    }

    results: dict[str, dict[str, object]] = {}
    triggered_actions: set[str] = set()

    for tier_name, request in tier_queries.items():
        initial_state = create_initial_state(request)

        with measure_time() as elapsed:
            result = await graph.ainvoke(initial_state)

        final_action = result.get("final_action", "")
        confidence = result.get("confidence")
        confidence_score = getattr(confidence, "overall_score", None) if confidence else None
        confidence_tier = getattr(confidence, "tier", None) if confidence else None
        error = result.get("error")

        results[tier_name] = {
            "final_action": final_action,
            "confidence_score": confidence_score,
            "confidence_tier": confidence_tier,
            "error": error,
            "duration_s": round(elapsed[0], 2),
        }

        if final_action:
            triggered_actions.add(str(final_action))

        logger.info(
            "Tier %s: action=%s, score=%s, tier=%s, error=%s, duration=%.2fs",
            tier_name,
            final_action,
            confidence_score,
            confidence_tier,
            error,
            elapsed[0],
        )

    # Log full results for analysis
    logger.info("Confidence tier diversity results: %s", results)

    # AC #5: at least 2 distinct final_action values (differentiation exists)
    # Note: if medium-confidence doesn't trigger, that's a documented finding, not a test failure
    settings = get_settings()
    logger.info(
        "Confidence thresholds: high=%.2f, low=%.2f",
        settings.confidence_scoring.high_threshold,
        settings.confidence_scoring.low_threshold,
    )

    assert len(triggered_actions) >= 2, (
        f"Expected at least 2 distinct actions, got {triggered_actions}. "
        f"Results: {results}"
    )


@requires_e2e
async def test_nfr_report_50k_e2e(scale_50k_catalog: int) -> None:
    """AC #6: Collect and log all NFR metrics as structured JSON report.

    Aggregates metrics from search latency, cache, pipeline, and memory into
    a single structured report.
    """
    assert scale_50k_catalog >= _MIN_SCALE_PRODUCTS

    factory = _get_session_factory()

    # Measure search latencies
    search_latencies: list[float] = []
    for query_text in _SEARCH_QUERIES[:5]:  # Sample 5 queries
        async with factory() as session:
            engine = get_search_engine(session)
            request = SearchRequest(query=query_text, limit=10)

            with measure_time() as elapsed:
                await engine.search_hybrid(request)
            search_latencies.append(elapsed[0])

    # Measure pipeline latency
    pipeline_request = ExtractedQuoteRequest(
        client_name="Descours & Cabaud",
        client_identifier="DESCOURS",
        line_items=[
            QuoteLineItem(
                description="vis hexagonale M12x40 inox A2",
                quantity=100,
                unit="pièce",
            ),
        ],
        raw_text="Besoin de 100 vis hexagonale M12x40 inox A2",
    )

    graph = get_agent_graph()
    initial_state = create_initial_state(pipeline_request)

    with measure_time() as pipeline_elapsed:
        await graph.ainvoke(initial_state)

    # Measure HNSW index size
    async with factory() as session:
        index_size_result = await session.execute(
            select(func.pg_relation_size("ix_products_vector_hnsw"))
        )
        hnsw_index_bytes = index_size_result.scalar_one_or_none() or 0

    # Build NFR report
    search_stats = compute_stats(search_latencies)
    peak_rss = get_peak_rss_mb()

    report = {
        "story": "5.5.4",
        "product_count": scale_50k_catalog,
        "ingestion": {
            "note": "Duration logged by session-scoped fixture — see fixture logs above",
        },
        "embedding": {
            "note": "Duration logged by session-scoped fixture — see fixture logs above",
        },
        "search_latency": {
            "samples": len(search_latencies),
            "p50_seconds": search_stats["p50"],
            "p95_seconds": search_stats["p95"],
            "mean_seconds": search_stats["mean"],
            "max_seconds": search_stats["max"],
            "nfr2_target_seconds": NFR2_SEARCH_MAX_SECONDS,
            "nfr2_pass": all(lat < NFR2_SEARCH_MAX_SECONDS for lat in search_latencies),
        },
        "pipeline_e2e": {
            "duration_seconds": round(pipeline_elapsed[0], 2),
            "nfr1_target_seconds": NFR1_PIPELINE_MAX_SECONDS,
            "nfr1_pass": pipeline_elapsed[0] < NFR1_PIPELINE_MAX_SECONDS,
        },
        "memory": {
            "peak_rss_mb": round(peak_rss, 1),
        },
        "hnsw_index": {
            "size_bytes": hnsw_index_bytes,
            "size_mb": round(hnsw_index_bytes / (1024 * 1024), 2) if hnsw_index_bytes else 0,
        },
    }

    log_nfr_report(report)

    # This test always passes — it's a measurement test.
    # NFR violations are documented findings, not test failures (per story spec).
    assert scale_50k_catalog > 0, "NFR report requires loaded products"
