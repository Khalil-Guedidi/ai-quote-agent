# Story 1.5: Configuration Connexions ERP & Email

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator**,
I want to configure ERP (Odoo) and email (IMAP) connection parameters,
So that the system knows how to connect to the company's existing infrastructure.

## Acceptance Criteria

1. **AC-1.5.1**: ERP adapter connects using Odoo XML-RPC
   - Given Odoo connection settings are in `.env` (`ERP__URL`, `ERP__DATABASE`, `ERP__USERNAME`, `ERP__API_KEY`)
   - When the ERP adapter is initialized with `ERPSettings` from `settings.erp`
   - Then it validates the connection parameters
   - And exposes an async `health_check()` method returning `ServiceHealth`
   - And credentials (`api_key`) are never logged or exposed (use `SecretStr`)

2. **AC-1.5.2**: Email adapter connects using IMAP
   - Given IMAP email settings are in `.env` (`EMAIL__IMAP_SERVER`, `EMAIL__IMAP_PORT`, `EMAIL__USERNAME`, `EMAIL__PASSWORD`, `EMAIL__FOLDER`)
   - When the email adapter is initialized with `EmailSettings` from `settings.email`
   - Then it validates the connection parameters
   - And exposes an async `health_check()` method returning `ServiceHealth`
   - And credentials (`password`) are never logged or exposed (use `SecretStr`)

3. **AC-1.5.3**: Health checks detect ERP/email unavailability
   - Given the ERP or email connection fails (wrong URL, invalid credentials, timeout)
   - When the adapter's `health_check()` is called
   - Then it returns `ServiceHealth(status="unhealthy", error="<descriptive message>")`
   - And the `/health` endpoint reflects degradation in `services.erp` and `services.email`

4. **AC-1.5.4**: Adapters follow the project Protocol pattern
   - Then `adapters/erp/protocol.py` defines an `ERPAdapter` Protocol class
   - And `adapters/erp/odoo.py` implements `OdooAdapter`
   - And `adapters/erp/models.py` defines typed DTOs
   - And `adapters/email/protocol.py` defines an `EmailAdapter` Protocol class
   - And `adapters/email/imap.py` implements `IMAPAdapter`
   - And `adapters/email/models.py` defines typed DTOs
   - And all health_check methods are async and return typed `ServiceHealth` DTOs

5. **AC-1.5.5**: Tests pass
   - Given the test suite exists
   - When I run `uv run pytest tests/unit/test_erp_adapter.py tests/unit/test_email_adapter.py`
   - Then all adapter tests pass (healthy check, unhealthy check, protocol compliance)
   - And `uv run ruff check src/ tests/` and `uv run mypy src/` both succeed

## Tasks / Subtasks

- [x] Task 1: Create ERP adapter DTOs (AC: 4)
  - [x] 1.1: Create `src/quote_agent/adapters/erp/models.py` with Pydantic DTOs:
    - `OdooVersionInfo` — `server_version: str`, `protocol_version: int` (returned by health check)
    - Stub future DTOs as comments only: `UniversalQuote`, `Product`, `Client` (will be implemented in Epic 3/4 stories)

- [x] Task 2: Create ERP adapter Protocol (AC: 4)
  - [x] 2.1: Create `src/quote_agent/adapters/erp/protocol.py` with:
    - `ERPAdapter` Protocol class with:
      - `async def health_check(self) -> ServiceHealth` — check ERP connectivity and authentication
    - Stub future methods as comments referencing architecture: `create_draft_quote`, `get_products`, `get_client` (NOT implemented yet — they come in Epic 3/4)

- [x] Task 3: Implement OdooAdapter (AC: 1, 3, 4)
  - [x] 3.1: Create `src/quote_agent/adapters/erp/odoo.py` with `OdooAdapter`:
    - Constructor takes `ERPSettings` (from `settings.erp`)
    - Stores settings but does NOT connect eagerly (connect on first use)
    - `health_check() -> ServiceHealth`:
      1. Call `xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common").version()` wrapped in `asyncio.to_thread` to verify connectivity (no auth needed)
      2. Call `common.authenticate(db, username, api_key)` wrapped in `asyncio.to_thread` to verify credentials — returns `uid` (int) on success, `False` on failure
      3. Return `ServiceHealth(status="healthy")` on success
      4. Catch `ConnectionRefusedError`, `OSError`, `xmlrpc.client.Fault`, `TimeoutError` → return `ServiceHealth(status="unhealthy", error=str(exc))`
    - Health check caching: same pattern as LLM adapter — `_last_health` + `_last_health_time` with 30s TTL
    - Use `_HEALTH_CHECK_TIMEOUT = 5.0` with `asyncio.wait_for` for the overall health check
  - [x] 3.2: Credentials handling: pass `settings.erp.api_key.get_secret_value()` only when calling `authenticate()` — never log it

- [x] Task 4: Create Email adapter DTOs (AC: 4)
  - [x] 4.1: Create `src/quote_agent/adapters/email/models.py` with Pydantic DTOs:
    - `IMAPHealthInfo` — `server: str`, `port: int`, `folder: str` (basic connection info for diagnostics)
    - Stub future DTOs as comments: `IncomingEmail`, `ParsedEmail` (will be implemented in Epic 2 stories)

- [x] Task 5: Create Email adapter Protocol (AC: 4)
  - [x] 5.1: Create `src/quote_agent/adapters/email/protocol.py` with:
    - `EmailAdapter` Protocol class with:
      - `async def health_check(self) -> ServiceHealth` — check IMAP connectivity and authentication
    - Stub future methods as comments: `fetch_emails` (NOT implemented yet — comes in Story 2.1)

- [x] Task 6: Implement IMAPAdapter (AC: 2, 3, 4)
  - [x] 6.1: Create `src/quote_agent/adapters/email/imap.py` with `IMAPAdapter`:
    - Constructor takes `EmailSettings` (from `settings.email`)
    - Stores settings but does NOT connect eagerly
    - `health_check() -> ServiceHealth`:
      1. Create `imaplib.IMAP4_SSL(server, port)` wrapped in `asyncio.to_thread`
      2. Call `login(username, password.get_secret_value())`
      3. Call `select(folder)` to verify folder exists
      4. Call `logout()`
      5. Return `ServiceHealth(status="healthy")` on success
      6. Catch `imaplib.IMAP4.error`, `ConnectionRefusedError`, `OSError`, `TimeoutError` → return `ServiceHealth(status="unhealthy", error=str(exc))`
    - Health check caching: same 30s TTL pattern
    - Use `_HEALTH_CHECK_TIMEOUT = 5.0` with `asyncio.wait_for`
  - [x] 6.2: Credentials handling: pass `settings.email.password.get_secret_value()` only in `login()` — never log it

- [x] Task 7: Wire ERP & Email adapters into health endpoint (AC: 3)
  - [x] 7.1: Create `get_erp_adapter() -> OdooAdapter` cached singleton in `adapters/erp/__init__.py` (same pattern as `get_llm_adapter`)
  - [x] 7.2: Create `get_email_adapter() -> IMAPAdapter` cached singleton in `adapters/email/__init__.py`
  - [x] 7.3: Update `src/quote_agent/api/health.py`:
    - Import `get_erp_adapter` and `get_email_adapter`
    - Add ERP and email health checks alongside existing DB + LLM checks
    - Add `"erp"` and `"email"` keys to the `services` dict in `HealthResponse`
    - Overall status: `"degraded"` if ANY service is unhealthy (existing logic handles this)
  - [x] 7.4: Update `adapters/erp/__init__.py` and `adapters/email/__init__.py` with proper exports

- [x] Task 8: Write tests (AC: 5)
  - [x] 8.1: Create `tests/unit/test_erp_adapter.py` with:
    - `test_health_check_returns_healthy_on_success` — mock `xmlrpc.client.ServerProxy` to return version + valid uid
    - `test_health_check_returns_unhealthy_on_connection_error` — mock to raise `ConnectionRefusedError`
    - `test_health_check_returns_unhealthy_on_auth_failure` — mock `authenticate` to return `False`
    - `test_health_check_caches_result` — verify second call within 30s returns cached result without hitting XML-RPC
    - `test_adapter_conforms_to_protocol` — verify `OdooAdapter` satisfies `ERPAdapter` protocol
    - `test_health_endpoint_includes_erp_service` — use `httpx.AsyncClient` with `ASGITransport` to hit `/health`, assert `services.erp` present
  - [x] 8.2: Create `tests/unit/test_email_adapter.py` with:
    - `test_health_check_returns_healthy_on_success` — mock `imaplib.IMAP4_SSL` to succeed on login + select
    - `test_health_check_returns_unhealthy_on_connection_error` — mock to raise `ConnectionRefusedError`
    - `test_health_check_returns_unhealthy_on_auth_failure` — mock `login` to raise `IMAP4.error`
    - `test_health_check_returns_unhealthy_on_bad_folder` — mock `select` to raise error
    - `test_health_check_caches_result` — verify caching behavior
    - `test_adapter_conforms_to_protocol` — verify `IMAPAdapter` satisfies `EmailAdapter` protocol
    - `test_health_endpoint_includes_email_service` — assert `services.email` present in `/health` response
  - [x] 8.3: Use `unittest.mock.patch` to mock `xmlrpc.client.ServerProxy` and `imaplib.IMAP4_SSL` — never hit real servers
  - [x] 8.4: Verify `uv run ruff check src/ tests/` and `uv run mypy src/` both pass

## Dev Notes

### Architecture Compliance

- **Adapter Pattern**: Every adapter follows `protocol.py` (interface) + `{impl}.py` (implementation) + `models.py` (DTOs). [Source: architecture.md#Structure-Patterns]
- **All methods async**: Every adapter method must be `async`. Use `asyncio.to_thread()` to wrap sync stdlib calls (`xmlrpc.client`, `imaplib`). [Source: architecture.md#Adapter-Protocol-Pattern]
- **Typed DTOs**: Return Pydantic models, never raw `dict`. [Source: architecture.md#Enforcement-Guidelines]
- **Health check**: Every adapter exposes `health_check() -> ServiceHealth`. [Source: architecture.md#Adapter-Protocol-Pattern]
- **Credentials never logged**: `api_key` and `password` are `SecretStr` in settings. Use `.get_secret_value()` only when passing to external APIs. [Source: architecture.md#Log-Sanitization]
- **Error handling**: Catch typed exceptions, never bare `except Exception`. Map to `ERPConnectionError` / `EmailConnectionError` where appropriate. Health check methods may use broad `except` as last resort since they must never crash. [Source: architecture.md#Process-Patterns]
- **Retry**: NOT in scope for this story. Retry logic will be added when actual CRUD operations are implemented (Epics 2-4). Health checks are simple pass/fail. [Source: architecture.md#Retry-Pattern-for-Adapters]

### Odoo XML-RPC Key Facts

- **No external dependency needed** — Python stdlib `xmlrpc.client` handles Odoo XML-RPC natively
- **Odoo API endpoints**:
  - `{url}/xmlrpc/2/common` — public (no auth): `version()` returns server info, `authenticate(db, login, password, {})` returns `uid` or `False`
  - `{url}/xmlrpc/2/object` — authenticated: `execute_kw(db, uid, password, model, method, args, kwargs)` for CRUD (NOT in scope for this story)
- **Async wrapping**: `xmlrpc.client.ServerProxy` is synchronous. Wrap all calls in `asyncio.to_thread()`:
  ```python
  import asyncio
  import xmlrpc.client

  async def _call_version(url: str) -> dict:
      proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
      return await asyncio.to_thread(proxy.version)

  async def _authenticate(url: str, db: str, user: str, key: str) -> int | bool:
      proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
      return await asyncio.to_thread(proxy.authenticate, db, user, key, {})
  ```
- **Health check strategy**: Call `version()` first (no auth, fast), then `authenticate()` (validates credentials). If version fails = connectivity issue. If authenticate returns `False` = bad credentials.
- **Type hint for xmlrpc**: `xmlrpc.client` is not fully typed. Use `# type: ignore[attr-defined]` where needed, or cast return values.

### IMAP Health Check Key Facts

- **No external dependency needed** — Python stdlib `imaplib` handles IMAP natively
- **Async wrapping**: `imaplib.IMAP4_SSL` is synchronous. Wrap entire connect-login-select-logout sequence in `asyncio.to_thread()`:
  ```python
  import asyncio
  import imaplib

  def _imap_health_sync(server: str, port: int, user: str, password: str, folder: str) -> None:
      """Synchronous IMAP health check — run via asyncio.to_thread."""
      conn = imaplib.IMAP4_SSL(server, port)
      try:
          conn.login(user, password)
          conn.select(folder)
      finally:
          try:
              conn.logout()
          except Exception:
              pass
  ```
- **Health check strategy**: Connect → login → select folder → logout. Tests all three failure modes: connectivity, authentication, folder existence.
- **IMAP4_SSL**: Always use SSL (port 993 default). Architecture specifies IMAP/TLS. [Source: architecture.md#Architectural-Boundaries]

### Health Endpoint Integration

The `/health` endpoint currently checks `database` and `llm`. This story adds `erp` and `email`, making it check 4 services total. The existing pattern in `health.py` handles this cleanly — just add more dependencies and service entries:

```python
@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_async_session),
    llm_adapter: OpenAICompatAdapter = Depends(get_llm_adapter),
    erp_adapter: OdooAdapter = Depends(get_erp_adapter),
    email_adapter: IMAPAdapter = Depends(get_email_adapter),
) -> dict[str, object]:
    db_health = await _check_database(session)
    llm_health = await llm_adapter.health_check()
    erp_health = await erp_adapter.health_check()
    email_health = await email_adapter.health_check()

    services = {
        "database": db_health,
        "llm": llm_health,
        "erp": erp_health,
        "email": email_health,
    }
    # ... existing degradation logic unchanged
```

**Cost consideration**: Unlike LLM health check (which costs tokens), ERP and IMAP health checks are free. Still cache for 30s to avoid hammering external servers on frequent `/health` polling.

### Existing Code to Build On

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/config.py` | `ERPSettings` with `url`, `database`, `username`, `api_key` (SecretStr) | Already complete — use as-is |
| `src/quote_agent/config.py` | `EmailSettings` with `imap_server`, `imap_port`, `username`, `password` (SecretStr), `folder`, `poll_interval` | Already complete — use as-is |
| `src/quote_agent/exceptions.py` | `ERPConnectionError(AdapterError)`, `EmailConnectionError(AdapterError)` | Already exist — use for typed errors |
| `src/quote_agent/api/health.py` | `/health` endpoint with `services` dict (currently `database` + `llm`) | Add `erp` and `email` keys |
| `src/quote_agent/api/health.py` | `ServiceHealth` model with `status` + `error` | Reuse for ERP/email health check return type |
| `src/quote_agent/adapters/erp/__init__.py` | Empty package placeholder (`"""Package erp."""`) | Populate with exports + `get_erp_adapter()` |
| `src/quote_agent/adapters/email/__init__.py` | Empty package placeholder (`"""Package email."""`) | Populate with exports + `get_email_adapter()` |
| `src/quote_agent/adapters/llm/__init__.py` | `get_llm_adapter()` pattern with `@lru_cache` | Copy this pattern for ERP and email |
| `src/quote_agent/adapters/llm/protocol.py` | `LLMAdapter` Protocol with `@runtime_checkable` | Follow same structure for `ERPAdapter` and `EmailAdapter` |
| `tests/conftest.py` | `env_vars` fixture already provides `ERP__*` and `EMAIL__*` vars | Reuse — no changes needed to conftest |

### Testing Pattern

Mock stdlib classes to avoid real connections:

```python
from unittest.mock import AsyncMock, MagicMock, patch

# ERP test
@patch("quote_agent.adapters.erp.odoo.xmlrpc.client.ServerProxy")
async def test_erp_health_healthy(mock_proxy_cls, adapter):
    mock_proxy = MagicMock()
    mock_proxy.version.return_value = {"server_version": "17.0"}
    mock_proxy.authenticate.return_value = 2  # uid
    mock_proxy_cls.return_value = mock_proxy
    result = await adapter.health_check()
    assert result.status == "healthy"

# Email test
@patch("quote_agent.adapters.email.imap.imaplib.IMAP4_SSL")
async def test_email_health_healthy(mock_imap_cls, adapter):
    mock_conn = MagicMock()
    mock_conn.login.return_value = ("OK", [b"Logged in"])
    mock_conn.select.return_value = ("OK", [b"42"])
    mock_imap_cls.return_value = mock_conn
    result = await adapter.health_check()
    assert result.status == "healthy"
```

For health endpoint integration tests, use FastAPI dependency overrides (same pattern as Story 1.4):

```python
from quote_agent.adapters.erp import get_erp_adapter
from quote_agent.adapters.email import get_email_adapter

app.dependency_overrides[get_erp_adapter] = lambda: mock_erp_adapter
app.dependency_overrides[get_email_adapter] = lambda: mock_email_adapter
```

**IMPORTANT**: Existing health tests (`tests/unit/test_health.py`) will need updating to also mock `get_erp_adapter` and `get_email_adapter` dependencies after the health endpoint is extended. Same situation as Story 1.4 which had to update tests for `get_llm_adapter`.

### File Locations

```
ai-quote-agent/
├── src/quote_agent/
│   └── adapters/
│       ├── erp/
│       │   ├── __init__.py              # MODIFY — add exports + get_erp_adapter()
│       │   ├── protocol.py              # NEW — ERPAdapter Protocol class
│       │   ├── odoo.py                  # NEW — OdooAdapter implementation
│       │   └── models.py               # NEW — OdooVersionInfo DTO (+ stubs)
│       └── email/
│           ├── __init__.py              # MODIFY — add exports + get_email_adapter()
│           ├── protocol.py              # NEW — EmailAdapter Protocol class
│           ├── imap.py                  # NEW — IMAPAdapter implementation
│           └── models.py               # NEW — IMAPHealthInfo DTO (+ stubs)
│   └── api/
│       └── health.py                   # MODIFY — add ERP + email services
└── tests/
    └── unit/
        ├── test_erp_adapter.py          # NEW — ERP adapter + health endpoint tests
        ├── test_email_adapter.py        # NEW — Email adapter + health endpoint tests
        └── test_health.py              # MODIFY — update existing tests to mock new adapters
```

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Call real Odoo/IMAP servers in unit tests | Mock `xmlrpc.client.ServerProxy` and `imaplib.IMAP4_SSL` |
| Use `requests` or `aiohttp` for Odoo XML-RPC | Use stdlib `xmlrpc.client` wrapped in `asyncio.to_thread` |
| Add `aioimaplib` dependency for health check | Use stdlib `imaplib` wrapped in `asyncio.to_thread` (add async lib in Story 2.1 when full ingestion is needed) |
| Call `str(settings.erp.api_key)` or `str(settings.email.password)` in logs | Use `.get_secret_value()` only when passing to external APIs |
| Create sync methods on adapters | ALL adapter methods must be `async` (wrap sync stdlib in `asyncio.to_thread`) |
| Return raw `dict` from adapter methods | Return typed `ServiceHealth` DTOs |
| Implement full ERP CRUD (get_products, create_draft_quote) | This story is CONFIG + HEALTH CHECK only — CRUD comes in Epics 3-4 |
| Implement full email ingestion (fetch_emails) | This story is CONFIG + HEALTH CHECK only — ingestion comes in Story 2.1 |
| Create new `ServiceHealth` model | Import existing one from `quote_agent.api.health` |
| Eagerly connect to ERP/IMAP on adapter init | Lazy connection — only connect when `health_check()` is called |
| Forget to update existing health tests | They will break once `/health` requires new adapter dependencies |

### Previous Story Intelligence (Story 1.4)

- **LLM adapter pattern is the blueprint**: Story 1.4 created `protocol.py` + `openai_compat.py` + `models.py` + `__init__.py` with `get_llm_adapter()`. Replicate this exact structure for ERP and email.
- **Health check caching**: LLM adapter uses `_last_health` + `_last_health_time` with 30s TTL. Use the same pattern.
- **Health endpoint extensibility**: The `services` dict was designed to accept new keys. Add `"erp"` and `"email"`.
- **Dependency override pattern**: Story 1.4 used `app.dependency_overrides[get_llm_adapter]` for testing — use same for `get_erp_adapter` and `get_email_adapter`.
- **`env_vars` fixture**: Already provides `ERP__URL`, `ERP__DATABASE`, `ERP__USERNAME`, `ERP__API_KEY`, `EMAIL__IMAP_SERVER`, `EMAIL__USERNAME`, `EMAIL__PASSWORD` — no changes needed to conftest.
- **Cache clearing**: Remember to clear `get_settings.cache_clear()` and any adapter caches between tests.
- **ChatOpenAI mock lesson**: Pydantic model instances intercept `__setattr__`. For stdlib classes like `ServerProxy` and `IMAP4_SSL`, standard `patch` on the class constructor works fine — no Pydantic gotchas here.
- **Existing test updates required**: Story 1.4 had to update Story 1.3 health tests to mock the new LLM dependency. Same will happen here — existing health tests need `get_erp_adapter` and `get_email_adapter` mocks.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Commits for Epic 1 so far:
- `98cc075` feat: add FastAPI server with health check and API v1 base endpoint (Story 1.3)
- `2482e07` feat: add PostgreSQL database foundation with async SQLAlchemy & Alembic migrations (Story 1.2)
- `7f9383a` feat: add project scaffolding & type-safe configuration system (Story 1.1)

Story 1.4 is done but not yet committed (changes are staged/unstaged in working tree).

### Dependencies to Add

**None.** Both `xmlrpc.client` and `imaplib` are Python stdlib. No `uv add` needed.

### Scope Boundaries

- **IN scope**: ERP adapter Protocol + Odoo implementation (health check only), Email adapter Protocol + IMAP implementation (health check only), health endpoint integration, typed DTOs, factory functions, unit tests
- **OUT of scope**: Full ERP CRUD operations (`get_products`, `create_draft_quote`, `get_client` — Epic 3/4), full email ingestion (`fetch_emails` — Story 2.1), retry/circuit breaker pattern (add when CRUD operations are implemented), notification adapter (Story 1.6), structured logging setup (Epic 7), `aioimaplib` async IMAP library (add in Story 2.1 if needed)

### References

- [Source: architecture.md#Structure-Patterns] — adapter organization (protocol.py + impl.py + models.py)
- [Source: architecture.md#Adapter-Protocol-Pattern] — Protocol class design, async methods, health_check, ERPAdapter example
- [Source: architecture.md#Process-Patterns] — error handling, exception hierarchy
- [Source: architecture.md#Enforcement-Guidelines] — typed DTOs, no raw dict, mypy --strict
- [Source: architecture.md#Architectural-Boundaries] — Agent → ERP: XML-RPC/JSON-RPC, Agent → IMAP: IMAP/TLS
- [Source: architecture.md#Complete-Project-Directory-Structure] — file locations for erp/, email/ adapters
- [Source: epics.md#Story-1.5] — acceptance criteria, user story
- [Source: prd.md#FR46] — IT operator can configure ERP and email connections
- [Source: prd.md#NFR-I4] — Email ingestion supports standard IMAP protocol
- [Source: prd.md#NFR-I5] — All integrations have health checks and automated alerting on failure
- [Source: _bmad-output/implementation-artifacts/1-4-configuration-llm-provider-adapter.md] — previous story learnings, adapter pattern blueprint

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Ruff flagged `try/except/pass` in IMAP logout — replaced with `contextlib.suppress(Exception)`

### Completion Notes List

- Implemented ERP adapter (Odoo XML-RPC) with Protocol + OdooAdapter + OdooVersionInfo DTO
- Implemented Email adapter (IMAP) with Protocol + IMAPAdapter + IMAPHealthInfo DTO
- Both adapters follow the exact same pattern as LLM adapter: lazy init, async health_check with 30s cache, SecretStr credentials handling
- Wired both adapters into `/health` endpoint — now checks 4 services (database, llm, erp, email)
- Updated existing health tests (test_health.py, test_llm_adapter.py) to mock the new ERP/email adapter dependencies
- 13 new tests across test_erp_adapter.py (6) and test_email_adapter.py (7)
- Full suite: 51 passed, 2 skipped (integration tests needing real DB)
- Zero new dependencies — both `xmlrpc.client` and `imaplib` are Python stdlib

### Change Log

- 2026-03-18: Story 1.5 implementation complete — ERP and email adapter configuration with health checks
- 2026-03-18: Code review fixes — broadened xmlrpc exception catch (`Fault` → `Error`), extracted test helpers to conftest.py, added ProtocolError test

### File List

- `src/quote_agent/adapters/erp/__init__.py` — MODIFIED: added exports + `get_erp_adapter()` factory
- `src/quote_agent/adapters/erp/models.py` — NEW: `OdooVersionInfo` DTO
- `src/quote_agent/adapters/erp/protocol.py` — NEW: `ERPAdapter` Protocol class
- `src/quote_agent/adapters/erp/odoo.py` — NEW: `OdooAdapter` implementation with XML-RPC health check
- `src/quote_agent/adapters/email/__init__.py` — MODIFIED: added exports + `get_email_adapter()` factory
- `src/quote_agent/adapters/email/models.py` — NEW: `IMAPHealthInfo` DTO
- `src/quote_agent/adapters/email/protocol.py` — NEW: `EmailAdapter` Protocol class
- `src/quote_agent/adapters/email/imap.py` — NEW: `IMAPAdapter` implementation with IMAP health check
- `src/quote_agent/api/health.py` — MODIFIED: added ERP + email services to health endpoint
- `tests/conftest.py` — MODIFIED: extracted shared test helpers (`create_test_app`, `mock_healthy_adapter`, `mock_healthy_session`)
- `tests/unit/test_erp_adapter.py` — NEW: 7 ERP adapter tests (added ProtocolError test)
- `tests/unit/test_email_adapter.py` — NEW: 7 email adapter tests
- `tests/unit/test_health.py` — MODIFIED: updated to use shared conftest helpers
- `tests/unit/test_llm_adapter.py` — MODIFIED: updated to use shared conftest helpers
