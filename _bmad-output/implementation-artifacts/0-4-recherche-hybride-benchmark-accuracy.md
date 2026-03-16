# Story 0.4: Recherche Hybride (Vector + Keyword) — Benchmark Accuracy

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want to benchmark hybrid search (vector + keyword) accuracy on the dirty catalog,
So that I can validate the core technical assumption: product matching works without manual catalog cleaning.

**This is the critical story — the #1 technical risk validation for the entire project.**

## Acceptance Criteria

1. **AC-0.4.1**: Hybrid search combining vector similarity + keyword/reference matching
   - Given: The Qdrant `products` collection exists with ~726 dense vector embeddings (from Story 0.3)
   - When: The developer adds sparse vector support to the collection and implements hybrid search
   - Then: A hybrid search function exists that combines dense (semantic) + sparse (lexical/BM25) retrieval
   - And: The hybrid search uses Qdrant's Query API with `prefetch` for multi-method retrieval and fusion (RRF or DBSF)
   - And: The search accepts a text query and returns top-K results with combined scores
   - And: An exact reference matching fallback exists: if a query contains a known `default_code` pattern, it's matched directly via payload filter before vector search

2. **AC-0.4.2**: Test suite of 20+ realistic product queries (jargon, typos, abbreviations, exact refs)
   - Given: The hybrid search is implemented
   - When: The developer runs the benchmark test suite
   - Then: At least 20 test queries are defined, each with:
     - Query text (realistic industrial French + some English)
     - Expected product ID(s) — the correct answer(s) from the catalog
     - Query category tag (one of: `standard`, `abbreviation`, `jargon`, `exact-ref`, `typo`, `cross-lingual`, `custom-product`, `multi-word`, `technical-spec`)
   - And: Test queries cover ALL category tags (at least 2 per category)
   - And: The test suite is stored as a JSON file (`prototype/data/benchmark/test_queries.json`) for reproducibility

3. **AC-0.4.3**: Accuracy metrics documented (precision, recall, top-k hit rate)
   - Given: The benchmark test suite has been executed
   - When: The developer reviews the benchmark results
   - Then: The following metrics are calculated and reported per search method AND overall:
     - **Hit@1**: % of queries where the correct product is the #1 result
     - **Hit@5**: % of queries where the correct product is in the top 5 results
     - **MRR** (Mean Reciprocal Rank): average of 1/rank for the correct product
   - And: Results are broken down by query category tag
   - And: Results are saved to `prototype/data/benchmark/results.json` with full per-query details
   - And: A human-readable summary is printed to console

4. **AC-0.4.4**: Comparison: hybrid vs vector-only vs keyword-only
   - Given: The benchmark has been executed for all three search methods
   - When: The developer compares results
   - Then: A comparison table shows Hit@1, Hit@5, MRR for each method:
     - **Vector-only** (dense semantic search — already exists from Story 0.3)
     - **Keyword-only** (sparse/BM25 search)
     - **Hybrid** (dense + sparse with fusion)
   - And: Per-category breakdown shows which method wins for each query type
   - And: Latency comparison (avg/p95 response time per method)

5. **AC-0.4.5**: GO/NO-GO decision documented based on results
   - Given: All benchmark results are available
   - When: The developer documents the decision in `prototype/README.md`
   - Then: A "Benchmark Results & Decision" section documents:
     - Summary results table (the 3-method comparison)
     - Per-category analysis (which query types are strong/weak)
     - The GO/NO-GO decision with rationale
     - Recommended search strategy for production (hybrid fusion method, weights, fallbacks)
     - Known limitations and what to address in the Python/LangGraph build
   - And: **GO threshold**: Hit@5 ≥ 80% on hybrid search across all categories. If below, document why and what needs improvement.

## Tasks / Subtasks

- [x] Task 1: Extend Qdrant collection with sparse vectors for BM25 (AC: #1)
  - [x] 1.1: Update `prototype/scripts/generate-embeddings.py` to generate BOTH dense AND sparse vectors using BGE-M3's multi-retrieval capability (`model.encode(texts, return_sparse=True)` via FlagEmbedding) OR use a separate BM25 sparse tokenizer
  - [x] 1.2: Recreate the Qdrant `products` collection with `vectors_config` for dense (1024 dims, cosine) AND `sparse_vectors_config` for sparse (with `Modifier.IDF` for server-side BM25 IDF)
  - [x] 1.3: Upsert all products with both dense and sparse vectors + full payload
  - [x] 1.4: Verify collection has both vector types via Qdrant dashboard or API

- [x] Task 2: Implement hybrid search script (AC: #1)
  - [x] 2.1: Create `prototype/scripts/hybrid-search.py` with three search functions: `search_dense()`, `search_sparse()`, `search_hybrid()`
  - [x] 2.2: `search_dense()`: reuse existing semantic search logic (query → BGE-M3 dense embedding → Qdrant nearest neighbors)
  - [x] 2.3: `search_sparse()`: query → sparse vector (BM25 tokenization) → Qdrant sparse vector search
  - [x] 2.4: `search_hybrid()`: use Qdrant Query API with `prefetch` for both dense and sparse retrieval, fused via RRF (Reciprocal Rank Fusion)
  - [x] 2.5: Add exact reference matching: if query matches a `default_code` pattern (regex), prepend a payload filter search before vector search
  - [x] 2.6: Each function returns results as `[{id, name, default_code, score, rank}]`

- [x] Task 3: Create benchmark test query dataset (AC: #2)
  - [x] 3.1: Create `prototype/data/benchmark/test_queries.json` with 20+ test queries
  - [x] 3.2: Each query has: `query`, `expected_product_ids` (list of acceptable correct IDs), `category` tag
  - [x] 3.3: To build ground truth: use `products_raw.json` to identify specific product IDs for each query — manually verify by inspecting catalog data
  - [x] 3.4: Ensure coverage of all 9 category tags (at least 2 each): standard, abbreviation, jargon, exact-ref, typo, cross-lingual, custom-product, multi-word, technical-spec

- [x] Task 4: Create benchmark runner script (AC: #3, #4)
  - [x] 4.1: Create `prototype/scripts/run-benchmark.py` that loads test queries, runs all 3 search methods, computes metrics
  - [x] 4.2: Compute per-query: rank of correct product (or -1 if not in top-K), response time
  - [x] 4.3: Compute aggregate metrics: Hit@1, Hit@5, MRR — overall and per category
  - [x] 4.4: Generate comparison table (hybrid vs vector-only vs keyword-only)
  - [x] 4.5: Save full results to `prototype/data/benchmark/results.json`
  - [x] 4.6: Print human-readable summary with colored output (green ≥ 80%, yellow 60-80%, red < 60%)

- [x] Task 5: Documentation and GO/NO-GO decision (AC: #5)
  - [x] 5.1: Update `prototype/README.md` with "Story 0.4 — Hybrid Search Benchmark" section
  - [x] 5.2: Document benchmark methodology, results summary table, per-category analysis
  - [x] 5.3: Document GO/NO-GO decision with rationale
  - [x] 5.4: Document recommended search strategy for the Python/LangGraph production build

## Dev Notes

### Critical: This is the #1 Technical Risk Validation

The entire project hinges on this question: **can hybrid search match products accurately on raw, uncleaned catalog data?** If this fails, the "zero-preprocessing" promise (PRD FR5, FR9) is invalid and the project needs a fundamentally different approach. The GO/NO-GO decision at the end of this story determines whether we proceed to Epic 1 (Python build) or pivot.

### Hybrid Search Strategy: BGE-M3 Dense + Sparse

**Key insight**: BGE-M3 (already used in Story 0.3 for dense embeddings) natively supports **three retrieval modes**: dense, sparse (lexical weights), and ColBERT multi-vector. This means we can potentially use the SAME model for both dense and sparse vectors.

**Option A — BGE-M3 sparse retrieval (recommended to try first):**
```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
output = model.encode(texts, return_dense=True, return_sparse=True)
dense_embeddings = output["dense_vecs"]  # shape (n, 1024)
sparse_embeddings = output["lexical_weights"]  # list of dicts {token_id: weight}
```

**Note**: This requires `pip install FlagEmbedding` instead of (or in addition to) `sentence-transformers`. The `FlagEmbedding` library provides the multi-retrieval interface. Check if `sentence-transformers` also exposes sparse retrieval for BGE-M3 — if not, switch to `FlagEmbedding`.

**Option B — Separate BM25 tokenizer (fallback):**
If BGE-M3 sparse mode doesn't work well on dirty French catalog data, use a simple BM25 approach:
```python
# Use fastembed or a manual BM25 tokenizer
from fastembed import SparseTextEmbedding
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
```

The `Qdrant/bm25` model is purpose-built for use with Qdrant's server-side IDF. It provides term frequency vectors, and Qdrant applies IDF automatically.

**Important**: Whichever option you use, the Qdrant collection must be configured with `sparse_vectors_config` including `Modifier.IDF` for server-side IDF computation.

### Qdrant Collection Setup for Hybrid

The existing `products` collection (from Story 0.3) has dense vectors only. You need to **recreate** it with both vector types:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, SparseVectorParams, Distance, Modifier, PointStruct, SparseVector
)

client = QdrantClient(host="localhost", port=6333)

# Recreate collection with dense + sparse vectors
client.recreate_collection(
    collection_name="products",
    vectors_config={
        "dense": VectorParams(size=1024, distance=Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams(modifier=Modifier.IDF),
    },
)

# Upsert with both vectors
client.upsert(
    collection_name="products",
    points=[
        PointStruct(
            id=product["id"],
            vector={
                "dense": dense_embedding.tolist(),
            },
            payload=product,
        )
        for product, dense_embedding in zip(products, dense_embeddings)
    ],
)
# Sparse vectors upserted separately or together depending on format
```

**Note**: `recreate_collection` is deprecated in newer qdrant-client versions. Story 0.3 already fixed this — use `collection_exists()` + `delete_collection()` + `create_collection()` pattern instead.

### Qdrant Hybrid Search with Query API

Use Qdrant's `query_points` with `prefetch` for hybrid retrieval:

```python
from qdrant_client.models import Prefetch, FusionQuery, Fusion

results = client.query_points(
    collection_name="products",
    prefetch=[
        Prefetch(
            query=dense_query_vector,  # dense embedding of query
            using="dense",
            limit=20,
        ),
        Prefetch(
            query=SparseVector(indices=sparse_indices, values=sparse_values),
            using="sparse",
            limit=20,
        ),
    ],
    query=FusionQuery(fusion=Fusion.RRF),  # Reciprocal Rank Fusion
    limit=10,
)
```

**Fusion options to benchmark:**
- **RRF (Reciprocal Rank Fusion)**: Rank-based, robust to score scale differences. Good default.
- **DBSF (Distribution-Based Score Fusion)**: Normalizes scores based on distribution. May work better when score distributions differ significantly.

Try RRF first — it's the most commonly recommended for hybrid search.

### Exact Reference Matching

Some queries will contain exact product references (e.g., "TUBE-INOX-304L-25x1.5-6M" or "BLN-HM-8.8-M12x60"). Before running vector search, check if the query matches a `default_code` pattern and do a direct payload filter search:

```python
def search_exact_ref(client, query: str, collection_name="products"):
    """Try exact reference match via payload filter."""
    results = client.scroll(
        collection_name=collection_name,
        scroll_filter=models.Filter(
            should=[
                models.FieldCondition(
                    key="default_code",
                    match=models.MatchValue(value=query.strip()),
                ),
                models.FieldCondition(
                    key="default_code",
                    match=models.MatchValue(value=query.upper().strip()),
                ),
            ]
        ),
        limit=5,
    )
    return results
```

This provides a fast, deterministic match for exact reference queries — no embedding needed.

### Building the Test Query Dataset

The test queries must have **ground truth** — you must know which product ID(s) are correct for each query. To build this:

1. Load `prototype/data/catalog/products_raw.json`
2. Browse the product list to identify specific products for each test scenario
3. Note the product `id` (Odoo integer ID) for each expected match
4. Some queries may have multiple acceptable answers (e.g., abbreviation queries where multiple variants exist)

**Example test query format:**
```json
[
  {
    "query": "tube acier inoxydable 304L diamètre 25",
    "expected_product_ids": [142, 145],
    "category": "standard",
    "notes": "Products 142 and 145 are both 304L tubes with 25mm diameter variants"
  },
  {
    "query": "BLN-HM-8.8-M12x60",
    "expected_product_ids": [87],
    "category": "exact-ref",
    "notes": "Exact default_code match"
  }
]
```

**Important**: The product IDs depend on the seeded catalog. Run `seed-catalog.py` + `ingest-catalog.json` + inspect `products_raw.json` to identify real product IDs. The IDs are Odoo-assigned and will differ between fresh seeds.

**Workaround for dynamic IDs**: Instead of hardcoding IDs, you can use `default_code` or partial `name` match as ground truth identifiers. The benchmark script can resolve these to IDs at runtime by searching the payload.

### Dependencies Update

Add to `prototype/requirements.txt`:
```
requests
sentence-transformers
qdrant-client
FlagEmbedding
```

`FlagEmbedding` is needed for BGE-M3 sparse retrieval mode. If using `Qdrant/bm25` instead, add `fastembed`:
```
fastembed
```

### Metrics Calculation

```python
def hit_at_k(results, expected_ids, k):
    """Returns 1 if any expected ID is in top-k results, 0 otherwise."""
    top_k_ids = [r["id"] for r in results[:k]]
    return 1 if any(eid in top_k_ids for eid in expected_ids) else 0

def reciprocal_rank(results, expected_ids):
    """Returns 1/rank of first correct result, or 0 if not found."""
    for i, r in enumerate(results):
        if r["id"] in expected_ids:
            return 1.0 / (i + 1)
    return 0.0
```

### Performance Expectations

Based on Story 0.3 results:
- Dense search: ~91ms avg per query (already validated)
- Sparse search: should be similar or faster (inverted index)
- Hybrid search: slightly slower due to fusion (expect 100-200ms)
- All should be well under the 3s architecture target

### Gotchas to Avoid

1. **Do NOT clean the catalog data** — the benchmark must test on raw data (zero-preprocessing validation)
2. **Do NOT use OpenAI or external API for embeddings** — architecture specifies local model
3. **Do NOT hardcode product IDs** without verifying against the actual seeded catalog — IDs change between seeds
4. **BGE-M3 sparse mode via `FlagEmbedding`** requires different import than `sentence-transformers` — test this early
5. **Qdrant sparse vector format**: indices must be sorted and values must be non-zero. Check the sparse output format carefully
6. **`Modifier.IDF`** on the sparse vector config is critical — without it, BM25 term frequencies won't be weighted by document rarity
7. **RRF fusion in Qdrant** uses the `FusionQuery` class — check qdrant-client version supports this (should be fine with recent versions)
8. **Memory**: Loading BGE-M3 for both dense + sparse may require more RAM than dense-only. Ensure sufficient memory (6 GB+ free recommended)
9. **Product `False` values**: Odoo returns `False` for empty fields — already handled in Story 0.3's `build_product_text()`, reuse that pattern
10. **The benchmark tests PROTOTYPE feasibility** — the production build (Epic 3) will use pgvector + PostgreSQL tsvector, not Qdrant. The goal here is to validate that hybrid search works on dirty data, not to build the production search engine

### Project Structure Notes

New files under `prototype/`:
```
prototype/
├── scripts/
│   ├── generate-embeddings.py     (MODIFIED — add sparse vectors)
│   ├── hybrid-search.py           (NEW — hybrid search functions)
│   └── run-benchmark.py           (NEW — benchmark runner)
├── data/
│   └── benchmark/
│       ├── test_queries.json      (NEW — ground truth test queries)
│       └── results.json           (NEW — benchmark results output)
├── requirements.txt               (MODIFIED — add FlagEmbedding or fastembed)
└── README.md                      (MODIFIED — add benchmark section)
```

No conflict with the architecture's `src/` structure — prototype is isolated.

### Previous Story Intelligence

From **Story 0.3** implementation:
- **BGE-M3 with sentence-transformers**: Works for dense retrieval. For sparse, may need `FlagEmbedding` library instead
- **Qdrant `recreate_collection` deprecation**: Already fixed to use `collection_exists()` check pattern — reuse this approach when recreating with sparse+dense config
- **`build_product_text()`**: Concatenates raw fields with `|` separator — reuse this exact function for both dense embedding text and sparse tokenization input
- **n8n output format handling**: `products_raw.json` may be `[{"products": [...]}]` — `load_products()` already handles this
- **Batch processing**: 32 products per batch works for dense BGE-M3 encoding. May need adjustment for combined dense+sparse
- **Embedding time**: ~126s for 726 products (dense only, CPU). Expect longer for dense+sparse combined
- **Code review fixes applied**: Batch upsert for memory efficiency, improved error messages, multi-query arg support

### Git Intelligence

Recent commits:
- `8b8bf31` — Story 0.3: generate-embeddings.py, test-semantic-search.py, docker-compose (Qdrant), requirements.txt, README
- `ddd9e53` — Story 0.2: seed-catalog.py, ingest-catalog.json, docker-compose volume mount, README
- `34866aa` — Story 0.1: Docker environment with n8n + Odoo

Pattern: each story commits all new/modified files together with a descriptive `feat:` message.

### Latest Technical Information

**Qdrant Hybrid Search (Query API)**:
- Qdrant's Query API supports `prefetch` for multi-source retrieval with server-side fusion
- Fusion methods: RRF (Reciprocal Rank Fusion), DBSF (Distribution-Based Score Fusion)
- Server-side IDF computation via `Modifier.IDF` on sparse vector config — no client-side IDF calculation needed
- The `Qdrant/bm25` model on HuggingFace is designed for use with Qdrant's server-side IDF

**BGE-M3 Multi-Retrieval**:
- Supports dense (1024 dims) + sparse (lexical weights) + ColBERT in a single `encode()` call via `FlagEmbedding`
- Sparse output: dict of `{token_id: weight}` per text
- The sparse mode computes learned lexical weights (not classical BM25) — may outperform traditional BM25 for semantic-aware keyword matching
- According to the BGE-M3 paper, sparse retrieval outperforms dense by 10 points on long documents

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 0, Story 0.4]
- [Source: _bmad-output/planning-artifacts/architecture.md - Search Strategy: Hybrid pgvector semantic + PostgreSQL tsvector keyword]
- [Source: _bmad-output/planning-artifacts/architecture.md - Embedding Model: BGE-M3 or multilingual-e5-large, local multilingual]
- [Source: _bmad-output/planning-artifacts/architecture.md - Vector Index: HNSW, Performance: search < 3s]
- [Source: _bmad-output/planning-artifacts/prd.md - FR5 (semantic + exact ref on raw catalogs), FR9 (zero-preprocessing), Prototype Phase validation]
- [Source: _bmad-output/implementation-artifacts/0-3-generation-embeddings-index-vectoriel.md - BGE-M3 setup, Qdrant integration, build_product_text(), batch processing patterns]
- [Qdrant Hybrid Search - Query API](https://qdrant.tech/articles/hybrid-search/) — Prefetch + fusion architecture
- [Qdrant Sparse Vectors](https://qdrant.tech/articles/sparse-vectors/) — BM25 sparse vector implementation
- [Qdrant/bm25 on HuggingFace](https://huggingface.co/Qdrant/bm25) — Purpose-built BM25 model for Qdrant
- [Qdrant 1.10 - Built-in IDF](https://qdrant.tech/blog/qdrant-1.10.x/) — Server-side IDF computation
- [BAAI/bge-m3 on HuggingFace](https://huggingface.co/BAAI/bge-m3) — Dense + sparse + ColBERT multi-retrieval
- [BGE-M3 Documentation](https://bge-model.com/bge/bge_m3.html) — FlagEmbedding usage for sparse retrieval

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- FlagEmbedding import error (`is_torch_fx_available` removed from transformers). Switched to fastembed (Qdrant/bm25) for sparse vectors as per Dev Notes fallback option.
- test-semantic-search.py required `using="dense"` parameter after collection migration to named vectors.

### Completion Notes List

- **Task 1**: Updated generate-embeddings.py to produce both dense (BGE-M3 via sentence-transformers) and sparse (BM25 via fastembed/Qdrant/bm25) vectors. Collection recreated with `vectors_config.dense` + `sparse_vectors_config.sparse` (with Modifier.IDF). 726 products indexed with both vector types.
- **Task 2**: Created hybrid-search.py with `search_dense()`, `search_sparse()`, `search_hybrid()` functions. Hybrid uses Qdrant Query API with prefetch + RRF fusion. Exact reference matching via payload filter on `default_code` for code-like queries.
- **Task 3**: Created test_queries.json with 26 queries across all 9 categories (2+ per category). Ground truth uses `expected_default_codes` and `expected_names` resolved to IDs at runtime for seed-independence.
- **Task 4**: Created run-benchmark.py computing Hit@1, Hit@5, MRR per method and per category, with latency tracking and colored output. Results saved to results.json.
- **Task 5**: Updated README.md with full benchmark results, GO/NO-GO decision (GO — 96.2% Hit@5), recommended production search strategy, and known limitations.
- **Regression fix**: Updated test-semantic-search.py to use `using="dense"` for named vector compatibility.

**GO DECISION**: Hybrid Hit@5 = 96.2% (threshold 80%). Zero-preprocessing validated on raw catalog. All categories except cross-lingual achieve 100%.

### Change Log

- 2026-03-16: Story 0.4 implementation complete — hybrid search benchmark with GO decision
- 2026-03-16: Code review fixes applied — removed dead import (run-benchmark.py), consistent collection_name parameterization (hybrid-search.py), updated README Story 0.3 section for hybrid collection

### File List

- `prototype/scripts/generate-embeddings.py` — MODIFIED: added sparse BM25 vectors (fastembed), named vector config, dual upsert
- `prototype/scripts/hybrid-search.py` — NEW: hybrid search with dense, sparse, hybrid (RRF), and exact-ref matching
- `prototype/scripts/run-benchmark.py` — NEW: benchmark runner with metrics computation and comparison
- `prototype/scripts/test-semantic-search.py` — MODIFIED: added `using="dense"` for named vector compatibility
- `prototype/data/benchmark/test_queries.json` — NEW: 26 ground truth test queries across 9 categories
- `prototype/data/benchmark/results.json` — NEW: full benchmark results output
- `prototype/requirements.txt` — MODIFIED: added `fastembed` dependency
- `prototype/README.md` — MODIFIED: added Story 0.4 benchmark section with results and GO/NO-GO decision
- `_bmad-output/implementation-artifacts/0-4-recherche-hybride-benchmark-accuracy.md` — MODIFIED: story file updates
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED: story status updates
