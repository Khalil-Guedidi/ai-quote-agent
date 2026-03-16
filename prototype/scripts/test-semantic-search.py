#!/usr/bin/env python3
"""Test semantic search on the Qdrant product vector index.

Runs a set of test queries against the products collection and displays
top-5 results with similarity scores for manual quality assessment.

Usage:
    python3 scripts/test-semantic-search.py                  # run default test queries
    python3 scripts/test-semantic-search.py "custom query"           # run a single custom query
    python3 scripts/test-semantic-search.py "query one" "query two"  # run multiple custom queries
"""

import os
import sys
import time

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "products"
MODEL_NAME = "BAAI/bge-m3"
TOP_K = 5

DEFAULT_QUERIES = [
    "tube acier inoxydable",
    "boulon haute résistance M12",
    "tuyau DN50",
    "plaque acier sur mesure",
    "safety helmet",
]


def run_search(client: QdrantClient, model: SentenceTransformer, query: str):
    """Run a single semantic search query and display results."""
    print(f"\n{'=' * 70}")
    print(f"  QUERY: \"{query}\"")
    print(f"{'=' * 70}")

    start = time.time()
    query_embedding = model.encode(query, normalize_embeddings=True)
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding.tolist(),
        limit=TOP_K,
    )
    elapsed_ms = (time.time() - start) * 1000

    print(f"  Response time: {elapsed_ms:.0f}ms")
    print(f"  {'Rank':<6} {'Score':<8} {'Name':<45} {'Ref':<15} {'Category'}")
    print(f"  {'-' * 6} {'-' * 8} {'-' * 45} {'-' * 15} {'-' * 20}")

    for i, point in enumerate(results.points, 1):
        payload = point.payload
        name = (payload.get("name") or "")[:44]
        ref = (payload.get("default_code") or "-")[:14]
        categ = payload.get("categ_id")
        categ_name = categ[1] if isinstance(categ, list) and len(categ) >= 2 else "-"
        score = point.score
        print(f"  {i:<6} {score:<8.4f} {name:<45} {ref:<15} {categ_name}")

    return elapsed_ms


def main():
    # Determine queries
    if len(sys.argv) > 1:
        queries = sys.argv[1:]
    else:
        queries = DEFAULT_QUERIES

    # Load model
    print(f"Loading embedding model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    print("Model loaded.")

    # Connect to Qdrant
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"Connected to Qdrant — collection '{COLLECTION_NAME}': {collection_info.points_count} vectors")

    # Run queries
    times = []
    for query in queries:
        elapsed = run_search(client, model, query)
        times.append(elapsed)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Queries run: {len(queries)}")
    print(f"  Avg response time: {sum(times) / len(times):.0f}ms")
    print(f"  Max response time: {max(times):.0f}ms")
    all_under_500 = all(t < 500 for t in times)
    print(f"  All under 500ms: {'YES ✓' if all_under_500 else 'NO ✗'}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
