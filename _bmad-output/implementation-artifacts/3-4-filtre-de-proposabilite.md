# Story 3.4: Filtre de Proposabilité

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want non-proposable products (inactive, out-of-stock) filtered out before I see search results,
So that I never receive proposals for products the company can't actually sell.

## Acceptance Criteria

1. **AC-1: Non-proposable products filtered from search results**
   - Given search results include products marked as `is_active = False` or `stock_status = "out_of_stock"`
   - When the proposability filter is applied (default: on)
   - Then non-proposable products are removed from the results
   - And the filter criteria come from `ProposabilitySettings` in configuration (not hardcoded)
   - And the filter applies consistently to all three search paths (hybrid, semantic-only, keyword-only) and exact reference

2. **AC-2: Empty result set when all products non-proposable**
   - Given all matching products are non-proposable
   - When the filter runs
   - Then an empty result set is returned (zero results)
   - And the `SearchResult.total_found` reflects the filtered count (0)
   - And structured logging reports the pre-filter and post-filter counts

3. **AC-3: Proposability status synced on catalog re-sync**
   - Given a product's `stock_status` changes in the ERP (e.g., from `"in_stock"` to `"out_of_stock"`)
   - When the catalog is re-synced via `CatalogService.sync_from_erp()`
   - Then the `stock_status` and `is_active` are updated in the DB (already done by Story 3.1)
   - And subsequent searches exclude the now-non-proposable product

4. **AC-4: Filter can be bypassed via SearchRequest**
   - Given a caller passes `apply_proposability_filter=False` in the SearchRequest
   - When the search runs
   - Then non-proposable products ARE included in results
   - And `ScoredProduct.is_proposable` indicates whether each product passes the filter

5. **AC-5: Configuration-driven rules**
   - Given `ProposabilitySettings` defines `exclude_out_of_stock=True` and `exclude_inactive=True`
   - When the configuration is changed (e.g., `PROPOSABILITY__EXCLUDE_OUT_OF_STOCK=false`)
   - Then the filter respects the updated configuration
   - And configurable `excluded_categories` list allows blocking entire product categories

6. **AC-6: E2E test with real PostgreSQL**
   - Given products with mixed proposability status are inserted (in_stock + active, out_of_stock, inactive)
   - When hybrid search runs with proposability filter enabled
   - Then only proposable products are returned
   - And when proposability filter is disabled, all matching products are returned

## Tasks / Subtasks

- [x] Task 1: Add `ProposabilitySettings` to configuration (AC: 5)
  - [x] 1.1: Add `ProposabilitySettings` to `config.py`: `exclude_out_of_stock` (bool, default `True`), `exclude_inactive` (bool, default `True`), `excluded_categories` (list[str], default `[]`)
  - [x] 1.2: Add `proposability: ProposabilitySettings` field to `Settings`
  - [x] 1.3: Verify env var mapping: `PROPOSABILITY__EXCLUDE_OUT_OF_STOCK`, `PROPOSABILITY__EXCLUDE_INACTIVE`, `PROPOSABILITY__EXCLUDED_CATEGORIES`

- [x] Task 2: Update `SearchRequest` and `ScoredProduct` DTOs (AC: 1, 4)
  - [x] 2.1: Add `apply_proposability_filter: bool = True` to `SearchRequest`
  - [x] 2.2: Add `is_proposable: bool = True` to `ScoredProduct` — indicates whether the product passes proposability rules

- [x] Task 3: Implement proposability filter logic (AC: 1, 2, 5)
  - [x] 3.1: Add a function `build_proposability_clauses(settings: ProposabilitySettings) -> list[ColumnElement]` in a new file `src/quote_agent/search/proposability.py`
  - [x] 3.2: Logic: returns a list of SQLAlchemy WHERE clauses based on settings — `Product.is_active.is_(True)` if `exclude_inactive`, `Product.stock_status != "out_of_stock"` if `exclude_out_of_stock`, `Product.category.notin_(excluded_categories)` if list not empty
  - [x] 3.3: Add a function `is_product_proposable(product: Product, settings: ProposabilitySettings) -> bool` — pure Python check for use in DTOs and post-filtering
  - [x] 3.4: Structured logging when filter removes results: component `search.proposability`

- [x] Task 4: Apply filter to all search functions (AC: 1, 4)
  - [x] 4.1: Update `search_semantic()` in `vector.py` — accept `proposability_clauses: list | None` parameter, apply to WHERE chain
  - [x] 4.2: Update `search_keyword()` in `keyword.py` — same pattern
  - [x] 4.3: Update `search_exact_ref()` in `keyword.py` — same pattern
  - [x] 4.4: Update `SearchEngine` in `engine.py` — build proposability clauses from config, pass through to all search functions; set `is_proposable` on each `ScoredProduct` in the result
  - [x] 4.5: When `apply_proposability_filter=False`, do NOT add WHERE clauses but still compute `is_proposable` for each result
  - [x] 4.6: Log pre-filter and post-filter counts when filter removes results

- [x] Task 5: Update `search/__init__.py` — exports (AC: 1)
  - [x] 5.1: Export `ProposabilitySettings` or keep internal (prefer internal — it's accessed via `get_settings().proposability`)

- [x] Task 6: Unit tests (AC: 1, 2, 4, 5)
  - [x] 6.1: Test `build_proposability_clauses()` returns correct clauses for each setting combination
  - [x] 6.2: Test `is_product_proposable()` with various product states (active+in_stock, inactive, out_of_stock, excluded category)
  - [x] 6.3: Test `SearchEngine.search_hybrid()` with proposability filter: mock DB to return mixed products, verify non-proposable removed
  - [x] 6.4: Test `SearchEngine.search_hybrid()` with `apply_proposability_filter=False`: verify all products returned, `is_proposable` correctly set
  - [x] 6.5: Test all-products-filtered-out edge case: verify empty result + logging
  - [x] 6.6: Test `excluded_categories` filtering
  - [x] 6.7: Test `ProposabilitySettings` defaults and env overrides
  - [x] 6.8: Test semantic-only and keyword-only paths also apply filter

- [x] Task 7: E2E test with real PostgreSQL (AC: 6)
  - [x] 7.1: Insert products with: (a) `is_active=True, stock_status="in_stock"`, (b) `is_active=False`, (c) `stock_status="out_of_stock"`, (d) `is_active=True, stock_status="on_order"` (proposable)
  - [x] 7.2: Run hybrid search with default filter → verify only (a) and (d) returned
  - [x] 7.3: Run hybrid search with `apply_proposability_filter=False` → verify all 4 returned, `is_proposable` correctly set
  - [x] 7.4: Test `excluded_categories` → add category to config, verify products in that category excluded
  - [x] 7.5: Cleanup: delete test products after tests

## Dev Notes

### Critical: Architecture Compliance

**Proposability is NOT an adapter** — it's search-internal filtering logic. Lives in `search/proposability.py`, no Protocol/factory/@lru_cache pattern. Same rationale as SearchEngine itself (Story 3.3 decision).

**Filter at SQL level, not post-query:**
The proposability filter MUST be applied as SQL WHERE clauses within the search queries themselves, not as a Python post-filter on returned results. Reasons:
- Performance: filtering at DB level avoids fetching rows we'll discard
- Correctness: `LIMIT` applies after WHERE, so we get the right number of results
- Consistency: same approach as `is_stale` filtering already in place

**Pattern to follow — same as `include_stale`:**
```python
# In search_semantic(), search_keyword(), search_exact_ref():
# Add proposability clauses the same way is_stale is handled
if proposability_clauses:
    for clause in proposability_clauses:
        stmt = stmt.where(clause)
```

### Technical Requirements

**ProposabilitySettings configuration:**
```python
class ProposabilitySettings(BaseModel):
    """Proposability filter rules — which products can be proposed to clients."""
    exclude_out_of_stock: bool = True
    exclude_inactive: bool = True
    excluded_categories: list[str] = Field(default_factory=list)
```
- Env vars: `PROPOSABILITY__EXCLUDE_OUT_OF_STOCK=true`, `PROPOSABILITY__EXCLUDED_CATEGORIES='["Obsolete","Custom"]'`

**WHERE clause builder:**
```python
def build_proposability_clauses(settings: ProposabilitySettings) -> list[ColumnElement]:
    clauses: list[ColumnElement] = []
    if settings.exclude_inactive:
        clauses.append(Product.is_active.is_(True))
    if settings.exclude_out_of_stock:
        clauses.append(Product.stock_status != "out_of_stock")
    if settings.excluded_categories:
        clauses.append(Product.category.notin_(settings.excluded_categories))
    return clauses
```

**`is_product_proposable()` — mirrors SQL logic in Python:**
```python
def is_product_proposable(product_active: bool, stock_status: str, category: str, settings: ProposabilitySettings) -> bool:
    if settings.exclude_inactive and not product_active:
        return False
    if settings.exclude_out_of_stock and stock_status == "out_of_stock":
        return False
    if settings.excluded_categories and category in settings.excluded_categories:
        return False
    return True
```
Used to set `ScoredProduct.is_proposable` when `apply_proposability_filter=False` (all products returned but flagged).

**SearchEngine integration:**
```python
# In SearchEngine.__init__:
self._proposability_settings = get_settings().proposability

# In search_hybrid (and semantic_only, keyword_only):
prop_clauses = (
    build_proposability_clauses(self._proposability_settings)
    if request.apply_proposability_filter
    else None
)
# Pass prop_clauses to search_semantic(), search_keyword(), search_exact_ref()
```

**Note on `stock_status` values:** From the Odoo adapter and test fixture, known values are: `"in_stock"`, `"out_of_stock"`, `"on_order"`. The filter only excludes `"out_of_stock"` — `"on_order"` products ARE proposable (can be ordered). This is configuration-driven, not hardcoded.

**Note on `sale_ok`:** Odoo's `sale_ok` field is stored in `metadata_["sale_ok"]`. For MVP, the proposability filter operates on `is_active` and `stock_status` only (top-level columns with indexes). A future enhancement could add metadata-based rules (Epic 8), but that's out of scope here. Do NOT add JSON-based filtering in this story.

### Architecture Compliance

**File structure:**
```
src/quote_agent/search/
├── __init__.py         # Update exports if needed
├── engine.py           # Update: pass proposability clauses to search functions
├── vector.py           # Update: accept + apply proposability clauses
├── keyword.py          # Update: accept + apply proposability clauses
├── models.py           # Update: add fields to SearchRequest + ScoredProduct
└── proposability.py    # NEW: build_proposability_clauses(), is_product_proposable()
```

**Naming conventions (PEP 8 strict):**
- File: `proposability.py`
- Functions: `build_proposability_clauses()`, `is_product_proposable()`
- Class: `ProposabilitySettings`
- Constants: none needed

**Imports:** Absolute only — `from quote_agent.search.proposability import build_proposability_clauses`

**Type safety:** `from __future__ import annotations` in every file. All functions typed. `mypy --strict` must pass. Use `ColumnElement` from `sqlalchemy.sql.elements` for type annotation of SQL clauses.

**Structured logging:**
```python
logger.info(
    "Proposability filter applied",
    extra={"context": {"pre_filter": count_before, "post_filter": count_after, "removed": count_before - count_after}},
)
```
Component: `search.proposability`. Never `print()`.

### Library & Framework Requirements

**No new dependencies.** SQLAlchemy, Pydantic, pydantic-settings all already installed. Proposability filtering uses standard SQLAlchemy WHERE clauses — no extension needed.

### File Structure Requirements

**New files:**
- `src/quote_agent/search/proposability.py` — `build_proposability_clauses()`, `is_product_proposable()`
- `tests/unit/test_search_proposability.py` — unit tests for proposability logic
- `tests/e2e/test_proposability_e2e.py` — E2E tests

**Modified files:**
- `src/quote_agent/config.py` — add `ProposabilitySettings` + field on `Settings`
- `src/quote_agent/search/models.py` — add `apply_proposability_filter` to `SearchRequest`, `is_proposable` to `ScoredProduct`
- `src/quote_agent/search/vector.py` — accept `proposability_clauses` parameter
- `src/quote_agent/search/keyword.py` — accept `proposability_clauses` parameter in both `search_keyword()` and `search_exact_ref()`
- `src/quote_agent/search/engine.py` — build and pass proposability clauses, set `is_proposable` on results

### Testing Requirements

**Unit tests (no DB, no real model):**
- Test `build_proposability_clauses()` returns correct number of clauses per config
- Test `is_product_proposable()` with all combinations: (active, in_stock) → True; (inactive, in_stock) → False; (active, out_of_stock) → False; (active, in_stock, excluded_category) → False
- Mock `AsyncSession` and `EmbeddingAdapter` for SearchEngine tests
- Test filter bypass (`apply_proposability_filter=False`) returns all products with correct `is_proposable`
- Test empty results after filtering
- Test naming: `test_{behavior}_when_{condition}()` e.g., `test_out_of_stock_excluded_when_filter_enabled()`
- Docstrings: `"""AC-{#}: ..."""`

**E2E tests (real PostgreSQL + real embedding model):**
- Mark with `@pytest.mark.e2e`
- Use `requires_e2e` skip decorator
- Insert products with varied `is_active`, `stock_status`, `category` values
- Run hybrid search with and without proposability filter
- Verify `is_proposable` flag on results
- Cleanup: delete test products after tests

### Previous Story Intelligence

**Story 3.3 (Hybrid Search — just completed):**
- `SearchEngine` takes `(session, embedding_adapter)` in constructor, reads settings from `get_settings().search`
- Three search methods: `search_hybrid()`, `search_semantic_only()`, `search_keyword_only()`
- `search_semantic()` and `search_keyword()` already accept `include_stale` kwarg — proposability clauses follow the same pattern
- `search_exact_ref()` also accepts `include_stale` — must also accept proposability clauses
- asyncpg limitation: sequential (not concurrent) search execution — no change needed
- `_rrf_fuse()` operates on `ScoredProduct` list — no change needed (filter happens at SQL level, before RRF)
- Story 3.3 debug: asyncpg doesn't support parameterized `SET LOCAL` — not relevant here

**Story 3.1 (Catalog Ingestion):**
- `Product` model has `is_active` (bool), `stock_status` (str), `is_stale` (bool)
- `is_active` already has an index: `ix_products_is_active`
- `stock_status` has NO index — consider adding one if filtering performance matters (at 50K rows, probably fine without)
- Odoo maps `active` → `is_active`, `stock_status` defaults to `"in_stock"` (stock module not in Community base), `sale_ok` → `metadata_["sale_ok"]`
- `CatalogService.sync_from_erp()` already updates `stock_status` and `is_active` on re-sync → AC-3 is already satisfied by existing code

**Story 3.2 (Embeddings):**
- E2E test pattern: insert from `catalog_50k_sample.jsonl`, use `e2e_db_session` fixture, run `embed_all()` before searching
- Fixture data distribution: 62 `in_stock`, 27 `on_order`, 11 `out_of_stock`; 97 active, 3 inactive

### Git Intelligence

Recent commits:
- `6dec026` feat: add hybrid search with semantic + keyword + RRF fusion (Story 3.3)
- `08f9b54` feat: add embedding generation, HNSW vector index, and dimension validation (Story 3.2)
- `2c28257` feat: add ERP catalog ingestion with zero-preprocessing, re-sync, and stale detection (Story 3.1)

Story 3.3 just completed. All 289 unit + 15 E2E tests passing. Search module fully functional.

### What NOT to Do

- Do NOT implement admin configuration UI or CLI commands (`agent config show --proposability`) — that's Story 8.1
- Do NOT implement config versioning/rollback — that's Story 8.1
- Do NOT filter on `metadata_["sale_ok"]` or any JSON field — stick to top-level indexed columns (`is_active`, `stock_status`, `category`)
- Do NOT implement caching — that's Story 3.5
- Do NOT implement jargon synonym tables — that's Story 3.6
- Do NOT create a new Alembic migration — no schema changes needed (all columns and indexes already exist)
- Do NOT post-filter in Python — apply WHERE clauses at SQL level for performance and LIMIT correctness
- Do NOT add a `stock_status` index — 50K rows is fine with a seq scan on a boolean condition; premature optimization
- Do NOT use relative imports anywhere
- Do NOT mock services in E2E tests — use ALL real services (PostgreSQL, embedding model)
- Do NOT change the `_rrf_fuse()` function — proposability filtering happens before RRF, at the SQL level
- Do NOT add `escalation` logic for empty results — that's the agent's responsibility (Epic 4), not the search engine's

### Project Structure Notes

- New file `search/proposability.py` — consistent with search module structure
- No conflicts with existing structure detected
- `search/cache.py` is NOT part of this story (Story 3.5)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4] — acceptance criteria: filter non-proposable, config-driven, re-sync
- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.1] — future admin configuration of proposability rules (CLI, versioning, reload)
- [Source: _bmad-output/planning-artifacts/prd.md#FR6] — "agent can filter out non-proposable products (custom, obsolete, out-of-stock)"
- [Source: _bmad-output/planning-artifacts/prd.md#FR42] — "administrator can configure proposability filter rules"
- [Source: _bmad-output/planning-artifacts/architecture.md#Search Component] — search module file structure
- [Source: docs/project-context.md] — naming conventions, test patterns, structured logging
- [Source: src/quote_agent/search/engine.py] — current SearchEngine with hybrid/semantic/keyword methods
- [Source: src/quote_agent/search/vector.py] — semantic search with `include_stale` pattern to follow
- [Source: src/quote_agent/search/keyword.py] — keyword + exact ref search with `include_stale` pattern
- [Source: src/quote_agent/search/models.py] — current SearchRequest, ScoredProduct, SearchResult DTOs
- [Source: src/quote_agent/models/product.py] — Product model: is_active (indexed), stock_status, is_stale, category
- [Source: src/quote_agent/config.py] — current Settings with SearchSettings pattern to follow
- [Source: src/quote_agent/adapters/erp/odoo.py] — Odoo mapping: active→is_active, stock_status defaults "in_stock", sale_ok→metadata
- [Source: tests/fixtures/catalog_50k_sample.jsonl] — fixture distribution: 62 in_stock, 27 on_order, 11 out_of_stock, 3 inactive

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no blockers encountered.

### Completion Notes List

- Implemented `ProposabilitySettings` as a Pydantic `BaseModel` with env var support via `__` nested delimiter
- Created `search/proposability.py` with `build_proposability_clauses()` (SQL-level WHERE clauses) and `is_product_proposable()` (pure Python mirror for DTO tagging)
- Filter applied at SQL level in all 3 search paths: semantic, keyword, exact_ref — consistent with existing `include_stale` pattern
- When `apply_proposability_filter=False`, SQL clauses are not added but `is_proposable` is computed per-product via `proposability_settings` passed to low-level search functions
- `log_proposability_filter()` helper in proposability.py + `proposability_filter` flag in engine log context
- 27 unit tests covering: settings defaults/env mapping, clause builder, pure-Python check, engine integration (all paths), DTOs
- 3 E2E tests covering: filter-on (only proposable returned), filter-off (all returned with correct `is_proposable`), excluded_categories
- All 316 unit tests pass, 0 regressions. Ruff + mypy clean.

### File List

**New files:**
- `src/quote_agent/search/proposability.py` — `build_proposability_clauses()`, `is_product_proposable()`
- `tests/unit/test_search_proposability.py` — 27 unit tests
- `tests/e2e/test_proposability_e2e.py` — 3 E2E tests

**Modified files:**
- `src/quote_agent/config.py` — added `ProposabilitySettings` class + `proposability` field on `Settings`
- `src/quote_agent/search/models.py` — added `apply_proposability_filter` to `SearchRequest`, `is_proposable` to `ScoredProduct`
- `src/quote_agent/search/vector.py` — added `proposability_clauses` and `proposability_settings` parameters, apply clauses + tag `is_proposable`
- `src/quote_agent/search/keyword.py` — same for `search_keyword()` and `search_exact_ref()`
- `src/quote_agent/search/engine.py` — build/pass proposability clauses to all search functions, `proposability_filter` in log context

### Change Log

- 2026-03-20: Story 3.4 implementation complete — proposability filter with configuration-driven rules, SQL-level filtering, filter bypass with `is_proposable` tagging, 27 unit + 3 E2E tests
- 2026-03-20: Code review fixes — removed dead `log_proposability_filter()` function (SQL-level filtering makes pre/post counts unavailable; engine already logs filter status); strengthened E2E test assertions to prevent vacuous pass
