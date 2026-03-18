# Story 1.3: Serveur API & Health Check

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator**,
I want a running FastAPI server with a `/health` endpoint that reports system status,
So that I can verify the application is alive and check service health for Docker HEALTHCHECK, CLI status, and future dashboard.

## Acceptance Criteria

1. **AC-1.3.1**: Health endpoint returns system status
   - Given the FastAPI application is started
   - When I call `GET /health`
   - Then I receive HTTP 200 with JSON: `{"data": {"status": "healthy", "services": {"database": "healthy"}}, "meta": {"timestamp": "<ISO8601>"}}`
   - And the database service status is verified by executing a real `SELECT 1` query
   - And the response uses the project's standard API format

2. **AC-1.3.2**: Health endpoint reports degraded status
   - Given the database is unreachable
   - When I call `GET /health`
   - Then I receive HTTP 200 with `{"data": {"status": "degraded", "services": {"database": {"status": "unhealthy", "error": "<message>"}}}, "meta": {"timestamp": "<ISO8601>"}}`
   - And the overall status is `"degraded"` (not `"healthy"`)
   - And the specific error message is included for troubleshooting

3. **AC-1.3.3**: API v1 base endpoint works
   - Given the API server is running
   - When I call `GET /api/v1/`
   - Then I receive HTTP 200 with `{"data": {"name": "ai-quote-agent", "version": "0.1.0"}, "meta": {"timestamp": "<ISO8601>"}}`
   - And the name and version come from `settings.app`

4. **AC-1.3.4**: Server starts with uvicorn
   - Given environment variables are configured (DATABASE__URL etc.)
   - When I run `uv run uvicorn quote_agent.main:app --host 0.0.0.0 --port 8000`
   - Then the server starts and responds to HTTP requests
   - And `app` is the module-level FastAPI instance created by `create_app()`

5. **AC-1.3.5**: Tests pass
   - Given the test suite exists
   - When I run `uv run pytest tests/unit/test_health.py`
   - Then all health endpoint tests pass (healthy response, degraded response, API v1 base)
   - And `uv run ruff check src/ tests/` and `uv run mypy src/` both succeed

## Tasks / Subtasks

- [x] Task 1: Create API response models (AC: 1, 2, 3)
  - [x] 1.1: Create `src/quote_agent/api/schemas.py` with Pydantic response models:
    - `ApiMeta` — `timestamp: datetime` (UTC, ISO 8601)
    - `ApiResponse[T]` — generic `data: T`, `meta: ApiMeta` (use `Generic[T]`)
    - `ApiError` — `code: str`, `message: str`, `detail: str | None`
    - `ApiErrorResponse` — `error: ApiError`, `meta: ApiMeta`
  - [x] 1.2: Add a helper function `make_response(data: T) -> dict` that wraps any data with `meta.timestamp` set to `datetime.now(UTC)`

- [x] Task 2: Create health check endpoint (AC: 1, 2)
  - [x] 2.1: Create `src/quote_agent/api/health.py` with:
    - `router = APIRouter()`
    - `GET /health` endpoint (no version prefix — this is an internal/infra endpoint)
    - Database check: acquire a session via `get_async_session()`, execute `SELECT 1`, report healthy/unhealthy
    - Catch `Exception` from DB check (typed as `sqlalchemy.exc.SQLAlchemyError` or `Exception` for connection refused), report as degraded with error message
    - Return response using `make_response()` helper
  - [x] 2.2: Health check response models:
    - `ServiceHealth` — `status: Literal["healthy", "unhealthy"]`, `error: str | None = None`
    - `HealthResponse` — `status: Literal["healthy", "degraded"]`, `services: dict[str, ServiceHealth]`, `timestamp: datetime`

- [x] Task 3: Create API v1 router (AC: 3)
  - [x] 3.1: Create `src/quote_agent/api/v1/__init__.py` (package)
  - [x] 3.2: Create `src/quote_agent/api/v1/router.py` with:
    - `router = APIRouter(prefix="/api/v1")`
    - `GET /api/v1/` returns `make_response({"name": settings.app.name, "version": settings.app.version})`

- [x] Task 4: Wire routers into FastAPI app (AC: 4)
  - [x] 4.1: Update `src/quote_agent/main.py`:
    - Add `lifespan` async context manager (log startup/shutdown, clear LRU caches on shutdown if needed)
    - Include health router: `app.include_router(health_router)`
    - Include v1 router: `app.include_router(v1_router)`
    - Expose module-level `app = create_app()` so uvicorn can find `quote_agent.main:app`

- [x] Task 5: Add global exception handler (AC: 1, 2)
  - [x] 5.1: In `main.py` or a dedicated middleware module, add a FastAPI exception handler for `QuoteAgentError` that returns the standard `ApiErrorResponse` format
  - [x] 5.2: Add a catch-all handler for unhandled exceptions that returns 500 with `ApiErrorResponse`

- [x] Task 6: Write tests (AC: 5)
  - [x] 6.1: Add `httpx` as dev dependency: `uv add --dev httpx` (required for `ASGITransport` / `AsyncClient` testing)
  - [x] 6.2: Create `tests/unit/test_health.py` with:
    - `test_health_endpoint_returns_healthy` — mock `get_async_session` to return a working session stub, assert 200 + `status == "healthy"` + `services.database.status == "healthy"` + `meta.timestamp` present
    - `test_health_endpoint_returns_degraded_when_db_fails` — mock `get_async_session` to raise `SQLAlchemyError`, assert 200 + `status == "degraded"` + `services.database.status == "unhealthy"` + error message present
    - `test_api_v1_base_endpoint` — assert 200 + `data.name == "ai-quote-agent"` + `data.version == "0.1.0"` + `meta.timestamp` present
    - `test_api_response_format_has_meta_timestamp` — any endpoint returns ISO 8601 timestamp in `meta`
    - `test_unhandled_exception_returns_500_error_format` — trigger exception, assert structured error response
  - [x] 6.3: Use `httpx.AsyncClient` with `ASGITransport(app=app)` for async endpoint testing (NOT `TestClient` which is sync)
  - [x] 6.4: Verify `uv run ruff check src/ tests/` and `uv run mypy src/` both pass

## Dev Notes

### Architecture Compliance

- **API Framework**: FastAPI >= 0.135.1 (installed). Use `lifespan` context manager, NOT deprecated `@app.on_event`. [Source: architecture.md#API-Framework-Choice]
- **Response Format**: ALL endpoints MUST return `{"data": {...}, "meta": {"timestamp": "ISO8601"}}`. Error responses: `{"error": {"code": "...", "message": "...", "detail": "..."}, "meta": {"timestamp": "..."}}`. [Source: architecture.md#API-Response-Formats]
- **URL Structure**: `/health` at root (no version prefix — infra endpoint). Business endpoints under `/api/v1/`. [Source: architecture.md#Health-Check-Endpoint-Design]
- **Dates**: ISO 8601 everywhere, UTC in storage. Use `datetime.now(UTC)`. [Source: architecture.md#API-&-Communication]
- **JSON fields**: snake_case. [Source: architecture.md#API-&-Communication]
- **Auth**: Static token authentication (HTTP Basic) for MVP — NOT in this story. Mentioned for awareness only. [Source: architecture.md#API-&-Communication]
- **Logging**: Structured JSON logging. Use `logging.getLogger(__name__)` — NO `print()`. [Source: architecture.md#Code-Quality-Mandates]

### Response Format Reference

```python
# Success — all endpoints
{"data": {...}, "meta": {"timestamp": "2026-03-18T10:00:00Z"}}

# Error — exception handler
{"error": {"code": "DATABASE_CONNECTION_FAILED", "message": "...", "detail": "..."}, "meta": {"timestamp": "..."}}

# Health — specific
{
  "data": {
    "status": "healthy",  # or "degraded"
    "services": {
      "database": {"status": "healthy", "error": null}
    },
    "timestamp": "2026-03-18T10:00:00Z"
  },
  "meta": {"timestamp": "2026-03-18T10:00:00Z"}
}
```

### Health Check Design

The `/health` endpoint serves three consumers:
1. **Docker HEALTHCHECK** — `curl -f http://localhost:8000/health || exit 1` (Story 1.7 will add the `HEALTHCHECK` instruction)
2. **CLI** — `agent status` command (future, Epic 7)
3. **Web dashboard** — polling every 30s (future, Epic 7)

For this story, only **database** service is checked. Future stories (1.4, 1.5, 1.6) will add their adapter health checks. Design the `services` dict to be extensible — each adapter will add its key.

### Existing Code to Build On

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/main.py` | `create_app()` factory returning `FastAPI` instance | Add lifespan, include routers, expose `app` module-level |
| `src/quote_agent/config.py` | Full settings system with `get_settings()` / lazy `settings` | Import `settings` for app name/version in v1 endpoint |
| `src/quote_agent/models/base.py` | `get_async_session()` async generator, `create_async_engine_from_settings()` | Use `get_async_session()` for DB health check |
| `src/quote_agent/exceptions.py` | `QuoteAgentError` hierarchy | Wire into global exception handler |
| `src/quote_agent/api/__init__.py` | Empty package | Leave as-is |
| `tests/conftest.py` | `env_vars` fixture, `_clear_settings_cache` fixture | Reuse `env_vars` for test app setup |

### Testing Pattern

Use `httpx.AsyncClient` with `ASGITransport` (NOT sync `TestClient`):

```python
from httpx import ASGITransport, AsyncClient

from quote_agent.main import create_app

app = create_app()

async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
```

For mocking the database session in health check tests, use FastAPI dependency overrides:

```python
app.dependency_overrides[get_async_session] = mock_session_factory
```

### File Locations

```
ai-quote-agent/
├── src/quote_agent/
│   ├── main.py                          # MODIFY — add lifespan, routers, module-level app
│   └── api/
│       ├── __init__.py                  # EXISTS (empty)
│       ├── schemas.py                   # NEW — ApiResponse, ApiError, ApiMeta, make_response
│       ├── health.py                    # NEW — GET /health router
│       └── v1/
│           ├── __init__.py              # NEW — v1 package
│           └── router.py               # NEW — GET /api/v1/ base endpoint
└── tests/
    └── unit/
        └── test_health.py              # NEW — health + v1 endpoint tests
```

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Use `@app.on_event("startup")` (deprecated) | Use `lifespan` async context manager |
| Use `TestClient` (sync) for async endpoint tests | Use `httpx.AsyncClient` with `ASGITransport` |
| Return raw `dict` without meta.timestamp | Always use `make_response()` wrapper |
| Hardcode app name/version in endpoints | Read from `settings.app.name` / `settings.app.version` |
| Put `/health` under `/api/v1/health` | Put at root `/health` (infra endpoint, no version) |
| Use `print()` for logging | Use `logging.getLogger(__name__)` |
| Use bare `except Exception` | Catch typed exceptions (`SQLAlchemyError`, specific DB errors) |
| Import `os.getenv()` for config | Use `from quote_agent.config import settings` |
| Create middleware for CORS/static files in this story | Only add what's needed: routers + exception handlers. CORS/static come later. |

### Previous Story Intelligence (Story 1.2)

- **LRU cache singletons**: `create_async_engine_from_settings()` and `_get_session_factory()` are both cached. Health check can call `get_async_session()` safely — it reuses the cached engine.
- **Async session pattern**: `get_async_session()` is an async generator that yields `AsyncSession`. In FastAPI endpoints, use it as a `Depends()` parameter.
- **Integration tests split**: Story 1.2 moved integration tests to `tests/integration/` with dedicated `conftest.py`. Health check unit tests should mock the session; integration tests (if added) can use the real DB.
- **`asyncpg` installed**: The async driver is already a project dependency.
- **`env_vars` fixture**: Provides all required env vars for `Settings()` instantiation. Tests should use `env_vars` + `_clear_settings_cache` fixtures.
- **Debug note**: `_clear_settings_cache` is essential — the `lru_cache` on `get_settings()` will persist stale settings across tests otherwise. Also need to clear `create_async_engine_from_settings.cache_clear()` and `_get_session_factory.cache_clear()` in tests to avoid stale DB connections.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Commits for Epic 1 so far:
- `2482e07` feat: add PostgreSQL database foundation with async SQLAlchemy & Alembic migrations (Story 1.2)
- `7f9383a` feat: add project scaffolding & type-safe configuration system (Story 1.1)

### Dependencies to Add

- `httpx` — dev dependency for async FastAPI testing (`uv add --dev httpx`)

### Scope Boundaries

- **IN scope**: FastAPI app with lifespan, `/health` endpoint (DB check only), `/api/v1/` base endpoint, response schemas, global exception handler, unit tests
- **OUT of scope**: CORS middleware, static files, authentication, WebSocket, adapter health checks (LLM/ERP/email/notification — those come in Stories 1.4-1.6), Docker HEALTHCHECK instruction (Story 1.7), structured logging setup (Epic 7), CLI commands

### References

- [Source: architecture.md#API-Framework-Choice] — FastAPI selection rationale
- [Source: architecture.md#API-Response-Formats] — mandatory response structure
- [Source: architecture.md#Health-Check-Endpoint-Design] — /health consumers and design
- [Source: architecture.md#Project-Structure-&-Boundaries] — api/ folder organization
- [Source: architecture.md#Implementation-Patterns-&-Consistency-Rules] — code quality mandates
- [Source: epics.md#Story-1.3] — acceptance criteria, user story
- [Source: _bmad-output/implementation-artifacts/1-2-base-de-donnees-postgresql-migrations.md] — previous story learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Starlette `app.exception_handler(Exception)` catch-all does not intercept `RuntimeError` in current Starlette version — switched to `BaseHTTPMiddleware` for the catch-all 500 handler.
- `Annotated[AsyncSession, Depends(...)]` breaks `dependency_overrides` in tests (FastAPI returns 422) — kept standard `Depends()` default param pattern with `noqa: B008`.
- PEP 695 `class ApiResponse[T](BaseModel)` used instead of `Generic[T]` per ruff UP046 rule.

### Completion Notes List

- ✅ Created `api/schemas.py` with `ApiMeta`, `ApiResponse[T]`, `ApiError`, `ApiErrorResponse`, `make_response()` — all using UTC ISO 8601 timestamps
- ✅ Created `api/health.py` with `GET /health` endpoint — real `SELECT 1` DB check via `get_async_session()` dependency, extensible `services` dict
- ✅ Created `api/v1/router.py` with `GET /api/v1/` — returns app name/version from settings
- ✅ Updated `main.py` with `lifespan` context manager (startup/shutdown logging, LRU cache cleanup), router registration, module-level `app` instance
- ✅ Added `QuoteAgentError` exception handler (400) and `CatchAllExceptionMiddleware` (500) — both return structured `ApiErrorResponse` format
- ✅ 5 unit tests covering healthy, degraded, v1 base, meta timestamp format, and unhandled exception scenarios
- ✅ All 24 tests pass (0 regressions), ruff clean, mypy strict clean
- ✅ Added `httpx` dev dependency for async ASGI testing

### Change Log

- 2026-03-18: Implemented Story 1.3 — FastAPI server with health check, v1 router, response schemas, exception handlers, and unit tests

### File List

- `src/quote_agent/api/schemas.py` — NEW: API response models (ApiMeta, ApiResponse, ApiError, ApiErrorResponse, make_response)
- `src/quote_agent/api/health.py` — NEW: GET /health endpoint with DB connectivity check
- `src/quote_agent/api/v1/__init__.py` — NEW: v1 package init
- `src/quote_agent/api/v1/router.py` — NEW: GET /api/v1/ base endpoint
- `src/quote_agent/main.py` — MODIFIED: added lifespan, routers, exception handlers, module-level app
- `tests/unit/test_health.py` — NEW: 5 async endpoint tests
- `src/quote_agent/config.py` — MODIFIED: added `extra="ignore"` to Settings model_config
- `pyproject.toml` — MODIFIED: added httpx dev dependency
- `uv.lock` — MODIFIED: lock file updated
