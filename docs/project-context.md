# Project Context — ai-quote-agent

<!-- last_updated: 2026-03-23 -->

Internal developer reference for established patterns, known pitfalls, conventions, and quality gates.
Derived from Epics 1-5.5 implementation and retrospectives.

---

## Quick Reference

- **Adapter Pattern**: `protocol.py` (@runtime_checkable Protocol) + `models.py` (Pydantic DTOs) + `{impl}.py` + `__init__.py` (factory with `@lru_cache(maxsize=1)`)
- **LLM calls**: `model.with_structured_output(PydanticModel)` then `await asyncio.wait_for(structured.ainvoke(messages), timeout=10.0)`
- **Async wrapping**: `await asyncio.to_thread(sync_function, *args)` for sync stdlib (xmlrpc, imaplib)
- **Security layers**: sanitizer (detect+escape) → input_isolation (delimiters) → log_redactor ([REDACTED_*]) → JSONLogFormatter (auto-redaction)
- **Pipeline flow**: `_persist_emails()` processes inline: received → cleaned → extracted → split, with per-step error handling
- **Config**: pydantic-settings with `__` nested delimiter, `get_settings()` cached singleton
- **Imports**: absolute only (`from quote_agent.adapters.erp.protocol import ERPAdapter`), never relative
- **Type safety**: `mypy --strict` with zero issues, `from __future__ import annotations` in every file
- **Tests**: `pytest-asyncio` with `asyncio_mode = "auto"`, E2E excluded by default (`-m 'not e2e'`)
- **Naming**: PEP 8 strict — `snake_case` files/functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants
- **DB naming**: `snake_case` plural tables, `{singular}_id` FKs, prefix conventions: `ix_/uq_/ck_/fk_/pk_`
- **Test naming**: `test_{behavior}_when_{condition}()` or `test_{behavior}_e2e()`
- **Severity comparison**: never use `max()` or lexicographic comparison on severity strings — use explicit conditional chains
- **Cache clearing**: clear ALL `@lru_cache` singletons between E2E tests (8 functions: get_settings, create_async_engine_from_settings, _get_session_factory, get_llm_adapter, get_email_adapter, get_erp_adapter, get_embedding_adapter, get_notification_adapter)
- **Health checks**: 30s TTL caching with `time.monotonic()`, `asyncio.wait_for(..., timeout=5.0)`
- **Fire-and-forget**: notification nodes never block pipeline, never set `state["error"]` — log failures silently
- **Graph node**: set `current_node` at entry + all return paths, error handling returns state — never raises
- **Scheduler**: pure asyncio, `@lru_cache` singleton, conditional startup in FastAPI lifespan
- **DoD gates**: mypy strict, ruff, pytest unit, CI green, E2E (when applicable) — all mandatory before merge
- **Graph node checklist**: 5 items when creating/copying nodes (see Conventions)

---

## Established Patterns

### Adapter Pattern

Every external integration follows a 4-file structure:

```
adapters/{service}/
├── protocol.py      # @runtime_checkable Protocol interface
├── models.py        # Pydantic BaseModel DTOs
├── {impl}.py        # Concrete implementation
└── __init__.py      # Factory with @lru_cache(maxsize=1)
```

**Protocol** — defines the contract with `@runtime_checkable`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMAdapter(Protocol):
    async def invoke(self, request: LLMRequest) -> LLMResponse: ...
    async def health_check(self) -> ServiceHealth: ...
```

**Factory** — cached singleton, lazy imports:

```python
@lru_cache(maxsize=1)
def get_llm_adapter() -> OpenAICompatAdapter:
    from quote_agent.adapters.llm.openai_compat import OpenAICompatAdapter
    from quote_agent.config import get_settings
    return OpenAICompatAdapter(get_settings().llm)
```

**6 implemented adapters**: LLM (`openai_compat.py`), ERP (`odoo.py`), Email (`imap.py`), Notification (`teams.py` + `log.py`), Embedding (`sentence_transformers.py`). Notification adapter uses a factory that routes by `settings.notification.channel` (teams/log).

**Health check pattern** — all adapters:
- Instance-level caching: `_last_health`, `_last_health_time`
- 30s TTL via `time.monotonic()`
- `asyncio.wait_for(..., timeout=5.0)` wrapping (except `TeamsAdapter` which uses httpx's native timeout)
- Returns `ServiceHealth(status="unhealthy", error=...)` on failure — never raises

### LLM Structured Output Pattern

```python
structured = model.with_structured_output(ExtractionResult)
result = await asyncio.wait_for(
    structured.ainvoke(messages),
    timeout=10.0,
)
```

- `with_structured_output(PydanticModel)` guarantees Pydantic-conformant output
- No manual JSON parsing needed
- Always wrap with `asyncio.wait_for` for timeout protection
- Catch `LLMTimeoutError` and `AdapterError` specifically

### Pipeline Integration Pattern

`EmailPollerService._persist_emails()` processes emails through 4 stages inline:

```
received → cleaned → extracted → split
```

**Per-step error handling:**
- Each stage checks previous status before executing (e.g., extraction only runs if `status == "cleaned"`)
- Stage failures set appropriate status (`cleaning_failed`, `extraction_failed`)
- Split has graceful degradation: if LLM splitting fails, creates single QuoteRequest from extraction data
- Database savepoints per email (`session.begin_nested()`) prevent one failure from rolling back the batch

**Status transitions:**
```
received → cleaned → extracted → split
    ↓           ↓           ↓
cleaning_failed  extraction_failed  (split falls back gracefully)
```

### Security Layer Pattern

4 separate modules with distinct responsibilities:

| Layer | Module | Input → Output | Purpose |
|-------|--------|----------------|---------|
| 1 | `sanitizer.py` | Raw text → `[SANITIZED: ...]` escaped | Detect & neutralize prompt injection |
| 2 | `input_isolation.py` | Sanitized text → delimited + system prompt | Structural boundary enforcement |
| 3 | `log_redactor.py` | Log context → `[REDACTED_*]` placeholders | Remove confidential data from logs |
| 4 | `audit/logger.py` | Log record → JSON with auto-redaction | Uniform structured output |

**Sanitizer threat categories**: role impersonation (HIGH), instruction override (HIGH), prompt leaking (MEDIUM), role switching (MEDIUM), delimiter injection (MEDIUM). Includes French-language patterns.

**Replacement technique**: sort matches by position descending, replace in reverse order to prevent index shifting.

**Input isolation delimiters**:
```
<<<UNTRUSTED_EMAIL_CONTENT_START>>>
{sanitized content}
<<<UNTRUSTED_EMAIL_CONTENT_END>>>
```

**Log redactor categories**: email → `[REDACTED_EMAIL]`, phone → `[REDACTED_PHONE]`, price → `[REDACTED_PRICE]`, IBAN → `[REDACTED_IBAN]`.

**JSONLogFormatter** auto-applies `redact_context()` to all `extra["context"]` dicts — developers don't manually redact.

### Async Pattern

Two variants depending on library support:

**Native async** (LangChain, httpx):
```python
result = await model.ainvoke(messages)
async with httpx.AsyncClient() as client:
    await client.post(url, json=payload, timeout=5)
```

**Sync stdlib wrapped** (xmlrpc, imaplib):
```python
result = await asyncio.wait_for(
    asyncio.to_thread(self._sync_method, *args),
    timeout=TIMEOUT_SECONDS,
)
```

The entire stack is async — no sync blocking calls in the event loop.

### Search Module Pattern

The search subsystem is **internal infrastructure**, not an adapter — it lives in `search/` (not `adapters/`). No Protocol, no factory, no `@lru_cache` — components are instantiated per-request with a database session.

```
search/
├── engine.py          # Orchestration + RRF fusion (combines results from vector + keyword)
├── vector.py          # pgvector semantic search (cosine similarity)
├── keyword.py         # tsvector full-text search + exact reference matching
├── proposability.py   # SQL-level filtering (proposable-only products)
├── cache.py           # PostgreSQL-backed TTL cache (no Redis)
└── models.py          # DTOs: SearchRequest, ScoredProduct, SearchResult
```

**Key design decisions**:
- RRF (Reciprocal Rank Fusion) merges semantic and keyword results with configurable weights
- All search methods return `list[ScoredProduct]` for uniform merging
- Engine exposes a single `search()` entry point that handles caching, expansion, and fusion

### SQL-Level Filtering Pattern

Proposability filtering is applied as `WHERE` clauses **within** the search queries, NOT as a Python post-filter. This ensures:
- `LIMIT` returns the correct number of proposable results (not fewer after post-filtering)
- Better performance by pushing filtering to PostgreSQL
- Consistent pattern with `is_stale` filtering already used elsewhere

### PostgreSQL Cache Pattern

Search results are cached in a PostgreSQL table — no Redis dependency.

- **Cache key**: SHA-256 hash of `SearchRequest` params (query, method, top_k, filters)
- **TTL**: configurable expiry checked on read
- **Write**: upsert via `ON CONFLICT ... DO UPDATE`
- **Invalidation**: full cache clear on catalog re-sync
- Cache key **must include the search method** (hybrid/semantic/keyword) to prevent cross-method collisions

### Embedding Adapter Pattern

Follows the standard 4-file adapter pattern (`protocol.py`, `models.py`, `sentence_transformers.py`, `__init__.py` with factory).

- Uses `asyncio.to_thread()` to wrap sync `sentence-transformers` calls
- Lazy model loading: the BGE-M3 model is loaded on first `embed()` call, not at import time
- BGE-M3 outputs **1024-dimensional** vectors (not 1536 like OpenAI)
- Device configurable via `EMBEDDING__DEVICE` (cpu/cuda)

### Fire-and-Forget Notification Pattern

Notification nodes never block the pipeline and never set `state["error"]`:

```python
async def notify_node(state: AgentState) -> AgentState:
    try:
        adapter = get_notification_adapter()
        await adapter.send(message)
    except Exception:
        logger.warning("Notification failed", extra={"context": {...}})
    return {**state, "current_node": "notify_node"}
```

- Notification failure is logged but never propagated
- Pipeline continues regardless of notification outcome
- Check notification logs explicitly during testing — errors are caught silently

### Graph Node Pattern

Every graph node follows this signature and structure:

```python
async def node_name(state: AgentState) -> AgentState:
    state["current_node"] = "node_name"  # MUST match actual node name
    try:
        # Business logic here
        return {**state, "current_node": "node_name", "result_field": value}
    except Exception as e:
        logger.error("Node failed", extra={"context": {"error": str(e)}})
        return {**state, "current_node": "node_name", "error": str(e)}
```

- `current_node` set at entry AND in all return paths
- State accessed via dict keys, not attributes
- Error handling returns state with `error` key — never raises (except fire-and-forget nodes which omit `error`)
- `final_action` must be unique and descriptive for traceability

### Scheduler Pattern

Pure asyncio scheduling — no APScheduler or Celery dependency:

```python
@lru_cache(maxsize=1)
def get_scheduler() -> NotificationScheduler:
    return NotificationScheduler(get_settings().notification)
```

- Singleton via `@lru_cache(maxsize=1)`
- Conditional startup in FastAPI lifespan (only if scheduling is enabled)
- Uses `asyncio.create_task()` for background scheduling
- No external scheduler dependency — stdlib asyncio only

### Post-Pipeline Error Check

After `graph.ainvoke()`, `process.py` checks for error states and sends error notifications:

```python
result = await graph.ainvoke(AgentState(...))
if result.get("error"):
    await _send_error_notification(result)
```

- Catches errors that nodes set in state but don't surface as exceptions
- Implemented in `src/quote_agent/cli/process.py`
- Uses fire-and-forget pattern — error notification failure doesn't raise

### Configuration Pattern

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    # ...

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

# Lazy module attribute
def __getattr__(name: str) -> Any:
    if name == "settings":
        return get_settings()
```

- Env var `DATABASE__URL` maps to `settings.database.url`
- `from quote_agent.config import settings` triggers lazy evaluation
- Cache must be cleared in tests

---

## Known Pitfalls

### Pydantic + Mocking

`patch.object` on Pydantic model instances fails silently because `__setattr__`/`__delattr__` are intercepted by Pydantic's model machinery.

**Fix**: Use class-level patching or mock at the protocol/factory level.

### Lexicographic String Comparison

`max()` on severity strings produces wrong results: `"medium" > "high"` lexicographically.

**Fix**: Use explicit conditional logic:
```python
severity_max = (
    "high" if any(t.severity == "high" for t in threats)
    else "medium" if any(t.severity == "medium" for t in threats)
    else "low"
)
```

### Regex Over-Matching

Price regex patterns can match unintended content like percentages (e.g., "remise 10%" matches as price).

**Fix**: Test edge cases explicitly. Write tests with boundary inputs.

### Recursive Logging

`redact()` called during log formatting can trigger additional log calls, creating noise.

**Fix**: Guard with `_in_format` flag or similar mechanism in the formatter.

### `from __future__ import annotations`

Required in all files for deferred annotation evaluation. Without it, `Mapped[datetime]` and other SQLAlchemy type annotations fail at runtime.

**Exception**: SQLAlchemy model files still need `datetime` imported at runtime — add `# noqa: TC003` comment.

### FastAPI `Depends()` and `dependency_overrides`

`Annotated[X, Depends(...)]` breaks `dependency_overrides` in tests (returns 422 validation errors).

**Fix**: Keep standard `Depends()` syntax with `# noqa: B008` to suppress flake8-bugbear.

### Health Check Cascade

Adding new services to the health endpoint breaks existing tests if mocks are missing.

**Fix**: Use shared test helpers from `conftest.py` (`create_test_app`, `mock_healthy_adapter`).

### Runtime vs Dev Dependencies

Dependencies can be misclassified. httpx was marked dev-only but used by `TeamsAdapter` at runtime.

**Fix**: Audit dependencies at each story. Verify imports match dependency groups.

### Integration Test Fixture Isolation

`env_vars` autouse fixtures can overwrite real `DATABASE__URL`, breaking integration tests.

**Fix**: Keep integration tests in separate `tests/integration/` with dedicated conftest. Never use autouse env var fixtures that affect database configuration.

### Settings Cache Clearing

The following `@lru_cache` singletons must be cleared between tests to prevent state leakage:

```python
get_settings.cache_clear()
create_async_engine_from_settings.cache_clear()
_get_session_factory.cache_clear()
get_llm_adapter.cache_clear()
get_email_adapter.cache_clear()
get_embedding_adapter.cache_clear()
get_erp_adapter.cache_clear()
get_notification_adapter.cache_clear()
```

### Dead Code from LLM Iterations

Dev agents produce clean code but can leave traces of their own iterations: unused constants, stale classes, dead test methods.

**Fix**: Review explicitly for dead code after each story implementation.

### PEP 695 Generics over typing.Generic

Prefer PEP 695 type parameter syntax (Python 3.12+) over `typing.Generic[T]` — cleaner and more readable, especially for Pydantic models.

### BaseHTTPMiddleware for Global Exception Catching

`app.exception_handler(Exception)` is insufficient for true global exception catching in FastAPI. Use `BaseHTTPMiddleware` instead to intercept all unhandled exceptions and return uniform error responses.

### asyncpg: No Concurrent Queries on Same Connection

asyncpg does not support concurrent queries on the same connection. Using `asyncio.gather()` for parallel DB queries on a single session **will fail** with `InterfaceError`.

**Fix**: Execute queries sequentially, or use separate connections/sessions for true parallelism.

### asyncpg: No Parameterized `SET LOCAL`

`SET LOCAL hnsw.ef_search = $1` fails with asyncpg — parameterized placeholders are not supported for `SET` statements.

**Fix**: Use f-string with explicit `int()` cast for safety:
```python
await session.execute(text(f"SET LOCAL hnsw.ef_search = {int(value)}"))
```

### Vector Dimension Must Match Model

BGE-M3 outputs **1024** dimensions, NOT 1536 (OpenAI's default). Using the wrong dimension for the pgvector column causes silent failures or dimension mismatch errors.

**Fix**: Always verify the embedding model's output dimension before creating or altering the vector column.

### Unicode Regex Word Boundaries

Python `\b` word boundary treats characters like `Ø` (U+00D8) as `\w`, so `\b` patterns don't match as expected around non-ASCII characters.

**Fix**: Use separate regex strategies for ASCII vs non-ASCII abbreviations (e.g., exact substring match for non-ASCII terms).

### Cache Key Must Include Search Method

Without the search method (hybrid/semantic/keyword) in the cache key, different search methods can collide and return wrong cached results.

**Fix**: Include all distinguishing parameters in the SHA-256 cache key: query text, method, top_k, and filter flags.

### Commit After Cache Invalidation

When invalidating cache inside a transaction (e.g., after catalog re-sync), the `DELETE` must be committed. If the session is rolled back later, the invalidation is lost and stale cache entries persist.

**Fix**: Ensure cache invalidation is committed (or use a separate transaction) before proceeding with operations that might roll back.

### Copy-Paste Node Constants

When duplicating a graph node, `current_node` and routing constants silently carry the old node's values. Tests don't catch this — the node runs but reports as the wrong node.

**Fix**: Always search-and-replace all constants when copying a node. Follow the Graph Node Checklist in Conventions.

### Fire-and-Forget Error Masking

Notification errors in fire-and-forget nodes are caught and logged but never surface as state errors or test failures.

**Fix**: Check notification logs explicitly during testing. Don't assume "no error" means "notification sent."

### Medium-Confidence Requires Realistic Data

Medium-confidence tier can't be triggered with 3-5 products. Requires a variant-rich catalogue with genuine ambiguity (e.g., multiple similar products with different specs).

**Fix**: Use `seed_odoo_realistic` or equivalent fixture with 50+ products for medium-confidence E2E tests.

---

## Conventions

### Naming Conventions

**Python (PEP 8 strict)**:
- Files: `snake_case` (`email_poller.py`, `odoo_adapter.py`)
- Classes: `PascalCase` (`QuoteProcessor`, `OdooAdapter`)
- Functions/methods: `snake_case` (`process_quote()`, `search_products()`)
- Variables: `snake_case` (`confidence_score`, `client_id`)
- Constants: `UPPER_SNAKE_CASE` (`MAX_RETRY_COUNT`, `DEFAULT_CONFIDENCE_THRESHOLD`)

**Database**:
- Tables: `snake_case` plural (`email_requests`, `quote_requests`)
- Columns: `snake_case` (`created_at`, `confidence_score`)
- Foreign keys: `{singular}_id` (`email_request_id`)
- Constraint prefixes: `ix_` (index), `uq_` (unique), `ck_` (check), `fk_` (foreign key), `pk_` (primary key)

**Tests**:
- Unit/integration: `test_{behavior}_when_{condition}()`
- E2E: `test_{scenario}_e2e()`
- Test classes: `Test{FeatureName}` (e.g., `TestPipelineHappyPath`)
- Docstrings: `AC-{#}: {acceptance criterion description}`

### Import Conventions

- Absolute imports only: `from quote_agent.adapters.erp.protocol import ERPAdapter`
- Never relative: ~~`from ..adapters import erp`~~
- Order: stdlib → third-party → local (Ruff enforces via `I` rule)
- Use `TYPE_CHECKING` blocks for import-only types to avoid circular imports

### Project Structure

```
src/quote_agent/
├── adapters/           # External integrations (5 types: llm, erp, email, notification, embedding)
│   ├── llm/            # protocol.py + models.py + openai_compat.py + __init__.py
│   ├── erp/
│   ├── email/
│   ├── notification/
│   └── embedding/      # protocol.py + models.py + sentence_transformers.py + __init__.py
├── search/             # Internal search infrastructure (not an adapter)
│   ├── engine.py       # Orchestration + RRF fusion
│   ├── vector.py       # pgvector semantic search
│   ├── keyword.py      # tsvector full-text + exact reference
│   ├── proposability.py # SQL-level proposability filtering
│   ├── cache.py        # PostgreSQL-backed TTL cache
│   └── models.py       # SearchRequest, ScoredProduct, SearchResult
├── agent/              # LangGraph (graph, state, nodes, tools)
├── models/             # SQLAlchemy models + DB access (base.py, email_request.py, quote_request.py)
├── services/           # Business logic (email_poller.py, email_cleaner.py, email_extractor.py, request_splitter.py)
├── security/           # Input sanitization (sanitizer.py, input_isolation.py, log_redactor.py)
├── audit/              # Logging (logger.py)
├── cli/                # CLI commands
├── api/                # FastAPI endpoints
└── config.py           # pydantic-settings configuration

tests/
├── unit/               # Isolated component tests (no DB, no real services)
├── integration/        # Multi-component with real DB, dedicated conftest
└── e2e/                # Full pipeline with real services (IMAP, PostgreSQL, LLM)
    ├── conftest.py     # Cache clearing, DB session, adapter fixtures
    └── fixtures/       # Test email factory functions
```

**Dependency rule**: layers depend downward only. `models/` never imports `services/`. `security/` has no outbound dependencies.

### Graph Node Checklist

When creating or copying a graph node, verify all 5 items:

1. **Update `current_node`** in all `state` writes within the new node — copy-paste carries the old node's value silently
2. **Update routing function** edge maps in `graph.py` — the node must be reachable
3. **Add to `docs/graph-path-inventory.md`** — every path from START to END must be documented
4. **Add E2E test** if the node creates a new path to END — untested paths are invisible failures
5. **Verify `final_action`** value is unique and descriptive — duplicates break traceability

_Rationale: Story 5.2 had `current_node` set to "notify" instead of "notify_proposals" in 3 locations. Caught by code review, invisible to all tests._

### Structured Logging

```json
{
    "timestamp": "2026-03-15T09:14:23.456Z",
    "level": "INFO",
    "component": "services.email_poller",
    "message": "Email received",
    "context": {"email_request_id": "...", "status": "received"}
}
```

- `component`: dot notation matching Python module path
- `context`: structured dict, auto-redacted by JSONLogFormatter
- Never include confidential data in context — redaction is a safety net, not a substitute for discipline
- Never use `print()` — always structured logging

### Search Configuration Settings

All search-related settings follow the existing pydantic-settings pattern and are accessed via `get_settings()`:

| Setting Class | Env Prefix | Purpose |
|---------------|-----------|---------|
| `SearchSettings` | `SEARCH__` | Top-k, RRF weights, ef_search |
| `SearchCacheSettings` | `SEARCH_CACHE__` | TTL, enabled flag |
| `ProposabilitySettings` | `PROPOSABILITY__` | Filter rules, enabled flag |
| `EmbeddingSettings` | `EMBEDDING__` | Model name, device (cpu/cuda), dimension |

### Test Markers

- `@pytest.mark.e2e` — requires real services (PostgreSQL, BGE-M3 model, optionally Odoo)
- `@pytest.mark.scale` — large-scale tests (50K products), excluded by default, run with `pytest -m "e2e and scale"`
- `@pytest.mark.benchmark` — performance benchmarks, excluded from CI by default

---

## Quality Gates

### mypy

```toml
[tool.mypy]
strict = true
python_version = "3.12"
plugins = ["pydantic.mypy"]
```

Zero issues required. All functions must have type annotations (parameters + return).

### Ruff

```toml
[tool.ruff]
target-version = "py312"
line-length = 120
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM", "TCH", "RUF"]
```

Rules: pycodestyle (E/W), Pyflakes (F), isort (I), pep8-naming (N), pyupgrade (UP), bugbear (B), builtins (A), simplify (SIM), type-checking (TCH), Ruff-specific (RUF).

### pytest

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "e2e: end-to-end tests requiring real services (IMAP, PostgreSQL, LLM)",
    "scale: large-scale tests (50K products, slow)",
    "benchmark: performance benchmarks",
]
addopts = "-m 'not e2e and not scale'"
```

- `asyncio_mode = "auto"`: no need for `@pytest.mark.asyncio` decorator
- E2E tests excluded by default; run with `pytest -m e2e`
- E2E tests require real `DATABASE__URL` and `LLM__API_KEY` environment variables; search E2E tests also require a loaded BGE-M3 model
- **Test count**: 781 unit + 28 E2E (22 pipeline + 6 graph paths). All passing against real services (PostgreSQL+pgvector, LLM, Odoo), verified Story 5.5.5.
- `@requires_e2e` skip decorator checks service availability

### E2E Test Requirements

- **E2E tests are gate-keepers**: if they break, work stops until fixed — no "pre-existing failure" deferral
- All E2E tests use real services (IMAP, PostgreSQL, LLM) — no mocked E2E acceptable
- Every new graph path to END must have a notification + E2E test
- `NOTIFICATION__CHANNEL=log` mandatory in test environments — never send real Teams notifications
- Cache clearing autouse fixture runs before and after each test
- Test data identified by `e2e-test` prefix in `message_id` for deterministic cleanup
- Cleanup respects FK constraints: delete QuoteRequests before EmailRequests

---

## Definition of Done (DoD)

Every story must satisfy these mandatory gates before merge:

1. `uv run mypy --strict src/` — 0 issues
2. `uv run ruff check src/ tests/` — 0 issues
3. `uv run pytest tests/unit/ -v --tb=short` — 0 failures, 0 regressions
4. CI pipeline green (GitHub Actions) before merge
5. E2E tests passing — applies to any story that modifies `agent/`, `adapters/`, `search/`, or graph nodes

**Scope note**: The E2E gate applies to stories touching `agent/`, `adapters/`, `search/`, or graph nodes. Documentation-only stories still require gates 1-4.

**Anti-pattern**: CI green is a gate, not a nice-to-have. "CI green in DoD" was a floating agreement confirmed lost in 4 consecutive retrospectives (Epics 2-5). Only items tracked as stories survive — this section is the fix.

---

## Decisions

### Jargon Dictionary Removed (Story 4.0c, 2026-03-20)

Story 3.6 introduced a jargon abbreviation dictionary (10 entries: inox, Ø, lg, DN, PN, etc.) for query expansion before embedding/keyword search. The Epic 3 retrospective flagged this as a product regression — the project's "zero-preprocessing" vision relies on BGE-M3's multilingual semantic understanding handling industrial jargon natively.

**Benchmark results** (25 queries across 4 categories on 100 products from catalog fixture):
- Expansion **enabled**: 24/25 = 96.0% (abbreviation 83%, jargon 100%, cross_language 100%, exact_reference 100%)
- Expansion **disabled**: 24/25 = 96.0% (identical breakdown)
- **Delta: 0%** — the dictionary provided zero measurable benefit

The single failure ("boulons HM M10x50") failed in both modes due to no matching product in the fixture, not a semantic search limitation.

**Decision**: Remove the dictionary entirely. BGE-M3 handles all tested abbreviations (inox, DN, PN, Ø, lg, TB, RD) natively via semantic search. Removed files: `search/jargon.py`, `JargonSettings`, `jargon_expanded`/`expanded_query` fields from `SearchResult`, all jargon unit and E2E tests.

---

## Tech Stack Summary

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| Package manager | uv |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.x (async with asyncpg) |
| Migrations | Alembic |
| Configuration | pydantic-settings |
| AI orchestration | LangGraph |
| LLM client | LangChain (ChatOpenAI) |
| Testing | pytest + pytest-asyncio |
| Linting | Ruff |
| Type checking | mypy (strict) |
| Embeddings | sentence-transformers (BGE-M3, 1024-dim) |
| Vector search | pgvector (cosine similarity via `<=>` operator) |
| Database | PostgreSQL (relational + vector + queue) |
| Containerization | Docker |
