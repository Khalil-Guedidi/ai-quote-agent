# Story 3.3: Recherche Hybride (Sémantique + Mot-Clé)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to search products using both semantic understanding and exact reference matching,
So that it finds the right product whether I describe it in natural language or use a catalog code.

## Acceptance Criteria

1. **AC-1: Hybrid search combining semantic + keyword**
   - Given a search query like "tubes inox 304L Ø25 lg 6m"
   - When hybrid search runs
   - Then it returns the correct product even if the catalog entry reads "TUBE ROND SS 304L 25x1.5 LONGUEUR 6000mm"
   - And the search combines pgvector semantic similarity with PostgreSQL tsvector keyword/exact matching
   - And results are ranked using Reciprocal Rank Fusion (RRF) of both signals

2. **AC-2: Exact reference match prioritization**
   - Given a search with an exact product reference (e.g., "REF-12345" or "TUB-304L-025")
   - When the search runs
   - Then the exact reference match is prioritized over semantic results (score = 1.0)
   - And partial reference matches also boost keyword ranking

3. **AC-3: Jargon and abbreviation handling via semantic search**
   - Given a search query with client jargon or abbreviations (e.g., "inox" for "acier inoxydable", "Ø" for diameter)
   - When the search runs
   - Then semantic understanding handles jargon without requiring manual synonym configuration
   - And the multilingual embedding model (BGE-M3) handles cross-language matching (French + technical English)

4. **AC-4: Performance < 3 seconds**
   - Given 50,000 products are indexed (HNSW vector index + GIN tsvector index)
   - When a hybrid search query executes
   - Then results are returned within 3 seconds (NFR-P2)
   - And structured logging reports query duration, result count, and search method used

5. **AC-5: E2E test with real PostgreSQL + real embedding model**
   - Given products from `tests/fixtures/catalog_50k_sample.jsonl` are inserted and embedded
   - When hybrid search runs for "tubes inox 304L"
   - Then semantically relevant products are returned (e.g., "TUBE ROND SS 304L...")
   - And exact reference search for a known reference returns that product first
   - And keyword search for a category term returns relevant products

## Tasks / Subtasks

- [x] Task 1: Add tsvector column + GIN index via Alembic migration (AC: 1, 4)
  - [x] 1.1: Create migration: add `search_vector` column of type `tsvector` to `products` table
  - [x] 1.2: Populate `search_vector` from existing data: `to_tsvector('french', coalesce(name,'') || ' ' || coalesce(reference,'') || ' ' || coalesce(category,'') || ' ' || coalesce(description,''))`
  - [x] 1.3: Create GIN index: `CREATE INDEX ix_products_search_vector_gin ON products USING gin(search_vector)`
  - [x] 1.4: Create trigger to keep `search_vector` in sync on INSERT/UPDATE
  - [x] 1.5: Downgrade: drop trigger, drop index, drop column

- [x] Task 2: Update Product model with `search_vector` column (AC: 1)
  - [x] 2.1: Add `search_vector` column to `Product` model in `models/product.py` — `Mapped[Optional[str]]` mapped to `TSVECTOR` column type, not directly queryable as Python field (DB-managed via trigger)
  - [x] 2.2: Ensure `search_vector` is excluded from normal serialization (it's DB-internal)

- [x] Task 3: Add `SearchSettings` to configuration (AC: 4)
  - [x] 3.1: Add `SearchSettings` to `config.py`: `default_limit` (int, default `10`), `semantic_weight` (float, default `0.5`), `keyword_weight` (float, default `0.5`), `rrf_k` (int, default `60`), `hnsw_ef_search` (int, default `100`)
  - [x] 3.2: Add `search: SearchSettings` field to `Settings`
  - [x] 3.3: Verify env var mapping: `SEARCH__DEFAULT_LIMIT`, `SEARCH__SEMANTIC_WEIGHT`, etc.

- [x] Task 4: Implement `search/vector.py` — semantic search module (AC: 1, 3)
  - [x] 4.1: Create `src/quote_agent/search/vector.py` with `async search_semantic(session, query_embedding, limit) -> list[ScoredProduct]`
  - [x] 4.2: Query: `SELECT *, (vector <=> :query_vector) AS distance FROM products WHERE vector IS NOT NULL AND is_stale = False ORDER BY distance LIMIT :limit`
  - [x] 4.3: Convert cosine distance to similarity score: `score = 1.0 - distance`
  - [x] 4.4: Set `hnsw.ef_search` before query for better recall: `SET LOCAL hnsw.ef_search = :ef_search`

- [x] Task 5: Implement `search/keyword.py` — tsvector keyword search module (AC: 1, 2)
  - [x] 5.1: Create `src/quote_agent/search/keyword.py` with `async search_keyword(session, query_text, limit) -> list[ScoredProduct]`
  - [x] 5.2: Build tsquery from user input: `plainto_tsquery('french', :query)` for natural language, `to_tsquery('french', :query)` for structured
  - [x] 5.3: Score with `ts_rank_cd(search_vector, tsquery)` (cover density ranking — better for short document fields)
  - [x] 5.4: Implement exact reference matching: `async search_exact_ref(session, query_text) -> list[ScoredProduct]` — `WHERE reference ILIKE :query` with score = 1.0
  - [x] 5.5: Detect if query looks like a reference code using regex pattern from prototype: `r"^[A-Z]{2,6}[-_][A-Z0-9.²]+(?:[-_][A-Z0-9.²x]+)*$"`

- [x] Task 6: Implement `search/models.py` — search DTOs (AC: 1)
  - [x] 6.1: Create `SearchRequest` DTO: `query` (str), `limit` (int, default 10), `include_stale` (bool, default False)
  - [x] 6.2: Create `ScoredProduct` DTO: `product_id` (UUID), `reference` (str), `name` (str), `category` (str), `description` (Optional[str]), `unit_price` (float), `score` (float), `rank` (int), `match_source` (Literal["semantic", "keyword", "exact_ref", "hybrid"])
  - [x] 6.3: Create `SearchResult` DTO: `results` (list[ScoredProduct]), `total_found` (int), `query` (str), `method` (str), `duration_seconds` (float)

- [x] Task 7: Implement `search/engine.py` — hybrid search orchestration with RRF (AC: 1, 2, 3, 4)
  - [x] 7.1: Create `src/quote_agent/search/engine.py` with `SearchEngine` class
  - [x] 7.2: Constructor takes `AsyncSession` and `EmbeddingAdapter` (dependency injection)
  - [x] 7.3: Implement `async search_hybrid(request: SearchRequest) -> SearchResult`:
    1. Check if query matches reference code pattern → if so, try exact ref match first; if found, return immediately
    2. Generate query embedding via `EmbeddingAdapter.embed_texts([query])`
    3. Run semantic search (`search_semantic`) and keyword search (`search_keyword`) concurrently with `asyncio.gather`
    4. Fuse results using Reciprocal Rank Fusion (RRF): `score = sum(1 / (k + rank_i))` for each result across both ranked lists
    5. Sort by fused score descending, assign final ranks, return top `limit` results
  - [x] 7.4: Implement `async search_semantic_only(request: SearchRequest) -> SearchResult` — exposes vector search alone
  - [x] 7.5: Implement `async search_keyword_only(request: SearchRequest) -> SearchResult` — exposes keyword search alone
  - [x] 7.6: Structured logging: query, method, result count, duration. Component: `search.engine`

- [x] Task 8: Update `search/__init__.py` — public API (AC: 1)
  - [x] 8.1: Export `SearchEngine`, `SearchRequest`, `SearchResult`, `ScoredProduct`
  - [x] 8.2: Add `get_search_engine(session: AsyncSession) -> SearchEngine` convenience factory

- [x] Task 9: Unit tests (AC: 1, 2, 3, 4)
  - [x] 9.1: Test RRF fusion: two ranked lists → verify fused scores and ordering are correct
  - [x] 9.2: Test exact reference detection: regex matches "TUB-304L-025", "BHM-M12x60", doesn't match "tubes inox"
  - [x] 9.3: Test `search_hybrid` orchestration: mock embedding adapter + mock session, verify exact ref path vs hybrid path
  - [x] 9.4: Test `search_semantic_only` and `search_keyword_only` paths
  - [x] 9.5: Test `SearchSettings` defaults and env overrides
  - [x] 9.6: Test `ScoredProduct` and `SearchResult` DTO construction
  - [x] 9.7: Test edge cases: empty query, no results, all results from one source only

- [x] Task 10: E2E test with real PostgreSQL + real embedding model (AC: 5)
  - [x] 10.1: E2E test: insert products from `catalog_50k_sample.jsonl`, run `embed_all()`, then `search_hybrid("tubes inox 304L")` → verify semantically relevant products returned
  - [x] 10.2: E2E test: exact reference search for a known reference from the fixture → verify it's returned first with score ~1.0
  - [x] 10.3: E2E test: keyword search for category term (e.g., "Tubes & Tuyaux") → verify relevant products returned
  - [x] 10.4: E2E test: verify tsvector column is populated (non-null) for all inserted products
  - [x] 10.5: Cleanup: delete test products after tests

## Dev Notes

### Critical: Architecture-Mandated File Structure

The architecture document defines the search module structure explicitly:

```
src/quote_agent/search/
├── __init__.py      # Public API exports + convenience factory
├── engine.py        # Hybrid search orchestration (vector + keyword + RRF)
├── vector.py        # pgvector semantic search operations
├── keyword.py       # PostgreSQL tsvector full-text search
└── models.py        # SearchRequest, ScoredProduct, SearchResult DTOs
```

**This is NOT an adapter** — search is internal infrastructure (no external service), so it lives in `search/` not `adapters/search/`. The `search/` directory already exists with an empty `__init__.py`.

### Technical Requirements

**tsvector for French full-text search:**
```sql
-- Column populated via trigger on INSERT/UPDATE
search_vector = to_tsvector('french',
    coalesce(name, '') || ' ' ||
    coalesce(reference, '') || ' ' ||
    coalesce(category, '') || ' ' ||
    coalesce(description, '')
)
```
- Use `'french'` text search configuration — handles French stemming (e.g., "inoxydable" → "inoxydabl")
- `coalesce()` prevents NULL propagation breaking the entire tsvector
- GIN index for fast lookup: `CREATE INDEX ix_products_search_vector_gin ON products USING gin(search_vector)`

**Keyword query construction:**
```python
# Natural language query (user input)
tsquery = func.plainto_tsquery('french', query_text)
# Ranking with cover density (better for short fields like product names)
score = func.ts_rank_cd(Product.search_vector, tsquery)
```

**Reciprocal Rank Fusion (RRF) — proven in prototype:**
```python
def _rrf_fuse(
    semantic_results: list[ScoredProduct],
    keyword_results: list[ScoredProduct],
    k: int = 60,
) -> list[ScoredProduct]:
    """Fuse two ranked lists using RRF. k=60 is standard default."""
    scores: dict[UUID, float] = {}
    products: dict[UUID, ScoredProduct] = {}
    for rank, item in enumerate(semantic_results, start=1):
        scores[item.product_id] = scores.get(item.product_id, 0) + 1.0 / (k + rank)
        products[item.product_id] = item
    for rank, item in enumerate(keyword_results, start=1):
        scores[item.product_id] = scores.get(item.product_id, 0) + 1.0 / (k + rank)
        products[item.product_id] = item
    sorted_ids = sorted(scores, key=lambda pid: scores[pid], reverse=True)
    return [
        products[pid].model_copy(update={"score": scores[pid], "rank": i + 1, "match_source": "hybrid"})
        for i, pid in enumerate(sorted_ids)
    ]
```

**Exact reference detection — regex from prototype:**
```python
REF_CODE_PATTERN = re.compile(
    r"^[A-Z]{2,6}[-_][A-Z0-9.²]+(?:[-_][A-Z0-9.²x]+)*$", re.IGNORECASE
)
```
When query matches this pattern, try exact `reference ILIKE :query` first. If match found, return immediately (score=1.0) — no need for semantic search.

**pgvector semantic search:**
```python
# Set higher ef_search for better recall (default 40, use 100)
await session.execute(text("SET LOCAL hnsw.ef_search = :ef"), {"ef": settings.search.hnsw_ef_search})
# Cosine distance query — vector <=> is the cosine distance operator
stmt = (
    select(Product, (Product.vector.cosine_distance(query_vector)).label("distance"))
    .where(Product.vector.isnot(None), Product.is_stale == False)
    .order_by("distance")
    .limit(limit)
)
```
Convert distance to score: `score = 1.0 - distance` (cosine distance ∈ [0, 2] for normalized vectors, typically [0, 1]).

**Concurrent execution — run both searches in parallel:**
```python
semantic_task = search_semantic(session, query_embedding, limit=prefetch_limit)
keyword_task = search_keyword(session, query_text, limit=prefetch_limit)
semantic_results, keyword_results = await asyncio.gather(semantic_task, keyword_task)
```
Use `prefetch_limit = limit * 2` (fetch more candidates for better RRF fusion, then trim to `limit`).

### Architecture Compliance

**Search module is NOT an adapter:**
- No Protocol needed — search is internal, not an external integration
- No factory with `@lru_cache` needed — `SearchEngine` is instantiated per-request with a session
- DTOs go in `search/models.py` (Pydantic BaseModel, same pattern as adapter DTOs)

**SearchEngine constructor — dependency injection:**
```python
class SearchEngine:
    def __init__(self, session: AsyncSession, embedding_adapter: EmbeddingAdapter) -> None:
        self._session = session
        self._embedding = embedding_adapter
        self._settings = get_settings().search
```

**Naming conventions (PEP 8 strict):**
- Files: `engine.py`, `vector.py`, `keyword.py`, `models.py`
- Classes: `SearchEngine`, `ScoredProduct`, `SearchResult`, `SearchRequest`
- Functions: `search_hybrid()`, `search_semantic()`, `search_keyword()`, `_rrf_fuse()`
- Constants: `REF_CODE_PATTERN`, `_PREFETCH_MULTIPLIER = 2`

**Imports:** Absolute only — `from quote_agent.search.vector import search_semantic`

**Type safety:** `from __future__ import annotations` in every file. All functions typed. `mypy --strict` must pass.

**Structured logging:**
```python
logger.info(
    "Hybrid search completed",
    extra={"context": {"query": query, "method": "hybrid", "results": len(results), "duration_s": elapsed}},
)
```
Component: `search.engine`. Never `print()`.

### Library & Framework Requirements

- **No new dependencies.** pgvector, SQLAlchemy, sentence-transformers, Alembic, pydantic all already installed.
- PostgreSQL `tsvector`, `tsquery`, `ts_rank_cd`, `plainto_tsquery` are built-in — no extension needed.
- `pgvector` extension already enabled (migration `c740a66c4ad2`).
- Do NOT install `fastembed` or `qdrant-client` — those were prototype-only. Production uses PostgreSQL tsvector for keyword search, not sparse vectors.

### File Structure Requirements

**New files:**
- `src/quote_agent/search/models.py` — SearchRequest, ScoredProduct, SearchResult DTOs
- `src/quote_agent/search/vector.py` — `search_semantic()` function
- `src/quote_agent/search/keyword.py` — `search_keyword()`, `search_exact_ref()`, `is_reference_code()` functions
- `src/quote_agent/search/engine.py` — `SearchEngine` class with hybrid orchestration
- `alembic/versions/xxxx_add_tsvector_and_gin_index.py` — migration
- `tests/unit/test_search_engine.py` — unit tests for search engine + RRF
- `tests/unit/test_search_keyword.py` — unit tests for keyword search + reference detection
- `tests/e2e/test_search_e2e.py` — E2E tests

**Modified files:**
- `src/quote_agent/search/__init__.py` — add exports + factory
- `src/quote_agent/config.py` — add `SearchSettings`
- `src/quote_agent/models/product.py` — add `search_vector` column mapping
- `tests/e2e/conftest.py` — add `get_embedding_adapter` clearing if not already present

### Testing Requirements

**Unit tests (no DB, no real model):**
- Mock `EmbeddingAdapter` — return fake query embedding of correct shape `(1, 1024)`
- Mock `AsyncSession` for DB operations — return fake `ScoredProduct` rows
- Test RRF fusion logic exhaustively: overlapping results, disjoint results, single-source results
- Test reference code regex: positive matches (TUB-304L-025, BHM-M12x60, TCA_10mm), negative matches ("tubes inox", "hello", "12345")
- Test naming: `test_{behavior}_when_{condition}()` e.g., `test_exact_ref_returned_first_when_reference_code_query()`
- Docstrings: `"""AC-1: ..."""`

**E2E tests (real PostgreSQL + real embedding model):**
- Mark with `@pytest.mark.e2e`
- Use `requires_e2e` skip decorator
- Insert products from `catalog_50k_sample.jsonl` into real PostgreSQL
- Run `embed_all()` to populate vector column (reuse from Story 3.2 E2E pattern)
- Verify tsvector column populated via trigger
- Run hybrid search, verify semantic relevance
- Run exact ref search, verify prioritization
- Cleanup: delete test products after tests

### Previous Story Intelligence

**Story 3.2 (Embeddings & Vector Index — just completed):**
- `EmbeddingAdapter.embed_texts()` returns `list[list[float]]` — call with `[query_text]` to get query embedding
- `EmbeddingService.embed_all()` populates `Product.vector` column — reuse in E2E test setup
- HNSW index already created: `ix_products_vector_hnsw` with `vector_cosine_ops`, m=16, ef_construction=64
- `_build_product_text()` concatenates `name | Ref: reference | category | description` — same text used for embeddings, so semantic search quality depends on this format
- E2E test pattern: insert from `catalog_50k_sample.jsonl`, use `e2e_db_session` fixture, cleanup with marker prefix
- Vector dimension: 1024 (BGE-M3)
- Health check caching: 30s TTL with `time.monotonic()`
- Adapter factory: `get_embedding_adapter()` with `@lru_cache(maxsize=1)` — clear in E2E conftest

**Story 3.1 (Catalog Ingestion):**
- `Product` model has: `reference`, `name`, `description`, `category`, `unit_price`, `stock_status`, `is_active`, `is_stale`, `vector`, `metadata_`
- `is_stale = True` → product should NOT appear in search results (filtering on `is_stale = False`)
- `is_active` flag exists but proposability filtering is Story 3.4's job — for now just filter on `is_stale`

**Prototype (hybrid-search.py):**
- Prototype used Qdrant for both dense and sparse search — production replaces Qdrant with PostgreSQL (pgvector for dense, tsvector for sparse/keyword)
- RRF fusion logic is the same conceptually — just different data sources
- Reference code regex pattern: reuse from prototype, extended with `_` separator
- `DEFAULT_TOP_K = 10` — same default in production

### Git Intelligence

Recent commits:
- `045fd71` content: add search deep dive LinkedIn post (Story T.8)
- `08f9b54` feat: add embedding generation, HNSW vector index, and dimension validation (Story 3.2)
- `2c28257` feat: add ERP catalog ingestion with zero-preprocessing, re-sync, and stale detection (Story 3.1)

Story 3.2 just completed. HNSW index exists. Embedding adapter fully functional. All tests passing (258 unit + E2E).

### What NOT to Do

- Do NOT implement proposability filtering — that's Story 3.4.
- Do NOT implement caching — that's Story 3.5.
- Do NOT implement LLM-based re-ranking or jargon synonym tables — that's Story 3.6. Semantic search via BGE-M3 handles jargon naturally.
- Do NOT install `fastembed` or `qdrant-client` — production uses PostgreSQL tsvector, not Qdrant sparse vectors.
- Do NOT create a search adapter with Protocol/factory/lru_cache — search is internal infrastructure in `search/`, not an external integration.
- Do NOT add an API endpoint — the `SearchEngine` is consumed by the LangGraph agent node (Story 4.x), not directly via REST.
- Do NOT re-implement embedding generation — reuse `EmbeddingAdapter.embed_texts()` for query embedding.
- Do NOT use relative imports anywhere.
- Do NOT mock services in E2E tests — use ALL real services (PostgreSQL, embedding model).
- Do NOT use `ts_rank()` — use `ts_rank_cd()` (cover density ranking, better for short product name/description fields).
- Do NOT add `unaccent` extension or complex text normalization — French tsvector config handles stemming; semantic search handles the rest.

### Project Structure Notes

- Search module goes in `src/quote_agent/search/` — directory already exists with empty `__init__.py`
- DTOs in `search/models.py` — consistent with adapter DTOs pattern (Pydantic BaseModel)
- No conflicts with existing structure detected
- `search/cache.py` and `search/indexer.py` are NOT part of this story — those are Stories 3.5 and already covered by `CatalogService`/`EmbeddingService`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3] — acceptance criteria, semantic + keyword hybrid, reference matching, jargon handling, < 3s performance
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — "Hybrid: pgvector (semantic) + PostgreSQL tsvector (keyword/exact ref)"
- [Source: _bmad-output/planning-artifacts/architecture.md#Search Component] — engine.py, vector.py, keyword.py file structure
- [Source: _bmad-output/planning-artifacts/architecture.md#NFR-P2] — search < 3 seconds
- [Source: docs/project-context.md] — adapter pattern (NOT for search), naming conventions, test patterns, cache clearing, async patterns
- [Source: prototype/scripts/hybrid-search.py] — RRF fusion logic, reference code regex, search method structure
- [Source: src/quote_agent/models/product.py] — Product model with vector column, existing indexes
- [Source: src/quote_agent/adapters/embedding/] — EmbeddingAdapter protocol, embed_texts() for query embedding
- [Source: src/quote_agent/services/embedding_service.py] — embed_all() for E2E test setup, _build_product_text() pattern
- [Source: alembic/versions/78fc0a54b3b9_fix_vector_dim_1024_and_add_hnsw_index.py] — existing HNSW index migration
- [Source: tests/e2e/test_embedding_e2e.py] — E2E test patterns, cosine similarity query examples

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- asyncpg does not support parameterized `SET LOCAL` statements — used f-string with `int()` cast for safety
- asyncpg does not support concurrent queries on the same connection — changed `asyncio.gather()` to sequential execution for semantic + keyword search
- Pydantic requires `uuid` import at runtime even with `from __future__ import annotations` — added `noqa: TC003` comment

### Completion Notes List

- Alembic migration `06ad988234a0`: adds `search_vector` tsvector column, populates from existing data, creates GIN index, creates trigger for sync on INSERT/UPDATE
- Product model updated with `search_vector` column mapped to PostgreSQL TSVECTOR type
- `SearchSettings` added to config: `default_limit`, `semantic_weight`, `keyword_weight`, `rrf_k`, `hnsw_ef_search`
- `search/models.py`: SearchRequest, ScoredProduct, SearchResult DTOs
- `search/vector.py`: pgvector cosine distance search with HNSW ef_search tuning
- `search/keyword.py`: French tsvector full-text search with `ts_rank_cd`, exact reference matching with ILIKE, reference code regex detection
- `search/engine.py`: SearchEngine with hybrid (RRF fusion), semantic-only, keyword-only modes; structured logging
- `search/__init__.py`: public API exports + `get_search_engine()` factory
- 31 unit tests: RRF fusion, reference detection, search orchestration, DTOs, settings, edge cases
- 4 E2E tests: hybrid search, exact reference, keyword category, tsvector population verification
- All 289 unit tests pass, all 15/16 E2E tests pass (1 pre-existing flaky LLM splitting test)

### Change Log

- 2026-03-20: Story 3.3 implemented — hybrid search with semantic + keyword + RRF fusion
- 2026-03-20: Code review — 3 MEDIUM fixes applied: (1) removed spurious session.rollback() in E2E cleanup, (2) strengthened exact_ref E2E test to verify exact_ref code path + score=1.0, (3) documented unused semantic_weight/keyword_weight as reserved for future weighted RRF

### File List

**New files:**
- `alembic/versions/06ad988234a0_add_tsvector_search_vector_column_and_.py`
- `src/quote_agent/search/models.py`
- `src/quote_agent/search/vector.py`
- `src/quote_agent/search/keyword.py`
- `src/quote_agent/search/engine.py`
- `tests/unit/test_search_engine.py`
- `tests/unit/test_search_keyword.py`
- `tests/e2e/test_search_e2e.py`

**Modified files:**
- `src/quote_agent/search/__init__.py`
- `src/quote_agent/config.py`
- `src/quote_agent/models/product.py`
