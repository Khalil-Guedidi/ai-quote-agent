# Story 3.2: Génération d'Embeddings & Index Vectoriel

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator (Laurent)**,
I want product data to be embedded into vectors and indexed for semantic search,
So that the agent can find products by meaning, not just exact text match.

## Acceptance Criteria

1. **AC-1: Embedding generation for all products**
   - Given products are ingested into the `products` table (Story 3.1)
   - When embedding generation runs
   - Then each product receives a vector embedding using the configured multilingual model (BGE-M3 by default)
   - And embeddings are stored in the `products.vector` column via pgvector
   - And products with `is_stale = True` are skipped (no embedding wasted on stale data)

2. **AC-2: 50K-scale performance**
   - Given a catalog with 50,000 product references
   - When embedding generation runs
   - Then it completes successfully without memory or performance issues
   - And progress is logged with structured JSON (batch count, total embedded, elapsed time)
   - And embeddings are generated in batches (not one-by-one) for GPU/CPU efficiency

3. **AC-3: HNSW vector index with < 3s search**
   - Given 50,000 products are embedded
   - When the HNSW index is built (via Alembic migration)
   - Then vector similarity search returns results in < 3 seconds (NFR-P2)
   - And the index uses cosine distance (`vector_cosine_ops`) for normalized embeddings

4. **AC-4: Configurable embedding model**
   - Given the embedding model is configurable via `EMBEDDING__MODEL_NAME`
   - When the operator changes the embedding model in configuration
   - Then the system uses the new model without code changes
   - And re-embedding can be triggered for the full catalog (nullify all vectors, re-run)

5. **AC-5: E2E test with real PostgreSQL**
   - Given the 50K synthetic catalog from `tests/fixtures/catalog_50k_sample.jsonl` (100 products)
   - When products are inserted into PostgreSQL and embedding generation runs
   - Then all 100 products have non-null `vector` columns of correct dimension
   - And cosine similarity search returns semantically relevant results (e.g., "tube inox" matches "TUBE ROND SS 304L")

## Tasks / Subtasks

- [x] Task 1: Fix vector column dimension — BGE-M3 outputs 1024, not 1536 (AC: 1, 3)
  - [x] 1.1: Create Alembic migration to `ALTER COLUMN vector TYPE vector(1024)` on `products` table
  - [x] 1.2: Update `Product` SQLAlchemy model: `Vector(dim=1024)` → make dimension configurable via settings
  - [x] 1.3: Drop any existing data in `vector` column (all NULL currently, no data loss)

- [x] Task 2: Add `EmbeddingSettings` to configuration (AC: 4)
  - [x] 2.1: Add `EmbeddingSettings` to `config.py`: `model_name` (str, default `"BAAI/bge-m3"`), `embedding_dim` (int, default `1024`), `batch_size` (int, default `64`), `device` (str, default `"cpu"`)
  - [x] 2.2: Add `embedding: EmbeddingSettings` field to `Settings`
  - [x] 2.3: Verify env var mapping: `EMBEDDING__MODEL_NAME`, `EMBEDDING__EMBEDDING_DIM`, `EMBEDDING__BATCH_SIZE`, `EMBEDDING__DEVICE`

- [x] Task 3: Implement embedding adapter (4-file pattern) (AC: 1, 4)
  - [x] 3.1: Create `adapters/embedding/protocol.py` — `EmbeddingAdapter` Protocol with `embed_texts(texts: list[str]) -> list[list[float]]` and `health_check() -> ServiceHealth`
  - [x] 3.2: Create `adapters/embedding/models.py` — `EmbeddingRequest`, `EmbeddingResult` DTOs
  - [x] 3.3: Create `adapters/embedding/sentence_transformers.py` — `SentenceTransformerAdapter` using `sentence-transformers` library, batch encoding with `model.encode(texts, batch_size=..., normalize_embeddings=True, show_progress_bar=False)`
  - [x] 3.4: Create `adapters/embedding/__init__.py` — `get_embedding_adapter()` factory with `@lru_cache(maxsize=1)`
  - [x] 3.5: Add health check: verify model loads successfully, return `ServiceHealth`

- [x] Task 4: Add `sentence-transformers` dependency (AC: 1)
  - [x] 4.1: `uv add sentence-transformers` — adds torch + transformers + sentence-transformers
  - [x] 4.2: Verify no version conflicts with existing dependencies (langchain-*, pydantic, etc.)

- [x] Task 5: Create `EmbeddingService` for batch embedding orchestration (AC: 1, 2)
  - [x] 5.1: Create `src/quote_agent/services/embedding_service.py` with `EmbeddingService` class
  - [x] 5.2: Constructor takes `EmbeddingAdapter` and `AsyncSession` (dependency injection)
  - [x] 5.3: Implement `embed_all()` method: fetch products with `vector IS NULL AND is_stale = False`, build text representations, embed in batches, update DB
  - [x] 5.4: Implement `embed_batch()` for a specific list of product IDs
  - [x] 5.5: Implement `reset_embeddings()` — sets all `vector = NULL` for re-embedding after model change
  - [x] 5.6: Text building function: `_build_product_text(product) -> str` concatenates `name | Ref: reference | category | description`
  - [x] 5.7: Structured logging: batch progress, total embedded, duration. Component: `services.embedding_service`
  - [x] 5.8: Return `EmbeddingResult` DTO with counts (embedded, skipped_stale, errors) and duration

- [x] Task 6: Create HNSW index via Alembic migration (AC: 3)
  - [x] 6.1: Create migration: `CREATE INDEX ix_products_vector_hnsw ON products USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 64)`
  - [x] 6.2: Index is safe to create on empty or populated table (HNSW builds incrementally)
  - [x] 6.3: Downgrade: `DROP INDEX ix_products_vector_hnsw`

- [x] Task 7: Unit tests (AC: 1, 2, 4)
  - [x] 7.1: Test `EmbeddingAdapter` protocol compliance — mock adapter returns correct shape vectors
  - [x] 7.2: Test `_build_product_text()` — products with/without description, empty reference, special characters
  - [x] 7.3: Test `EmbeddingService.embed_all()` — mock adapter + mock session, verify batching, stale skipping, DB updates
  - [x] 7.4: Test `EmbeddingService.reset_embeddings()` — verify all vectors set to NULL
  - [x] 7.5: Test `EmbeddingSettings` configuration — defaults, env overrides
  - [x] 7.6: Test `SentenceTransformerAdapter` initialization — model name, dimension validation

- [x] Task 8: E2E test with real PostgreSQL + real embedding model (AC: 5)
  - [x] 8.1: E2E test: insert 100 products from `catalog_50k_sample.jsonl`, run `embed_all()`, verify all have non-null vectors of dimension 1024
  - [x] 8.2: E2E test: run cosine similarity query — `SELECT * FROM products ORDER BY vector <=> $query_vector LIMIT 5` — verify semantic relevance
  - [x] 8.3: E2E test: verify stale products are skipped (insert a stale product, run embed_all, confirm vector is NULL)
  - [x] 8.4: Cleanup: delete test products after tests

## Dev Notes

### Critical: Vector Dimension Mismatch

**The current `products.vector` column is `Vector(dim=1536)` but BGE-M3 outputs 1024 dimensions.** 1536 is the OpenAI `text-embedding-3-small` dimension. Since the architecture specifies local multilingual models by default (BGE-M3 or multilingual-e5-large), both of which output 1024 dimensions, the column must be altered.

**Migration approach:** `ALTER TABLE products ALTER COLUMN vector TYPE vector(1024)`. Since the column is currently all NULLs (Story 3.1 left it empty by design), this is a safe, zero-data-loss change.

### Technical Requirements

**Embedding model — BGE-M3 (BAAI/bge-m3):**
- Output dimension: **1024** (not 1536)
- Max input tokens: **8192** (more than enough for product text)
- Multilingual: 100+ languages including French — critical for French industrial catalogs
- Architecture: XLM-RoBERTa-large, 568M parameters
- Usage via sentence-transformers:
  ```python
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer("BAAI/bge-m3")
  embeddings = model.encode(texts, normalize_embeddings=True, batch_size=64)
  # embeddings.shape → (len(texts), 1024)
  ```
- **Always normalize embeddings** (`normalize_embeddings=True`) — required for cosine similarity to work correctly with pgvector

**Text concatenation for embedding — follow prototype pattern:**
```python
def _build_product_text(product: Product) -> str:
    parts = [product.name]
    if product.reference:
        parts.append(f"Ref: {product.reference}")
    parts.append(product.category)
    if product.description:
        parts.append(product.description)
    return " | ".join(parts)
```
This produces text like: `"TUBE ROND SS 304L 25x1.5 LG6000 | Ref: TUB-304L-025 | Tubes & Tuyaux | Tube rond acier inoxydable 304L..."`. The `|` separator helps the model distinguish fields.

**Batching strategy for 50K products:**
- Fetch from DB: batches of 500 (same as CatalogService pattern)
- Encode: batches of 64 (sentence-transformers `batch_size` param — balances RAM/speed)
- DB update: flush every 50 products (same write batch size as CatalogService)
- Total expected time: ~10-30 minutes on CPU for 50K products (model loading ~30s, encoding ~0.5s/batch of 64)

**pgvector HNSW index:**
- Operator: `vector_cosine_ops` (for cosine distance) — matches normalized embeddings
- Parameters: `m=16`, `ef_construction=64` (pgvector defaults, good for 50K vectors)
- HNSW indexes can be created before data is inserted — they build incrementally
- Query syntax: `ORDER BY vector <=> query_vector` (cosine distance operator in pgvector)
- For search-time recall tuning: `SET hnsw.ef_search = 100` (default 40, increase for better recall)

### Architecture Compliance

**Adapter pattern (4-file structure):**
- `protocol.py` — `EmbeddingAdapter` Protocol with `@runtime_checkable`
- `models.py` — `EmbeddingRequest`, `EmbeddingResult` Pydantic DTOs
- `sentence_transformers.py` — `SentenceTransformerAdapter` implementation
- `__init__.py` — `get_embedding_adapter()` factory with `@lru_cache(maxsize=1)`

**Service layer:**
- File: `src/quote_agent/services/embedding_service.py`
- `EmbeddingService` class — takes `EmbeddingAdapter` and `AsyncSession` as constructor args (dependency injection)
- Returns typed `EmbeddingResult` DTO

**Sentence-transformers is synchronous** — the `model.encode()` call blocks. Wrap with `asyncio.to_thread()` following the established async wrapping pattern:
```python
vectors = await asyncio.to_thread(
    self._model.encode,
    texts,
    batch_size=self._batch_size,
    normalize_embeddings=True,
    show_progress_bar=False,
)
```

**Naming conventions (PEP 8 strict):**
- Files: `snake_case` — `embedding_service.py`, `sentence_transformers.py`
- Classes: `PascalCase` — `EmbeddingService`, `SentenceTransformerAdapter`, `EmbeddingSettings`
- Functions: `snake_case` — `embed_all()`, `embed_batch()`, `_build_product_text()`
- Constants: `UPPER_SNAKE` — `_FETCH_BATCH_SIZE = 500`, `_WRITE_BATCH_SIZE = 50`

**Imports:** Absolute only — `from quote_agent.adapters.embedding.protocol import EmbeddingAdapter`

**Type safety:** `from __future__ import annotations` in every file. All functions typed. `mypy --strict` must pass.

**Structured logging:**
```python
logger.info(
    "Embedding batch generated",
    extra={"context": {"batch": batch_num, "count": len(batch), "total": total_embedded}},
)
```
Component: `services.embedding_service`. Never `print()`.

### Library & Framework Requirements

- **New dependency: `sentence-transformers`** — adds `torch`, `transformers`, `huggingface-hub`. This is a significant dependency (~2GB disk for model + torch). Install via `uv add sentence-transformers`.
- **No other new dependencies.** pgvector, SQLAlchemy, Alembic, pydantic already installed.
- **Model download:** First `SentenceTransformer("BAAI/bge-m3")` call downloads ~2.3GB model from HuggingFace Hub. Cache location: `~/.cache/huggingface/` by default. For Docker: set `SENTENCE_TRANSFORMERS_HOME` or `HF_HOME` env var to persistent volume.

### File Structure Requirements

**New files:**
- `src/quote_agent/adapters/embedding/protocol.py` — EmbeddingAdapter Protocol
- `src/quote_agent/adapters/embedding/models.py` — DTOs
- `src/quote_agent/adapters/embedding/sentence_transformers.py` — SentenceTransformerAdapter
- `src/quote_agent/services/embedding_service.py` — EmbeddingService orchestration
- `alembic/versions/xxxx_fix_vector_dim_and_add_hnsw_index.py` — migration
- `tests/unit/test_embedding_service.py` — unit tests
- `tests/unit/test_embedding_adapter.py` — adapter unit tests
- `tests/e2e/test_embedding_e2e.py` — E2E tests

**Modified files:**
- `src/quote_agent/adapters/embedding/__init__.py` — add factory function
- `src/quote_agent/config.py` — add `EmbeddingSettings`
- `src/quote_agent/models/product.py` — change `Vector(dim=1536)` → `Vector(dim=1024)` (or dynamic from settings)
- `pyproject.toml` — add `sentence-transformers` dependency
- `tests/e2e/conftest.py` — add `get_embedding_adapter` to cache clearing

### Testing Requirements

**Unit tests (no DB, no real model):**
- Mock `EmbeddingAdapter` — return fake vectors of correct shape `(n, 1024)`
- Mock `AsyncSession` for DB operations
- Test naming: `test_{behavior}_when_{condition}()` e.g., `test_stale_products_skipped_when_embedding()`
- Docstrings: `"""AC-1: ..."""`

**E2E tests (real PostgreSQL + real embedding model):**
- Mark with `@pytest.mark.e2e`
- Use `requires_e2e` skip decorator
- Real `SentenceTransformerAdapter` with BGE-M3 (downloads model on first run)
- Insert products from `catalog_50k_sample.jsonl` into real PostgreSQL
- Verify: vector dimensions, cosine similarity relevance, stale skipping
- Cleanup: delete test products after tests
- **Note:** E2E tests with real model may take ~60s due to model loading + encoding. Consider a `requires_e2e_embedding` skip decorator that checks model availability.

### Previous Story Intelligence

**Story 3.1 (Catalog Ingestion — just completed):**
- `Product` model created with `vector` column as nullable placeholder — exactly for this story
- `CatalogService.ingest_full()` populates all columns except `vector` — embedding is a separate step
- `odoo_id` field used for re-sync keying — embedding should be regenerated when product data changes
- `is_stale` flag — stale products should NOT be embedded (waste of compute)
- SHA-256 hash used for change detection — if a product's data changes, its embedding should be regenerated (set vector to NULL, re-embed)
- E2E test patterns: `_has_real_erp()` check, `requires_e2e_erp` decorator, cleanup with marker prefix
- `IngestionResult` DTO pattern — follow same pattern for `EmbeddingResult`

**Story 3.0c (50K Synthetic Catalog):**
- `tests/fixtures/catalog_50k_sample.jsonl` — 100 products for quick tests
- Record shape: `reference`, `name`, `description`, `category`, `unit_price`, `stock_status`, `is_active`, `metadata`
- Text is French industrial with noise — good test material for multilingual embeddings

**Prototype (Story 0.2-0.4):**
- Prototype used `SentenceTransformer("BAAI/bge-m3")` for dense embeddings + `SparseTextEmbedding("Qdrant/bm25")` for sparse
- Prototype stored in Qdrant (external) — this story uses pgvector (internal, simpler)
- Text concatenation: `name | Ref: reference | category | description` — proven effective, reuse
- `normalize_embeddings=True` critical for cosine similarity

### Git Intelligence

Recent commits show clean project state. Story 3.1 just completed: `2c28257 feat: add ERP catalog ingestion with zero-preprocessing, re-sync, and stale detection (Story 3.1)`. Products table exists with vector column placeholder. All tests passing.

### What NOT to Do

- Do NOT implement search queries — that's Story 3.3's job. This story only generates embeddings and creates the HNSW index.
- Do NOT implement proposability filtering — that's Story 3.4.
- Do NOT implement caching — that's Story 3.5.
- Do NOT implement sparse/BM25 embeddings — that's part of Story 3.3's hybrid search.
- Do NOT use the LLM adapter for embeddings — use the dedicated embedding adapter with sentence-transformers.
- Do NOT store embeddings in a separate table — use the existing `products.vector` column.
- Do NOT skip stale products silently — log them as skipped.
- Do NOT add re-ranking logic — that's Story 3.3/3.6.
- Do NOT use Qdrant or any external vector DB — pgvector is the architectural choice.
- Do NOT use relative imports anywhere.
- Do NOT mock services in E2E tests — use ALL real services.

### Project Structure Notes

- Embedding adapter goes in `src/quote_agent/adapters/embedding/` — directory already exists (scaffolded)
- Service goes in `src/quote_agent/services/embedding_service.py` — alongside `catalog_service.py`
- No conflicts with existing structure detected
- The `search/` directory remains empty — that's Story 3.3

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2] — acceptance criteria, model choice, performance requirements
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — PostgreSQL + pgvector, HNSW, embedding model choice (BGE-M3 or multilingual-e5-large), configurable
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] — adapter pattern, naming, imports, structured logging
- [Source: _bmad-output/planning-artifacts/architecture.md#Adapter Organization] — protocol.py + {impl}.py + models.py pattern
- [Source: docs/project-context.md] — async wrapping, cache clearing, test conventions, known pitfalls
- [Source: src/quote_agent/models/product.py] — current Product model with Vector(dim=1536) placeholder
- [Source: src/quote_agent/services/catalog_service.py] — batching pattern, IngestionResult DTO pattern
- [Source: src/quote_agent/adapters/embedding/__init__.py] — empty scaffold, ready for implementation
- [Source: prototype/scripts/generate-embeddings.py] — text concatenation pattern, BGE-M3 usage, normalize_embeddings=True
- [Source: alembic/versions/a3905354d158_add_products_table.py] — current migration with Vector(dim=1536)
- [Source: alembic/versions/c740a66c4ad2_enable_pgvector_extension.py] — pgvector extension already enabled
- [Source: BAAI/bge-m3 HuggingFace] — 1024 dimensions, 568M params, 8192 max tokens, multilingual

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- All 254 unit tests pass (17 new embedding tests + 237 existing, zero regressions)
- All 3 E2E embedding tests pass with real PostgreSQL + real BGE-M3 model (37s total)
- Ruff: all checks passed
- mypy --strict: no issues found (6 source files checked)
- Post-review: 258 unit tests pass (21 embedding tests + 237 existing), ruff clean, mypy clean

### Completion Notes List

- Task 1: Created Alembic migration `78fc0a54b3b9` to alter vector column from 1536 to 1024 dimensions (BGE-M3) and add HNSW index in a single migration. Updated Product model accordingly.
- Task 2: Added `EmbeddingSettings` to config with `model_name`, `embedding_dim`, `batch_size`, `device` — all configurable via `EMBEDDING__*` env vars.
- Task 3: Implemented 4-file embedding adapter pattern: `protocol.py` (runtime_checkable Protocol), `models.py` (EmbeddingRequest/EmbeddingResult DTOs), `sentence_transformers.py` (SentenceTransformerAdapter with lazy model loading, asyncio.to_thread wrapping, 30s health check caching), `__init__.py` (get_embedding_adapter factory with lru_cache).
- Task 4: Added `sentence-transformers==5.3.0` dependency (brings torch, transformers, etc.). No version conflicts.
- Task 5: Created `EmbeddingService` with `embed_all()` (batch fetch/embed/update with stale skipping), `embed_batch()` (specific product IDs), `reset_embeddings()` (nullify all vectors for re-embedding). Structured logging throughout.
- Task 6: HNSW index combined into Task 1 migration — `ix_products_vector_hnsw` using `vector_cosine_ops` with m=16, ef_construction=64.
- Task 7: 17 unit tests covering protocol compliance, text building (4 edge cases), embed_all batching/stale-skipping/error-handling, reset_embeddings, settings defaults/overrides, adapter initialization.
- Task 8: 3 E2E tests — 100-product embedding with dimension verification, cosine similarity search, stale product skipping. All use real PostgreSQL + real BGE-M3 model.

### Change Log

- 2026-03-19: Story 3.2 implementation complete — embedding generation, HNSW index, adapter pattern, unit + E2E tests
- 2026-03-19: Code review fixes — added dimension validation in adapter, optimized stale count to DB-side query, failure-safe E2E cleanup, added embed_batch unit tests

### File List

**New files:**
- `src/quote_agent/adapters/embedding/protocol.py`
- `src/quote_agent/adapters/embedding/models.py`
- `src/quote_agent/adapters/embedding/sentence_transformers.py`
- `src/quote_agent/services/embedding_service.py`
- `alembic/versions/78fc0a54b3b9_fix_vector_dim_1024_and_add_hnsw_index.py`
- `tests/unit/test_embedding_adapter.py`
- `tests/unit/test_embedding_service.py`
- `tests/e2e/test_embedding_e2e.py`

**Modified files:**
- `src/quote_agent/adapters/embedding/__init__.py`
- `src/quote_agent/config.py`
- `src/quote_agent/models/product.py`
- `pyproject.toml`
- `uv.lock`
- `tests/e2e/conftest.py`
