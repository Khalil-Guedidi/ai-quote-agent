#!/usr/bin/env python3
"""Hybrid search functions: dense, sparse, and hybrid (dense + sparse with fusion).

Provides three search methods against the Qdrant products collection:
- search_dense(): semantic search using BGE-M3 dense embeddings
- search_sparse(): BM25 keyword search using Qdrant/bm25 sparse vectors
- search_hybrid(): combined dense + sparse with Reciprocal Rank Fusion (RRF)

Also includes exact reference matching via payload filter for known default_code patterns.

Usage:
    python3 scripts/hybrid-search.py "query text"
    python3 scripts/hybrid-search.py --method dense "query text"
    python3 scripts/hybrid-search.py --method sparse "query text"
    python3 scripts/hybrid-search.py --method hybrid "query text"
    python3 scripts/hybrid-search.py --method all "query text"
"""

import argparse
import os
import re
import time

from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
    SparseVector,
)
from sentence_transformers import SentenceTransformer

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "products"
DENSE_MODEL_NAME = "BAAI/bge-m3"
SPARSE_MODEL_NAME = "Qdrant/bm25"
DEFAULT_TOP_K = 10

# Pattern for product reference codes (e.g., BHM-M12x60, TCA-10mm, TPVC-DN50)
REF_CODE_PATTERN = re.compile(
    r"^[A-Z]{2,6}[-][A-Z0-9.²]+(?:[-][A-Z0-9.²x]+)*$", re.IGNORECASE
)


def _format_result(point, rank: int) -> dict:
    """Format a Qdrant search result into a standardized dict."""
    payload = point.payload or {}
    return {
        "id": point.id,
        "name": payload.get("name", ""),
        "default_code": payload.get("default_code") or "",
        "score": point.score if hasattr(point, "score") and point.score is not None else 0.0,
        "rank": rank,
        "categ_id": payload.get("categ_id"),
        "sale_ok": payload.get("sale_ok"),
        "active": payload.get("active"),
    }


def search_exact_ref(
    client: QdrantClient, query: str, collection_name: str = COLLECTION_NAME, limit: int = 5
) -> list[dict]:
    """Try exact reference match via payload filter on default_code."""
    query_stripped = query.strip()
    results, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter=Filter(
            should=[
                FieldCondition(key="default_code", match=MatchValue(value=query_stripped)),
                FieldCondition(key="default_code", match=MatchValue(value=query_stripped.upper())),
            ]
        ),
        limit=limit,
    )
    return [
        {
            "id": point.id,
            "name": (point.payload or {}).get("name", ""),
            "default_code": (point.payload or {}).get("default_code", ""),
            "score": 1.0,  # exact match
            "rank": i + 1,
            "categ_id": (point.payload or {}).get("categ_id"),
            "sale_ok": (point.payload or {}).get("sale_ok"),
            "active": (point.payload or {}).get("active"),
        }
        for i, point in enumerate(results)
    ]


def search_dense(
    client: QdrantClient,
    dense_model: SentenceTransformer,
    query: str,
    limit: int = DEFAULT_TOP_K,
    collection_name: str = COLLECTION_NAME,
) -> list[dict]:
    """Semantic search using dense BGE-M3 embeddings."""
    query_embedding = dense_model.encode(query, normalize_embeddings=True)
    results = client.query_points(
        collection_name=collection_name,
        query=query_embedding.tolist(),
        using="dense",
        limit=limit,
    )
    return [_format_result(p, i + 1) for i, p in enumerate(results.points)]


def search_sparse(
    client: QdrantClient,
    sparse_model: SparseTextEmbedding,
    query: str,
    limit: int = DEFAULT_TOP_K,
    collection_name: str = COLLECTION_NAME,
) -> list[dict]:
    """BM25 keyword search using sparse vectors."""
    sparse_embeddings = list(sparse_model.embed([query]))
    sparse_emb = sparse_embeddings[0]
    sparse_vector = SparseVector(
        indices=sparse_emb.indices.tolist(),
        values=sparse_emb.values.tolist(),
    )
    results = client.query_points(
        collection_name=collection_name,
        query=sparse_vector,
        using="sparse",
        limit=limit,
    )
    return [_format_result(p, i + 1) for i, p in enumerate(results.points)]


def search_hybrid(
    client: QdrantClient,
    dense_model: SentenceTransformer,
    sparse_model: SparseTextEmbedding,
    query: str,
    limit: int = DEFAULT_TOP_K,
    collection_name: str = COLLECTION_NAME,
) -> list[dict]:
    """Hybrid search: dense + sparse with Reciprocal Rank Fusion (RRF).

    If the query looks like a product reference code, prepend exact-match results.
    """
    # Check for exact reference match first
    if REF_CODE_PATTERN.match(query.strip()):
        exact_results = search_exact_ref(client, query, collection_name=collection_name)
        if exact_results:
            return exact_results[:limit]

    # Dense embedding
    query_embedding = dense_model.encode(query, normalize_embeddings=True)

    # Sparse embedding
    sparse_embeddings = list(sparse_model.embed([query]))
    sparse_emb = sparse_embeddings[0]
    sparse_vector = SparseVector(
        indices=sparse_emb.indices.tolist(),
        values=sparse_emb.values.tolist(),
    )

    # Hybrid search with prefetch + RRF fusion
    results = client.query_points(
        collection_name=collection_name,
        prefetch=[
            Prefetch(
                query=query_embedding.tolist(),
                using="dense",
                limit=20,
            ),
            Prefetch(
                query=sparse_vector,
                using="sparse",
                limit=20,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
    )
    return [_format_result(p, i + 1) for i, p in enumerate(results.points)]


def timed_search(search_fn, *args, **kwargs) -> tuple[list[dict], float]:
    """Run a search function and return (results, elapsed_ms)."""
    start = time.time()
    results = search_fn(*args, **kwargs)
    elapsed_ms = (time.time() - start) * 1000
    return results, elapsed_ms


def print_results(method: str, query: str, results: list[dict], elapsed_ms: float):
    """Pretty-print search results."""
    print(f"\n{'=' * 80}")
    print(f"  [{method.upper()}] Query: \"{query}\"  ({elapsed_ms:.0f}ms)")
    print(f"{'=' * 80}")
    print(f"  {'Rank':<6} {'Score':<8} {'ID':<6} {'Name':<45} {'Ref':<20}")
    print(f"  {'-' * 6} {'-' * 8} {'-' * 6} {'-' * 45} {'-' * 20}")

    for r in results:
        name = r["name"][:44]
        ref = (r["default_code"] or "-")[:19]
        print(f"  {r['rank']:<6} {r['score']:<8.4f} {r['id']:<6} {name:<45} {ref:<20}")

    if not results:
        print("  (no results)")


def main():
    parser = argparse.ArgumentParser(description="Hybrid search on product catalog")
    parser.add_argument("query", nargs="+", help="Search query text")
    parser.add_argument(
        "--method", choices=["dense", "sparse", "hybrid", "all"], default="all",
        help="Search method (default: all)",
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Number of results")
    args = parser.parse_args()
    query = " ".join(args.query)

    # Load models
    print(f"Loading dense model: {DENSE_MODEL_NAME}...")
    dense_model = SentenceTransformer(DENSE_MODEL_NAME)
    print(f"Loading sparse model: {SPARSE_MODEL_NAME}...")
    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
    print("Models loaded.")

    # Connect to Qdrant
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    info = client.get_collection(COLLECTION_NAME)
    print(f"Connected — {COLLECTION_NAME}: {info.points_count} vectors")

    methods = [args.method] if args.method != "all" else ["dense", "sparse", "hybrid"]

    for method in methods:
        if method == "dense":
            results, ms = timed_search(search_dense, client, dense_model, query, args.top_k)
        elif method == "sparse":
            results, ms = timed_search(search_sparse, client, sparse_model, query, args.top_k)
        elif method == "hybrid":
            results, ms = timed_search(
                search_hybrid, client, dense_model, sparse_model, query, args.top_k
            )
        print_results(method, query, results, ms)


if __name__ == "__main__":
    main()
