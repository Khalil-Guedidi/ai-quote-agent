# Story 3.5: Cache de Résultats de Recherche

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want search results for recurring or similar requests cached,
So that repeated queries are answered faster and LLM costs are reduced.

## Acceptance Criteria

1. **AC-1: Cache hit returns results in < 1 second**
   - Given a search query has been executed before with identical parameters (query, limit, include_stale, apply_proposability_filter)
   - When the same query is submitted again within the TTL window
   - Then cached results are returned in < 1 second (NFR-P6)
   - And no embedding generation or DB search queries are executed for the cached response
   - And the response includes `from_cache=True` metadata

2. **AC-2: Cache miss executes fresh search and stores result**
   - Given a search query has not been cached or TTL has expired
   - When the query is submitted
   - Then a fresh search is executed normally
   - And the result is stored in the cache with a computed TTL
   - And `from_cache=False` in the response metadata

3. **AC-3: TTL expiry triggers fresh search**
   - Given a cached entry's TTL has expired
   - When the same query is submitted
   - Then a fresh search is executed and the cache is updated with a new TTL
   - And structured logging records the cache miss reason ("expired")

4. **AC-4: Cache invalidated on catalog re-sync**
   - Given the product catalog is re-ingested via `CatalogService.ingest_full()`
   - When ingestion completes successfully
   - Then ALL cache entries are invalidated (full flush)
   - And cache invalidation is logged with entry count removed

5. **AC-5: Cache can be disabled via configuration**
   - Given `SearchCacheSettings.enabled=False` (env: `SEARCH_CACHE__ENABLED=false`)
   - When a search is executed
   - Then no cache lookup or storage occurs
   - And search behaves exactly as before this story

6. **AC-6: Cache key is deterministic based on search parameters**
   - Given two identical SearchRequests (same query, limit, include_stale, apply_proposability_filter)
   - When both are hashed
   - Then they produce the same cache key
   - And changing any parameter produces a different key

7. **AC-7: E2E test with real PostgreSQL**
   - Given products are ingested and embedded
   - When hybrid search runs twice with the same query
   - Then the second call returns from cache (< 1 second, `from_cache=True`)
   - And after `invalidate_all()`, the next call is a cache miss
   - And with `enabled=False`, no cache interaction occurs

## Tasks / Subtasks

- [x] Task 1: Add `SearchCacheSettings` to configuration (AC: 5, 6)
  - [x] 1.1: Add `SearchCacheSettings` to `config.py`: `enabled` (bool, default `True`), `ttl_seconds` (int, default `3600`), `max_entries` (int, default `10000`)
  - [x] 1.2: Add `search_cache: SearchCacheSettings` field to `Settings`
  - [x] 1.3: Verify env var mapping: `SEARCH_CACHE__ENABLED`, `SEARCH_CACHE__TTL_SECONDS`, `SEARCH_CACHE__MAX_ENTRIES`

- [x] Task 2: Create `search_cache` table and Alembic migration (AC: 1, 2, 3)
  - [x] 2.1: Create `src/quote_agent/models/search_cache.py` with `SearchCache` SQLAlchemy model: `id` (UUID PK), `cache_key` (str, unique index), `query` (str), `search_params` (JSON — limit, include_stale, apply_proposability_filter), `results_json` (JSON — serialized SearchResult), `created_at` (timestamp), `expires_at` (timestamp, indexed)
  - [x] 2.2: Export `SearchCache` from `models/__init__.py`
  - [x] 2.3: Create Alembic migration for `search_cache` table with: unique index on `cache_key` (`ix_search_cache_cache_key`), index on `expires_at` (`ix_search_cache_expires_at`) for TTL cleanup queries

- [x] Task 3: Implement cache logic in `search/cache.py` (AC: 1, 2, 3, 4, 6)
  - [x] 3.1: Implement `compute_cache_key(request: SearchRequest) -> str` — deterministic SHA-256 hash of (query, limit, include_stale, apply_proposability_filter)
  - [x] 3.2: Implement `async get_cached(session: AsyncSession, cache_key: str) -> SearchResult | None` — lookup by key, check `expires_at > now()`, return deserialized result or None
  - [x] 3.3: Implement `async put_cached(session: AsyncSession, cache_key: str, request: SearchRequest, result: SearchResult, ttl_seconds: int) -> None` — upsert cache entry (INSERT ON CONFLICT UPDATE for key collisions)
  - [x] 3.4: Implement `async invalidate_all(session: AsyncSession) -> int` — DELETE all rows, return count
  - [x] 3.5: Implement `async cleanup_expired(session: AsyncSession) -> int` — DELETE WHERE `expires_at < now()`, return count
  - [x] 3.6: Implement `async count_entries(session: AsyncSession) -> int` — COUNT for observability
  - [x] 3.7: Structured logging: component `search.cache`, log hits/misses/invalidations/cleanups with counts

- [x] Task 4: Add `from_cache` metadata to SearchResult (AC: 1, 2)
  - [x] 4.1: Add `from_cache: bool = False` field to `SearchResult` in `models.py`

- [x] Task 5: Integrate cache into SearchEngine (AC: 1, 2, 3, 5)
  - [x] 5.1: In `SearchEngine.__init__`, read `get_settings().search_cache` to determine if cache is enabled
  - [x] 5.2: In `search_hybrid()`: before executing search, compute cache key and check cache; on hit, return cached result with `from_cache=True` and duration measured from cache lookup only; on miss, execute search normally, store result in cache, return with `from_cache=False`
  - [x] 5.3: Same pattern for `search_semantic_only()` and `search_keyword_only()`
  - [x] 5.4: When `enabled=False`, skip all cache logic entirely (no key computation, no DB queries)
  - [x] 5.5: Enforce `max_entries` — before inserting, if count exceeds max, run `cleanup_expired()` first; if still over max, skip cache store (don't block the response)

- [x] Task 6: Add cache invalidation hook to CatalogService (AC: 4)
  - [x] 6.1: In `CatalogService.ingest_full()`, after successful ingestion, call `invalidate_all()` and log the count
  - [x] 6.2: Pass session to `invalidate_all()` — reuse the existing session from `ingest_full()`

- [x] Task 7: Update `search/__init__.py` exports (AC: 1)
  - [x] 7.1: Export `compute_cache_key` if needed externally (prefer internal — accessed via SearchEngine)

- [x] Task 8: Unit tests (AC: 1, 2, 3, 4, 5, 6)
  - [x] 8.1: Test `compute_cache_key()` determinism: same input → same key, different input → different key
  - [x] 8.2: Test `compute_cache_key()` sensitivity: changing any SearchRequest field changes the key
  - [x] 8.3: Test `get_cached()` returns None when key not found
  - [x] 8.4: Test `get_cached()` returns None when entry is expired
  - [x] 8.5: Test `get_cached()` returns SearchResult when entry is valid
  - [x] 8.6: Test `put_cached()` stores and retrieves correctly
  - [x] 8.7: Test `put_cached()` upserts on duplicate key (updates existing entry)
  - [x] 8.8: Test `invalidate_all()` removes all entries and returns count
  - [x] 8.9: Test `cleanup_expired()` removes only expired entries
  - [x] 8.10: Test SearchEngine cache integration: mock cache functions, verify cache hit path skips search
  - [x] 8.11: Test SearchEngine cache integration: mock cache miss, verify search executes and result is cached
  - [x] 8.12: Test SearchEngine with `enabled=False`: verify no cache interaction
  - [x] 8.13: Test `SearchCacheSettings` defaults and env overrides
  - [x] 8.14: Test `from_cache` flag is True on cache hit, False on cache miss

- [x] Task 9: E2E test with real PostgreSQL (AC: 7)
  - [x] 9.1: Insert products, generate embeddings, run hybrid search → verify `from_cache=False`
  - [x] 9.2: Run same search again → verify `from_cache=True` and `duration_seconds < 1.0`
  - [x] 9.3: Call `invalidate_all()` → run same search → verify `from_cache=False`
  - [x] 9.4: Test with `enabled=False` → verify `from_cache=False` on all calls
  - [x] 9.5: Cleanup: delete test products and cache entries after tests

## Dev Notes

### Critical: Architecture Compliance

**Cache is search-internal** — it lives in `search/cache.py`, NOT as an adapter with Protocol/factory/@lru_cache pattern. Same rationale as SearchEngine and proposability filter (Stories 3.3, 3.4). Cache is an implementation detail of the search layer.

**PostgreSQL-based cache, NOT Redis** — architecture decision: "No Redis dependency — use PostgreSQL job table + asyncio for task processing" and "PostgreSQL cache table with TTL-based invalidation for query results". Single infrastructure component.

**Cache at SearchEngine level, NOT at individual search functions** — the cache wraps the complete search result (after RRF fusion, after proposability filtering), not individual semantic/keyword sub-queries. This is simpler, more effective, and avoids cache coherence issues between sub-queries.

**Serialization strategy:** Store `SearchResult` as JSON in a JSONB column. Pydantic's `.model_dump(mode="json")` for serialization, `SearchResult.model_validate()` for deserialization. UUIDs serialize to strings, floats preserved.

### Technical Requirements

**SearchCacheSettings configuration:**
```python
class SearchCacheSettings(BaseModel):
    """Search result cache settings."""
    enabled: bool = True
    ttl_seconds: int = 3600       # 1 hour default
    max_entries: int = 10_000     # Upper bound on cache rows
```
- Env vars: `SEARCH_CACHE__ENABLED=true`, `SEARCH_CACHE__TTL_SECONDS=3600`, `SEARCH_CACHE__MAX_ENTRIES=10000`

**Cache key computation:**
```python
import hashlib
import json

def compute_cache_key(request: SearchRequest) -> str:
    """Deterministic SHA-256 hash of search parameters."""
    key_data = json.dumps({
        "query": request.query,
        "limit": request.limit,
        "include_stale": request.include_stale,
        "apply_proposability_filter": request.apply_proposability_filter,
    }, sort_keys=True)
    return hashlib.sha256(key_data.encode()).hexdigest()
```

**SearchCache SQLAlchemy model:**
```python
class SearchCache(Base, TimestampMixin):
    __tablename__ = "search_cache"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # SHA-256 hex
    query: Mapped[str]                    # Original query text (for debugging)
    search_params: Mapped[dict] = mapped_column(JSONB)  # {limit, include_stale, apply_proposability_filter}
    results_json: Mapped[dict] = mapped_column(JSONB)   # Serialized SearchResult
    expires_at: Mapped[datetime] = mapped_column(index=True)
```

**Cache integration in SearchEngine:**
```python
# In search_hybrid():
if self._cache_enabled:
    cache_key = compute_cache_key(request)
    cached = await get_cached(self._session, cache_key)
    if cached is not None:
        cached.from_cache = True
        cached.duration_seconds = time.monotonic() - start
        return cached

# ... execute normal search ...

if self._cache_enabled:
    await put_cached(self._session, cache_key, request, result, self._cache_settings.ttl_seconds)
```

**Cache invalidation in CatalogService:**
```python
# In ingest_full(), after successful sync:
from quote_agent.search.cache import invalidate_all
count = await invalidate_all(session)
logger.info("Search cache invalidated after catalog re-sync",
    extra={"context": {"entries_removed": count}})
```

**Upsert pattern (PostgreSQL ON CONFLICT):**
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(SearchCache).values(...).on_conflict_do_update(
    index_elements=["cache_key"],
    set_={"results_json": ..., "expires_at": ..., "updated_at": ...}
)
```

### Architecture Compliance

**File structure:**
```
src/quote_agent/search/
├── __init__.py         # Update exports if needed
├── engine.py           # Update: wrap search methods with cache check/store
├── cache.py            # NEW: compute_cache_key(), get_cached(), put_cached(), invalidate_all(), cleanup_expired()
├── models.py           # Update: add from_cache to SearchResult
├── vector.py           # No changes
├── keyword.py          # No changes
└── proposability.py    # No changes

src/quote_agent/models/
├── __init__.py         # Update: export SearchCache
├── search_cache.py     # NEW: SearchCache SQLAlchemy model
└── ...

src/quote_agent/services/
├── catalog_service.py  # Update: add cache invalidation after ingest_full()
└── ...

alembic/versions/
└── xxx_add_search_cache_table.py  # NEW: migration
```

**Naming conventions (PEP 8 strict):**
- File: `cache.py`, `search_cache.py`
- Functions: `compute_cache_key()`, `get_cached()`, `put_cached()`, `invalidate_all()`, `cleanup_expired()`
- Classes: `SearchCacheSettings`, `SearchCache`
- Table: `search_cache` (snake_case, no plural — compound noun)

**Imports:** Absolute only — `from quote_agent.search.cache import compute_cache_key`

**Type safety:** `from __future__ import annotations` in every file. All functions typed. `mypy --strict` must pass.

**Structured logging:**
```python
logger.info("Cache hit", extra={"context": {"cache_key": key[:12], "query": request.query}})
logger.info("Cache miss", extra={"context": {"cache_key": key[:12], "reason": "not_found"}})
logger.info("Cache stored", extra={"context": {"cache_key": key[:12], "ttl_seconds": ttl}})
logger.info("Cache invalidated", extra={"context": {"entries_removed": count}})
```
Component: `search.cache`. Never `print()`.

### Library & Framework Requirements

**No new dependencies.** SQLAlchemy, Pydantic, hashlib, json all already available. PostgreSQL JSONB via `sqlalchemy.dialects.postgresql.JSONB`. The `pg_insert` for upsert is from `sqlalchemy.dialects.postgresql`.

### File Structure Requirements

**New files:**
- `src/quote_agent/search/cache.py` — cache logic functions
- `src/quote_agent/models/search_cache.py` — SQLAlchemy model
- `alembic/versions/xxx_add_search_cache_table.py` — migration
- `tests/unit/test_search_cache.py` — unit tests
- `tests/e2e/test_search_cache_e2e.py` — E2E tests

**Modified files:**
- `src/quote_agent/config.py` — add `SearchCacheSettings` + field on `Settings`
- `src/quote_agent/search/models.py` — add `from_cache` to `SearchResult`
- `src/quote_agent/search/engine.py` — integrate cache check/store in search methods
- `src/quote_agent/search/__init__.py` — update exports if needed
- `src/quote_agent/models/__init__.py` — export `SearchCache`
- `src/quote_agent/services/catalog_service.py` — add cache invalidation after ingestion

### Testing Requirements

**Unit tests (no DB, no real model):**
- Test `compute_cache_key()` determinism and sensitivity
- Test `SearchCacheSettings` defaults and env overrides
- Mock `AsyncSession` for `get_cached()`, `put_cached()`, `invalidate_all()`, `cleanup_expired()`
- Test SearchEngine cache integration: mock cache functions, verify correct path taken
- Test `from_cache` flag correctness
- Test `enabled=False` skips all cache logic
- Test naming: `test_{behavior}_when_{condition}()` e.g., `test_cache_hit_when_valid_entry_exists()`
- Docstrings: `"""AC-{#}: ..."""`

**E2E tests (real PostgreSQL + real embedding model):**
- Mark with `@pytest.mark.e2e`
- Use `requires_e2e` skip decorator
- Insert products, embed, search, verify cache behavior
- Verify `from_cache` and `duration_seconds` on cache hits
- Test invalidation clears cache
- Test `enabled=False` bypasses cache
- Cleanup: delete test products and cache entries after tests

### Previous Story Intelligence

**Story 3.4 (Proposability Filter — just completed):**
- Proposability filter applies at SQL level via WHERE clauses, before RRF fusion
- `apply_proposability_filter` is a SearchRequest field — MUST be part of cache key (different filter settings = different results)
- 316 unit tests + E2E tests all passing. No regressions.
- Clean code review — removed dead `log_proposability_filter()` function

**Story 3.3 (Hybrid Search):**
- `SearchEngine` takes `(session, embedding_adapter)` in constructor
- Three methods: `search_hybrid()`, `search_semantic_only()`, `search_keyword_only()`
- All return `SearchResult` — this is what gets cached
- asyncpg limitation: sequential (not concurrent) search execution — caching especially valuable to avoid repeated sequential queries
- `_rrf_fuse()` operates on `ScoredProduct` list — cache stores the fused result, not sub-results

**Story 3.1 (Catalog Ingestion):**
- `CatalogService.ingest_full()` returns `IngestionResult` and commits the session
- This is where cache invalidation hook goes — after successful commit
- `sync_from_erp()` is the public method that calls `ingest_full()`

**Story 3.2 (Embeddings):**
- E2E test pattern: insert from `catalog_50k_sample.jsonl`, use `e2e_db_session` fixture
- Embedding generation MUST complete before search works — cache E2E tests must embed first

### Git Intelligence

Recent commits:
- `6c0285d` feat: add proposability filter with config-driven rules and SQL-level filtering (Story 3.4)
- `6dec026` feat: add hybrid search with semantic + keyword + RRF fusion (Story 3.3)
- `08f9b54` feat: add embedding generation, HNSW vector index, and dimension validation (Story 3.2)
- `2c28257` feat: add ERP catalog ingestion with zero-preprocessing, re-sync, and stale detection (Story 3.1)

All 316 unit tests passing. Search module fully functional. No regressions.

### What NOT to Do

- Do NOT use Redis or any external cache — PostgreSQL table only (architecture decision)
- Do NOT cache at individual search function level (semantic/keyword) — cache at SearchEngine level after full result composition
- Do NOT implement semantic similarity for "similar" queries — use exact parameter matching only for MVP. Semantic cache deduplication is a future enhancement
- Do NOT cache embedding generation calls — that's a different concern (embeddings are generated once per product, not per query)
- Do NOT implement cache warming or pre-population — queries are cached on first execution only
- Do NOT implement per-product cache invalidation — full invalidation on catalog re-sync is sufficient for MVP (50K products, 300 quotes/day)
- Do NOT add periodic cache cleanup as a background task — `cleanup_expired()` runs opportunistically before cache store when `max_entries` exceeded
- Do NOT implement jargon synonym tables — that's Story 3.6
- Do NOT create an admin CLI for cache management — that's Epic 8 scope
- Do NOT use relative imports anywhere
- Do NOT mock services in E2E tests — use ALL real services (PostgreSQL, embedding model)
- Do NOT change `_rrf_fuse()` — caching wraps the complete search, not sub-queries
- Do NOT add cache metrics to the health endpoint — that's Epic 7 (observability)
- Do NOT hash the embedding vector in the cache key — the cache key is based on SearchRequest parameters only; the embedding is an implementation detail of the search

### Project Structure Notes

- New file `search/cache.py` — consistent with search module structure (like `proposability.py`)
- New file `models/search_cache.py` — follows existing model pattern (like `product.py`)
- New Alembic migration — follows existing migration naming convention
- No conflicts with existing structure detected

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.5] — acceptance criteria: cache recurring queries, TTL-based, invalidate on re-sync
- [Source: _bmad-output/planning-artifacts/prd.md#FR10] — "agent can cache search results for similar or recurring requests to reduce processing time and LLM costs"
- [Source: _bmad-output/planning-artifacts/prd.md#NFR-P6] — "cache hit response < 1 second"
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — "PostgreSQL table with TTL-based invalidation. No additional infrastructure (no Redis)"
- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure] — "No Redis dependency — use PostgreSQL"
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] — `search/cache.py` listed in project structure
- [Source: docs/project-context.md] — naming conventions, test patterns, structured logging, settings pattern
- [Source: src/quote_agent/search/engine.py] — current SearchEngine with hybrid/semantic/keyword methods
- [Source: src/quote_agent/search/models.py] — current SearchRequest, ScoredProduct, SearchResult DTOs
- [Source: src/quote_agent/config.py] — Settings with SearchSettings pattern to follow
- [Source: src/quote_agent/models/base.py] — Base class, TimestampMixin, engine/session factories
- [Source: src/quote_agent/models/product.py] — Product model structure for reference
- [Source: src/quote_agent/services/catalog_service.py] — ingest_full() where cache invalidation hook goes
- [Source: _bmad-output/implementation-artifacts/3-4-filtre-de-proposabilite.md] — previous story learnings, file patterns, test patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no blockers.

### Completion Notes List

- Task 1: Added `SearchCacheSettings` (enabled, ttl_seconds, max_entries) to config.py with `search_cache` field on Settings. Env var mapping verified (SEARCH_CACHE__ENABLED, etc.)
- Task 2: Created `SearchCache` SQLAlchemy model in `models/search_cache.py` with JSONB columns, TTL-based expiry, unique index on cache_key. Alembic migration `24ece7f6fefc` created.
- Task 3: Implemented all cache functions in `search/cache.py`: compute_cache_key (SHA-256), get_cached (TTL-aware lookup), put_cached (upsert via ON CONFLICT), invalidate_all, cleanup_expired, count_entries. Structured logging on all operations.
- Task 4: Added `from_cache: bool = False` field to SearchResult DTO.
- Task 5: Integrated cache into SearchEngine — all 3 search methods (hybrid, semantic_only, keyword_only) check cache before search and store after. max_entries enforced with cleanup_expired before insert. Cache disabled path skips all cache logic.
- Task 6: Added cache invalidation hook in CatalogService.ingest_full() after stale detection — calls invalidate_all() and logs count.
- Task 7: No export changes needed — cache accessed internally via SearchEngine.
- Task 8: 23 unit tests covering: cache key determinism/sensitivity, get/put/invalidate/cleanup/count, SearchEngine cache integration (hit/miss/disabled), SearchCacheSettings defaults and env overrides, from_cache flag correctness.
- Task 9: 3 E2E tests: cache hit returns from_cache=True with duration < 1s, invalidate_all clears cache, enabled=False bypasses cache.
- Updated 4 existing test files (test_catalog_service.py, test_search_engine.py, test_search_proposability.py) to account for cache invalidation call in ingest_full() and cache settings in SearchEngine constructor.
- All 339 unit tests pass (316 existing + 23 new). No regressions.

### Change Log

- 2026-03-20: Story 3.5 implementation complete — search result cache with PostgreSQL-backed TTL, all 9 tasks done
- 2026-03-20: Code review fixes — H-1: commit after cache invalidation in ingest_full(), H-2: add method to cache key to prevent cross-method collision, M-1: distinguish expired vs not_found in cache miss logging, L-1: remove redundant unique=True on cache_key column

### File List

**New files:**
- `src/quote_agent/search/cache.py` — cache logic (compute_cache_key, get_cached, put_cached, invalidate_all, cleanup_expired, count_entries)
- `src/quote_agent/models/search_cache.py` — SearchCache SQLAlchemy model
- `alembic/versions/24ece7f6fefc_add_search_cache_table.py` — Alembic migration
- `tests/unit/test_search_cache.py` — 23 unit tests
- `tests/e2e/test_search_cache_e2e.py` — 3 E2E tests

**Modified files:**
- `src/quote_agent/config.py` — added SearchCacheSettings class and search_cache field on Settings
- `src/quote_agent/search/models.py` — added from_cache: bool = False to SearchResult
- `src/quote_agent/search/engine.py` — integrated cache check/store in all search methods, added _check_cache and _store_in_cache helpers
- `src/quote_agent/models/__init__.py` — exported SearchCache
- `src/quote_agent/services/catalog_service.py` — added cache invalidation after ingest_full()
- `tests/unit/test_catalog_service.py` — added cache invalidation mock result to side_effect lists
- `tests/unit/test_search_engine.py` — added search_cache.enabled=False to mock settings
- `tests/unit/test_search_proposability.py` — added search_cache.enabled=False to _make_engine()
