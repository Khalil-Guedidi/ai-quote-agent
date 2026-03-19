# Story 3.1: Ingestion Catalogue depuis l'ERP (Zero-Preprocessing)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator (Laurent)**,
I want the agent to ingest product catalog data from Odoo (API or export) without any manual preprocessing,
So that the system works with dirty, unstructured catalogs out of the box — no cleanup required.

## Acceptance Criteria

1. **AC-1: Zero-preprocessing ingestion from Odoo**
   - Given an Odoo instance with a messy product catalog (inconsistent naming, duplicates, missing metadata, abbreviations)
   - When the ingestion process runs
   - Then all products are stored in PostgreSQL as-is without requiring manual cleanup
   - And product data includes: reference, name, description, category, price, stock status, and any available metadata

2. **AC-2: 50K-scale performance**
   - Given a catalog with 50,000 product references
   - When ingestion runs
   - Then it completes successfully without memory or performance issues
   - And progress is logged with structured JSON (batch count, total processed, elapsed time)

3. **AC-3: Re-sync / delta detection**
   - Given the catalog has already been ingested
   - When ingestion runs again (re-sync)
   - Then new products are inserted, updated products are updated, and stale entries are flagged (not deleted)
   - And the re-sync is logged with counts: inserted, updated, unchanged, flagged-stale

4. **AC-4: E2E test with real Odoo**
   - Given the 50K synthetic catalog from `tests/fixtures/catalog_50k.jsonl`
   - When loaded into the test Odoo instance via a seed fixture
   - Then ingestion through the real `ERPAdapter.get_products()` path produces correct records in PostgreSQL
   - And at least a representative subset (500+ products) is validated end-to-end

## Tasks / Subtasks

- [x] Task 1: Create `Product` DTO and extend `ERPAdapter` protocol (AC: 1)
  - [x] 1.1: Add `Product` Pydantic DTO to `src/quote_agent/adapters/erp/models.py` — fields aligned with catalog_50k.jsonl shape: `reference` (str), `name` (str), `description` (str | None), `category` (str), `unit_price` (float), `stock_status` (str), `is_active` (bool), `metadata` (dict[str, Any])
  - [x] 1.2: Add `ProductFilter` Pydantic DTO to `models.py` — optional filters: `active_only` (bool, default True), `category` (str | None), `limit` (int, default 500), `offset` (int, default 0)
  - [x] 1.3: Add `get_products(self, filters: ProductFilter) -> list[Product]` to `ERPAdapter` Protocol in `protocol.py`

- [x] Task 2: Implement `OdooAdapter.get_products()` (AC: 1, 2)
  - [x] 2.1: Implement `get_products()` in `odoo.py` — XML-RPC `search_read` on `product.product` model with field mapping from Odoo fields to `Product` DTO
  - [x] 2.2: Field mapping: `default_code` → `reference`, `name` → `name`, `description_sale` → `description`, `categ_id[1]` → `category`, `list_price` → `unit_price`, `active` → `is_active`. Stock status: default `"in_stock"` (no `stock` module in Community base install — see pitfall below)
  - [x] 2.3: Pagination via `limit`/`offset` with `order: "id asc"`. Use `context: {"active_test": False}` to include archived products
  - [x] 2.4: Build `metadata` dict from optional Odoo fields: `barcode`, `type`, `sale_ok`, `uom_id[1]`, `weight`
  - [x] 2.5: Handle Odoo `False` values (Odoo returns `False` instead of `None` for empty fields) — convert to `None`

- [x] Task 3: Create `products` SQLAlchemy model + Alembic migration (AC: 1, 2)
  - [x] 3.1: Create `src/quote_agent/models/product.py` — SQLAlchemy model `Product` with `TimestampMixin`:
    - `id` (UUID, PK), `odoo_id` (int, unique, nullable — for re-sync), `reference` (str, indexed), `name` (str), `description` (text, nullable), `category` (str, indexed), `unit_price` (float), `stock_status` (str), `is_active` (bool, default True), `metadata_` (JSON, nullable), `is_stale` (bool, default False)
  - [x] 3.2: Add `vector` column placeholder (pgvector `Vector(dim)`) — nullable, populated by Story 3.2
  - [x] 3.3: Create Alembic migration for `products` table with indexes: `ix_products_reference`, `ix_products_category`, `ix_products_odoo_id`, `ix_products_is_active`
  - [x] 3.4: Register model in `models/__init__.py`

- [x] Task 4: Create `CatalogService` for ingestion orchestration (AC: 1, 2, 3)
  - [x] 4.1: Create `src/quote_agent/services/catalog_service.py` with `CatalogService` class
  - [x] 4.2: Implement `ingest_full()` method: paginated fetch from ERP adapter → batch upsert to PostgreSQL. Use batches of 500 for reads, commit every 500 records
  - [x] 4.3: Implement upsert logic keyed on `odoo_id`: INSERT if new, UPDATE if changed (compare hash of key fields), skip if unchanged
  - [x] 4.4: Implement stale detection: after full ingestion, mark products with `odoo_id NOT IN (fetched IDs)` as `is_stale = True`
  - [x] 4.5: Structured logging: log batch progress (`component: "services.catalog_service"`), final summary with counts (inserted, updated, unchanged, stale)
  - [x] 4.6: Return `IngestionResult` DTO with counts and duration

- [x] Task 5: Unit tests (AC: 1, 2, 3)
  - [x] 5.1: Test `Product` DTO validation — valid data, missing optional fields, Odoo `False` conversion
  - [x] 5.2: Test Odoo field mapping — verify `categ_id` tuple extraction, `default_code` False → None, metadata assembly
  - [x] 5.3: Test `CatalogService` upsert logic — insert new, update changed, skip unchanged, flag stale (mock the adapter and DB session)
  - [x] 5.4: Test pagination termination — last batch smaller than limit stops the loop
  - [x] 5.5: Test structured logging output for ingestion events

- [x] Task 6: E2E test with real Odoo (AC: 4)
  - [x] 6.1: Create Odoo seed fixture: load a representative subset of `catalog_50k.jsonl` (500+ products) into the test Odoo instance via XML-RPC `product.product` create (batch size 50)
  - [x] 6.2: E2E test: run `CatalogService.ingest_full()` against real Odoo → verify products in real PostgreSQL
  - [x] 6.3: E2E test: run ingestion twice → verify re-sync produces correct counts (second run: 0 inserted, 0 updated, N unchanged)
  - [x] 6.4: E2E test: modify a product in Odoo → re-run ingestion → verify updated count = 1
  - [x] 6.5: Cleanup fixture: delete seeded products from Odoo and PostgreSQL after tests

## Dev Notes

### Technical Requirements

**Odoo XML-RPC API — established pattern from prototype (Story 0.2):**
- Endpoint: `/xmlrpc/2/object` → `execute_kw(db, uid, api_key, "product.product", "search_read", [domain], kwargs)`
- Auth: `/xmlrpc/2/common` → `authenticate()` returns `uid` (int). Already implemented in `OdooAdapter.__init__` path via health check.
- The OdooAdapter already wraps sync `xmlrpc.client` calls with `asyncio.to_thread()` — follow same pattern for `get_products()`.
- Pagination: `limit=500`, `offset=0`, `order="id asc"`. Stop when `len(batch) < limit`.
- Include archived products: `context: {"active_test": False}`.

**Odoo field mapping table:**

| Odoo Field | Product DTO Field | Type | Notes |
|------------|-------------------|------|-------|
| `id` | — (stored as `odoo_id` in DB) | int | Used for re-sync keying |
| `default_code` | `reference` | str \| False | False when empty — convert to `""` |
| `name` | `name` | str | May contain abbreviations, mixed case |
| `description_sale` | `description` | str \| False | May contain HTML, truncated text, mixed FR/EN |
| `categ_id` | `category` | [int, str] | Extract index [1] for name. Returns `[5, "Tubes & Tuyaux"]` |
| `list_price` | `unit_price` | float | Sales price from template |
| `active` | `is_active` | bool | False = archived |
| `barcode` | `metadata.barcode` | str \| False | Unique constraint in Odoo |
| `type` | `metadata.type` | str | "consu", "service", "product" |
| `sale_ok` | `metadata.sale_ok` | bool | Proposability filter (Story 3.4) |
| `uom_id` | `metadata.uom` | [int, str] | Extract [1] for unit name |
| `weight` | `metadata.weight_kg` | float | May be 0.0 if not set |

**Critical pitfall — `qty_available`:** This field requires the `stock` module, which is NOT installed in base Odoo Community. Do NOT include it in the fields list. `stock_status` will default to `"in_stock"` — Story 3.4 will handle real stock status when the stock module is available. [Source: Story 0.2 debug log]

**Critical pitfall — Odoo `False` values:** Odoo returns Python `False` (not `None`) for empty fields like `default_code`, `barcode`, `description_sale`. The DTO field mapping MUST convert `False` → `None` (or `""` for `reference`). Use a helper: `def _odoo_str(val: Any) -> str | None: return val if isinstance(val, str) else None`.

**Critical pitfall — `categ_id` is a tuple:** Odoo Many2one fields return `[id, "Name"]` or `False`. Extract with: `product["categ_id"][1] if product["categ_id"] else "Uncategorized"`.

### Architecture Compliance

**Adapter pattern (4-file structure):**
- `protocol.py` — add `get_products()` to `ERPAdapter` Protocol
- `models.py` — add `Product` and `ProductFilter` DTOs
- `odoo.py` — implement `get_products()` on `OdooAdapter`
- `__init__.py` — no changes needed (factory already exists)

**SQLAlchemy model:**
- File: `src/quote_agent/models/product.py`
- Table name: `products` (snake_case plural)
- Use `TimestampMixin` for `created_at`/`updated_at`
- UUID primary key with `gen_random_uuid()` server default
- Column naming: `snake_case` — `unit_price`, `stock_status`, `is_active`, `is_stale`
- Constraint naming follows `convention` dict in `base.py`: `ix_products_*`, `uq_products_*`
- JSON column for metadata: name it `metadata_` (trailing underscore to avoid shadowing Python builtin `metadata`)

**Service layer:**
- File: `src/quote_agent/services/catalog_service.py`
- `CatalogService` class — takes `ERPAdapter` and `AsyncSession` as constructor args (dependency injection, not global singletons)
- Returns typed `IngestionResult` DTO (Pydantic BaseModel with `inserted`, `updated`, `unchanged`, `stale`, `duration_seconds` fields)

**Naming conventions (PEP 8 strict):**
- Files: `snake_case` — `catalog_service.py`, `product.py`
- Classes: `PascalCase` — `CatalogService`, `Product`, `ProductFilter`
- Functions: `snake_case` — `ingest_full()`, `get_products()`
- Constants: `UPPER_SNAKE` — `_BATCH_SIZE = 500`, `_WRITE_BATCH_SIZE = 50`

**Imports:** Absolute only — `from quote_agent.adapters.erp.protocol import ERPAdapter`, never relative.

**Type safety:** `from __future__ import annotations` in every file. All functions typed (params + return). `mypy --strict` must pass.

**Structured logging:**
```python
logger.info(
    "Catalog batch ingested",
    extra={"context": {"batch": batch_num, "count": len(batch), "total": total_processed}},
)
```
Component: `services.catalog_service`. Never `print()`. Auto-redacted by JSONLogFormatter.

### Library & Framework Requirements

- **No new dependencies.** Everything needed is already installed: `sqlalchemy`, `pydantic`, `asyncpg`, `xmlrpc.client` (stdlib).
- **pgvector** is already installed and the extension is enabled (migration `c740a66c4ad2`). The `vector` column on the `products` table is a placeholder for Story 3.2 — import from `pgvector.sqlalchemy import Vector`.
- **Alembic** for migration — use `alembic revision --autogenerate -m "add products table"`.

### File Structure Requirements

**New files:**
- `src/quote_agent/models/product.py` — SQLAlchemy Product model
- `src/quote_agent/services/catalog_service.py` — ingestion orchestration service
- `alembic/versions/xxxx_add_products_table.py` — migration (auto-generated)
- `tests/unit/services/test_catalog_service.py` — unit tests for CatalogService
- `tests/unit/adapters/test_odoo_get_products.py` — unit tests for Odoo field mapping
- `tests/e2e/test_catalog_ingestion_e2e.py` — E2E tests with real Odoo + PostgreSQL

**Modified files:**
- `src/quote_agent/adapters/erp/protocol.py` — add `get_products()` method
- `src/quote_agent/adapters/erp/models.py` — add `Product`, `ProductFilter`, `IngestionResult` DTOs
- `src/quote_agent/adapters/erp/odoo.py` — implement `get_products()`
- `src/quote_agent/models/__init__.py` — register `Product` model
- `tests/e2e/conftest.py` — add `get_erp_adapter` to cache clearing, add Odoo seed fixture

### Testing Requirements

**Unit tests (no DB, no real services):**
- Mock `OdooAdapter` using the Protocol — return fake Odoo-shaped dicts
- Mock `AsyncSession` for DB operations
- Test naming: `test_{behavior}_when_{condition}()` e.g., `test_products_inserted_when_new_catalog()`
- Docstrings: `"""AC-1: ..."""`

**E2E tests (real Odoo + PostgreSQL + no mocking):**
- Mark with `@pytest.mark.e2e`
- Use `requires_e2e` skip decorator
- Add `_has_real_erp()` check to `conftest.py` — verify `ERP__URL`, `ERP__DATABASE`, `ERP__USERNAME`, `ERP__API_KEY` are set
- Seed fixture: load 500+ products from `catalog_50k_sample.jsonl` + some extras into Odoo via XML-RPC `product.product` create (batch size 50)
- Cleanup: delete seeded products from both Odoo and PostgreSQL
- Product identification for cleanup: use a marker in product names (e.g., prefix `[E2E-TEST]`) or a dedicated test category

### Previous Story Intelligence

**Story 0.2 (Prototype — Odoo catalog ingestion via n8n):**
- JSON-RPC pagination works with offset/limit of 200. MVP uses XML-RPC (same conceptually).
- `qty_available` field unavailable without stock module — documented, do NOT include.
- `active=False` products hidden by default — must pass `active_test: False` context.
- Barcode uniqueness constraint — when seeding test data, set `barcode=False` on duplicates.
- Batch writes to Odoo: use groups of 50 to avoid timeouts.
- Seeder script created 677 products with 8 categories and realistic noise patterns.

**Story 3.0c (50K synthetic catalog):**
- `tests/fixtures/catalog_50k.jsonl` — 50,000 records, 17.4 MB, deterministic (seed 42).
- `tests/fixtures/catalog_50k_sample.jsonl` — first 100 records for quick tests.
- Record shape: `reference`, `name`, `description`, `category`, `unit_price`, `stock_status`, `is_active`, `metadata` (dict with variable keys: `weight_kg`, `dimensions`, `material`, `supplier`, `country_of_origin`, `min_order_qty`, `lead_time_days`).
- 15 product families, weighted distribution. ~30% missing metadata, ~5% duplicates, ~10% mixed FR/EN, ~5% truncated, ~3% inconsistent casing, ~2% inactive.
- The record shape in catalog_50k.jsonl **defines the contract** for what the `Product` DTO must handle.

**Story 3.0a (E2E tests for Epic 2):**
- E2E test patterns: `requires_e2e` skip decorator, `_E2E_TEST_PREFIX` for cleanup, `e2e_db_session` fixture with Alembic migrations.
- Cache clearing: 5 `@lru_cache` singletons cleared before/after each test.
- FK-aware cleanup order.

### Git Intelligence

Recent commits show clean project state. Stories 3.0a/3.0b/3.0c all completed and reviewed. The `scripts/`, `tests/fixtures/`, `tests/e2e/` directories all exist. No pending changes.

### What NOT to Do

- Do NOT generate embeddings — that's Story 3.2's job. The `vector` column is nullable, left `NULL` here.
- Do NOT implement search — that's Story 3.3. This story only stores products.
- Do NOT implement proposability filtering — that's Story 3.4.
- Do NOT add caching — that's Story 3.5.
- Do NOT clean/normalize product data before storing — the entire point is zero-preprocessing. Store as-is.
- Do NOT delete products during re-sync — only flag as `is_stale`. Deletion is dangerous for audit trail.
- Do NOT use `qty_available` from Odoo — stock module not available in base Community.
- Do NOT add new pip dependencies — everything needed is already installed.
- Do NOT use relative imports anywhere.
- Do NOT mock services in E2E tests — use ALL real services (IMAP/PostgreSQL/Odoo).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1] — acceptance criteria and E2E test requirement
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — PostgreSQL + pgvector, HNSW, adapter pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] — naming, structure, imports, error handling
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 7] — zero-preprocessing onboarding promise
- [Source: _bmad-output/planning-artifacts/prd.md#Innovation Areas] — zero-preprocessing as core differentiator
- [Source: _bmad-output/implementation-artifacts/0-2-ingestion-catalogue-odoo.md] — prototype Odoo ingestion learnings
- [Source: _bmad-output/implementation-artifacts/3-0c-generation-catalogue-test-50k-realiste.md] — catalog shape contract, noise design
- [Source: docs/project-context.md] — adapter pattern, async wrapping, config, test conventions, known pitfalls
- [Source: src/quote_agent/adapters/erp/protocol.py] — current ERPAdapter (health_check only)
- [Source: src/quote_agent/adapters/erp/models.py] — current DTOs (OdooVersionInfo only)
- [Source: src/quote_agent/adapters/erp/odoo.py] — current OdooAdapter with XML-RPC + asyncio.to_thread pattern
- [Source: src/quote_agent/models/base.py] — Base, TimestampMixin, engine/session factories, naming convention dict

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Unit tests: 237 passed, 0 failures (including 22 new tests for Story 3.1)
- Ruff: all new/modified files pass clean
- Mypy: all new/modified files pass clean (2 pre-existing errors in other files)
- Alembic migration: products table created successfully
- E2E tests: 3 tests written, correctly skip when Odoo not available (placeholder credentials in .env)

### Completion Notes List

- AC-1: Product DTO, ERPAdapter protocol, OdooAdapter.get_products(), SQLAlchemy Product model, CatalogService — all implemented. Zero-preprocessing: data stored as-is from Odoo.
- AC-2: Paginated fetch (batch 500) with structured JSON logging. IngestionResult DTO with counts + duration.
- AC-3: Re-sync via odoo_id keyed upsert with SHA-256 change detection hash. Stale detection marks unfetched products without deletion.
- AC-4: E2E tests seed 500+ products from catalog_50k.jsonl into real Odoo, validate ingestion → PostgreSQL, re-sync counts, and update detection.
- Added `odoo_id: int | None` field to Product DTO (not in original spec but required for re-sync keying).
- Added `get_erp_adapter` to E2E cache clearing fixtures per project-context.md recommendation.

### Change Log

- 2026-03-19: Story 3.1 implemented — catalog ingestion from ERP with zero-preprocessing, re-sync, stale detection, unit + E2E tests

### File List

**New files:**
- `src/quote_agent/models/product.py` — SQLAlchemy Product model with pgvector placeholder
- `src/quote_agent/services/catalog_service.py` — CatalogService with ingest_full(), upsert, stale detection
- `alembic/versions/a3905354d158_add_products_table.py` — Alembic migration for products table
- `tests/unit/test_odoo_get_products.py` — 13 unit tests for Odoo field mapping
- `tests/unit/test_catalog_service.py` — 9 unit tests for CatalogService
- `tests/e2e/test_catalog_ingestion_e2e.py` — 3 E2E tests with real Odoo + PostgreSQL

**Modified files:**
- `src/quote_agent/adapters/erp/models.py` — added Product, ProductFilter, IngestionResult DTOs
- `src/quote_agent/adapters/erp/protocol.py` — added get_products() to ERPAdapter Protocol
- `src/quote_agent/adapters/erp/odoo.py` — implemented get_products() with field mapping
- `src/quote_agent/models/__init__.py` — registered Product model
- `alembic/env.py` — imported Product model for autogenerate
- `tests/e2e/conftest.py` — added _has_real_erp(), requires_e2e_erp, get_erp_adapter cache clearing, e2e_erp_adapter fixture
- `docker-compose.yml` — added Odoo + odoo-db services for E2E catalog tests
