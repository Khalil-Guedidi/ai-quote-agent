#!/usr/bin/env python3
"""Benchmark runner: evaluates dense, sparse, and hybrid search accuracy.

Loads test queries from test_queries.json, runs all three search methods,
computes Hit@1, Hit@5, MRR metrics, and generates a comparison report.

Ground truth uses default_code (and optionally name) matching instead of
hardcoded IDs to handle Odoo ID changes between catalog seeds.

Usage:
    python3 scripts/run-benchmark.py
    python3 scripts/run-benchmark.py --top-k 10
"""

import argparse
import json
import os
import statistics
import sys
import time

# Add parent scripts dir to path so we can import hybrid-search functions
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOTYPE_DIR = os.path.dirname(SCRIPT_DIR)
CATALOG_PATH = os.path.join(PROTOTYPE_DIR, "data", "catalog", "products_raw.json")
QUERIES_PATH = os.path.join(PROTOTYPE_DIR, "data", "benchmark", "test_queries.json")
RESULTS_PATH = os.path.join(PROTOTYPE_DIR, "data", "benchmark", "results.json")

sys.path.insert(0, SCRIPT_DIR)

# Import from hybrid-search.py (has hyphen in name)
import importlib.util

spec = importlib.util.spec_from_file_location("hybrid_search", os.path.join(SCRIPT_DIR, "hybrid-search.py"))
hs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hs)

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))


def load_catalog():
    """Load products and build lookup indexes."""
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list) and len(data) == 1 and "products" in data[0]:
        products = data[0]["products"]
    elif isinstance(data, dict) and "products" in data:
        products = data["products"]
    else:
        products = data

    # Build lookups
    code_to_ids = {}
    name_to_ids = {}
    for p in products:
        pid = p["id"]
        code = p.get("default_code")
        if code and code is not False:
            code_to_ids.setdefault(code, []).append(pid)
        name = p.get("name", "")
        if name:
            name_to_ids.setdefault(name, []).append(pid)
    return products, code_to_ids, name_to_ids


def resolve_expected_ids(query_def: dict, code_to_ids: dict, name_to_ids: dict) -> list[int]:
    """Resolve expected_default_codes and expected_names to product IDs."""
    ids = set()
    for code in query_def.get("expected_default_codes", []):
        ids.update(code_to_ids.get(code, []))
    for name in query_def.get("expected_names", []):
        ids.update(name_to_ids.get(name, []))
    return sorted(ids)


def hit_at_k(results: list[dict], expected_ids: list[int], k: int) -> int:
    """Returns 1 if any expected ID is in top-k results, 0 otherwise."""
    top_k_ids = [r["id"] for r in results[:k]]
    return 1 if any(eid in top_k_ids for eid in expected_ids) else 0


def reciprocal_rank(results: list[dict], expected_ids: list[int]) -> float:
    """Returns 1/rank of first correct result, or 0 if not found."""
    for i, r in enumerate(results):
        if r["id"] in expected_ids:
            return 1.0 / (i + 1)
    return 0.0


def find_rank(results: list[dict], expected_ids: list[int]) -> int:
    """Returns rank of first correct result, or -1 if not found."""
    for i, r in enumerate(results):
        if r["id"] in expected_ids:
            return i + 1
    return -1


def colorize(value: float, threshold_good=0.8, threshold_warn=0.6) -> str:
    """Colorize a metric value: green ≥ 80%, yellow 60-80%, red < 60%."""
    pct = value * 100
    if value >= threshold_good:
        return f"\033[92m{pct:6.1f}%\033[0m"
    elif value >= threshold_warn:
        return f"\033[93m{pct:6.1f}%\033[0m"
    else:
        return f"\033[91m{pct:6.1f}%\033[0m"


def run_benchmark(top_k: int = 10):
    """Run the full benchmark suite."""
    # Load test queries
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        test_queries = json.load(f)
    print(f"Loaded {len(test_queries)} test queries from {QUERIES_PATH}")

    # Load catalog for ID resolution
    products, code_to_ids, name_to_ids = load_catalog()
    print(f"Loaded {len(products)} products for ground truth resolution")

    # Resolve expected IDs
    for q in test_queries:
        q["expected_ids"] = resolve_expected_ids(q, code_to_ids, name_to_ids)
        if not q["expected_ids"]:
            print(f"  WARNING: No expected IDs resolved for query: \"{q['query']}\"")

    # Load models
    print(f"\nLoading dense model: {hs.DENSE_MODEL_NAME}...")
    from sentence_transformers import SentenceTransformer
    dense_model = SentenceTransformer(hs.DENSE_MODEL_NAME)

    print(f"Loading sparse model: {hs.SPARSE_MODEL_NAME}...")
    from fastembed import SparseTextEmbedding
    sparse_model = SparseTextEmbedding(model_name=hs.SPARSE_MODEL_NAME)
    print("Models loaded.\n")

    # Connect to Qdrant
    from qdrant_client import QdrantClient
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    info = client.get_collection(hs.COLLECTION_NAME)
    print(f"Connected — {hs.COLLECTION_NAME}: {info.points_count} vectors\n")

    methods = {
        "dense": lambda q: hs.search_dense(client, dense_model, q, top_k),
        "sparse": lambda q: hs.search_sparse(client, sparse_model, q, top_k),
        "hybrid": lambda q: hs.search_hybrid(client, dense_model, sparse_model, q, top_k),
    }

    # Run benchmark
    all_results = {}
    for method_name, search_fn in methods.items():
        print(f"Running {method_name} search...")
        method_results = []
        for q in test_queries:
            start = time.time()
            results = search_fn(q["query"])
            elapsed_ms = (time.time() - start) * 1000

            expected_ids = q["expected_ids"]
            h1 = hit_at_k(results, expected_ids, 1)
            h5 = hit_at_k(results, expected_ids, 5)
            mrr = reciprocal_rank(results, expected_ids)
            rank = find_rank(results, expected_ids)

            method_results.append({
                "query": q["query"],
                "category": q["category"],
                "expected_ids": expected_ids,
                "hit_at_1": h1,
                "hit_at_5": h5,
                "mrr": mrr,
                "rank": rank,
                "elapsed_ms": elapsed_ms,
                "top_results": [
                    {"id": r["id"], "name": r["name"], "default_code": r["default_code"], "score": r["score"]}
                    for r in results[:5]
                ],
            })

        all_results[method_name] = method_results
        print(f"  {method_name}: {len(method_results)} queries completed")

    # Compute aggregate metrics
    print(f"\n{'=' * 90}")
    print("  BENCHMARK RESULTS")
    print(f"{'=' * 90}")

    # Overall comparison table
    print(f"\n  {'Method':<12} {'Hit@1':>10} {'Hit@5':>10} {'MRR':>10} {'Avg ms':>10} {'P95 ms':>10}")
    print(f"  {'-' * 12} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}")

    summary = {}
    for method_name in ["dense", "sparse", "hybrid"]:
        mr = all_results[method_name]
        h1 = sum(r["hit_at_1"] for r in mr) / len(mr)
        h5 = sum(r["hit_at_5"] for r in mr) / len(mr)
        mrr = sum(r["mrr"] for r in mr) / len(mr)
        times = [r["elapsed_ms"] for r in mr]
        avg_ms = statistics.mean(times)
        p95_ms = sorted(times)[int(len(times) * 0.95)]

        summary[method_name] = {
            "hit_at_1": h1,
            "hit_at_5": h5,
            "mrr": mrr,
            "avg_ms": avg_ms,
            "p95_ms": p95_ms,
        }

        print(
            f"  {method_name:<12} {colorize(h1):>19} {colorize(h5):>19} {colorize(mrr):>19} "
            f"{avg_ms:>9.0f}ms {p95_ms:>9.0f}ms"
        )

    # Per-category breakdown
    categories = sorted(set(q["category"] for q in test_queries))
    print(f"\n  Per-Category Breakdown (Hit@5)")
    print(f"  {'Category':<20} {'Dense':>10} {'Sparse':>10} {'Hybrid':>10} {'Winner':<10}")
    print(f"  {'-' * 20} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}")

    category_summary = {}
    for cat in categories:
        cat_scores = {}
        for method_name in ["dense", "sparse", "hybrid"]:
            mr = [r for r in all_results[method_name] if r["category"] == cat]
            h5 = sum(r["hit_at_5"] for r in mr) / len(mr) if mr else 0
            cat_scores[method_name] = h5

        winner = max(cat_scores, key=cat_scores.get)
        # If tie, prefer hybrid
        if cat_scores["hybrid"] >= max(cat_scores.values()):
            winner = "hybrid"
        category_summary[cat] = cat_scores

        print(
            f"  {cat:<20} {colorize(cat_scores['dense']):>19} "
            f"{colorize(cat_scores['sparse']):>19} "
            f"{colorize(cat_scores['hybrid']):>19} {winner:<10}"
        )

    # Failed queries (rank == -1 for hybrid)
    hybrid_fails = [r for r in all_results["hybrid"] if r["rank"] == -1]
    if hybrid_fails:
        print(f"\n  HYBRID SEARCH FAILURES ({len(hybrid_fails)} queries):")
        for r in hybrid_fails:
            print(f"    ✗ [{r['category']}] \"{r['query']}\" — expected IDs: {r['expected_ids']}")
            if r["top_results"]:
                top = r["top_results"][0]
                print(f"      Got: #{top['id']} {top['name']} ({top['default_code'] or '-'})")

    # GO/NO-GO threshold check
    hybrid_h5 = summary["hybrid"]["hit_at_5"]
    go_threshold = 0.80
    print(f"\n{'=' * 90}")
    if hybrid_h5 >= go_threshold:
        print(f"  ✅ GO — Hybrid Hit@5 = {hybrid_h5*100:.1f}% (threshold: {go_threshold*100:.0f}%)")
    else:
        print(f"  ❌ NO-GO — Hybrid Hit@5 = {hybrid_h5*100:.1f}% (threshold: {go_threshold*100:.0f}%)")
    print(f"{'=' * 90}")

    # Save full results
    output = {
        "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "top_k": top_k,
        "total_queries": len(test_queries),
        "collection_points": info.points_count,
        "summary": summary,
        "category_summary": category_summary,
        "go_threshold": go_threshold,
        "go_decision": "GO" if hybrid_h5 >= go_threshold else "NO-GO",
        "per_query_results": all_results,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nFull results saved to: {RESULTS_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Run hybrid search benchmark")
    parser.add_argument("--top-k", type=int, default=10, help="Top-K results to evaluate (default: 10)")
    args = parser.parse_args()
    run_benchmark(top_k=args.top_k)


if __name__ == "__main__":
    main()
