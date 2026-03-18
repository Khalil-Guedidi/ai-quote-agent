# Story 1.6: Configuration Canal de Notification

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator**,
I want to configure notification channel preferences (Teams webhook URL),
So that the system can notify sales reps through the company's communication tools.

## Acceptance Criteria

1. **AC-1.6.1**: Notification adapter validates Teams webhook configuration
   - Given `NOTIFICATION__TEAMS_WEBHOOK_URL` is set in `.env` (and optionally `NOTIFICATION__CHANNEL=teams`)
   - When the Teams notification adapter is initialized with `NotificationSettings` from `settings.notification`
   - Then it validates the webhook URL format (must be a valid HTTPS URL)
   - And exposes an async `health_check()` method returning `ServiceHealth`
   - And the webhook URL is never logged in full (treat as semi-sensitive — log only the hostname)

2. **AC-1.6.2**: Notification adapter follows the adapter pattern
   - Then `adapters/notification/protocol.py` defines a `NotificationAdapter` Protocol class with `@runtime_checkable`
   - And `adapters/notification/teams.py` implements `TeamsAdapter`
   - And `adapters/notification/models.py` defines typed DTOs
   - And the Protocol interface is documented and extensible (Teams is the first implementation)
   - And future methods (`send_notification`) are stubbed as comments in the Protocol

3. **AC-1.6.3**: Health check detects webhook unavailability
   - Given the Teams webhook URL is unreachable or invalid
   - When `health_check()` is called
   - Then it returns `ServiceHealth(status="unhealthy", error="<descriptive message>")`
   - And the `/health` endpoint reflects degradation in `services.notification`

4. **AC-1.6.4**: Health endpoint includes notification service
   - Given the system is running
   - When I call `GET /health`
   - Then the response includes `services.notification` alongside database, llm, erp, email
   - And overall status is `"degraded"` if notification is unhealthy

5. **AC-1.6.5**: Tests pass
   - Given the test suite exists
   - When I run `uv run pytest tests/unit/test_notification_adapter.py`
   - Then all tests pass (healthy check, unhealthy check, invalid URL, protocol compliance, health endpoint)
   - And `uv run ruff check src/ tests/` and `uv run mypy src/` both succeed

## Tasks / Subtasks

- [x] Task 1: Create Notification adapter DTOs (AC: 2)
  - [x] 1.1: Create `src/quote_agent/adapters/notification/models.py` with Pydantic DTOs:
    - `TeamsWebhookInfo` — `hostname: str` (extracted from webhook URL for diagnostics, never the full URL)
    - Stub future DTOs as comments: `NotificationPayload`, `NotificationResult` (will be implemented in Epic 5 stories)

- [x] Task 2: Create Notification adapter Protocol (AC: 2)
  - [x] 2.1: Create `src/quote_agent/adapters/notification/protocol.py` with:
    - `NotificationAdapter` Protocol class with `@runtime_checkable`:
      - `async def health_check(self) -> ServiceHealth` — check notification channel connectivity
    - Stub future methods as comments: `send_notification` (NOT implemented yet — comes in Epic 5)

- [x] Task 3: Implement TeamsAdapter (AC: 1, 3)
  - [x] 3.1: Create `src/quote_agent/adapters/notification/teams.py` with `TeamsAdapter`:
    - Constructor takes `NotificationSettings` (from `settings.notification`)
    - Validates `teams_webhook_url` is a non-empty HTTPS URL on init (raise `ConfigurationError` if invalid)
    - Stores settings but does NOT eagerly connect
    - `health_check() -> ServiceHealth`:
      1. Validate the URL format (non-empty, starts with `https://`)
      2. Use `httpx.AsyncClient` to send a POST request with a minimal empty JSON body `{}` to the webhook URL (with a 5s timeout)
      3. Accept any HTTP response (2xx, 4xx) as "reachable" — the server responded. Only treat connection failures as unhealthy
      4. Return `ServiceHealth(status="healthy")` if the server responds
      5. Catch `httpx.ConnectError`, `httpx.TimeoutException`, `httpx.InvalidURL`, `OSError` → return `ServiceHealth(status="unhealthy", error=str(exc))`
    - Health check caching: same 30s TTL pattern as other adapters (`_last_health` + `_last_health_time`)
    - Use `_HEALTH_CHECK_TIMEOUT = 5.0` with httpx timeout parameter
  - [x] 3.2: URL handling: log only `urlparse(url).hostname` for diagnostics — never the full webhook URL (it contains tokens)

- [x] Task 4: Wire notification adapter into health endpoint (AC: 4)
  - [x] 4.1: Create `get_notification_adapter() -> TeamsAdapter` cached singleton in `adapters/notification/__init__.py` (same pattern as `get_erp_adapter`)
  - [x] 4.2: Update `src/quote_agent/api/health.py`:
    - Import `get_notification_adapter`
    - Add notification health check alongside existing DB + LLM + ERP + email checks
    - Add `"notification"` key to the `services` dict in `HealthResponse`
    - Overall status: `"degraded"` if ANY service is unhealthy (existing logic handles this)
  - [x] 4.3: Update `adapters/notification/__init__.py` with proper exports

- [x] Task 5: Write tests (AC: 5)
  - [x] 5.1: Create `tests/unit/test_notification_adapter.py` with:
    - `test_health_check_returns_healthy_on_success` — mock `httpx.AsyncClient.post` to return a 200 response
    - `test_health_check_returns_unhealthy_on_connection_error` — mock to raise `httpx.ConnectError`
    - `test_health_check_returns_unhealthy_on_timeout` — mock to raise `httpx.TimeoutException`
    - `test_health_check_returns_unhealthy_on_empty_webhook_url` — pass empty webhook URL, verify ConfigurationError on init
    - `test_health_check_returns_unhealthy_on_non_https_url` — pass `http://` URL, verify ConfigurationError on init
    - `test_health_check_caches_result` — verify second call within 30s returns cached result without hitting httpx
    - `test_adapter_conforms_to_protocol` — verify `TeamsAdapter` satisfies `NotificationAdapter` protocol
    - `test_health_endpoint_includes_notification_service` — use `httpx.AsyncClient` with `ASGITransport` to hit `/health`, assert `services.notification` present
  - [x] 5.2: Update `tests/conftest.py`:
    - Add `get_notification_adapter` to `create_test_app()` cache clearing
    - The existing `mock_healthy_adapter()` helper works for notification too
  - [x] 5.3: Update existing health tests in `tests/unit/test_health.py` and other adapter tests to mock `get_notification_adapter` dependency (same as Story 1.5 had to update for ERP/email)
  - [x] 5.4: Verify `uv run ruff check src/ tests/` and `uv run mypy src/` both pass

## Dev Notes

### Architecture Compliance

- **Adapter Pattern**: Every adapter follows `protocol.py` (interface) + `{impl}.py` (implementation) + `models.py` (DTOs). [Source: architecture.md#Structure-Patterns]
- **All methods async**: Every adapter method must be `async`. httpx already provides async support natively — no `asyncio.to_thread` wrapping needed. [Source: architecture.md#Adapter-Protocol-Pattern]
- **Typed DTOs**: Return Pydantic models, never raw `dict`. [Source: architecture.md#Enforcement-Guidelines]
- **Health check**: Every adapter exposes `health_check() -> ServiceHealth`. [Source: architecture.md#Adapter-Protocol-Pattern]
- **URL security**: Webhook URLs contain embedded tokens (e.g., Teams incoming webhook URLs include an API token in the path). Treat as semi-sensitive — log only hostname for diagnostics. [Source: architecture.md#Log-Sanitization]
- **Error handling**: Catch typed exceptions, never bare `except Exception`. Use `NotificationError` from exceptions.py where appropriate. Health check methods may use broad `except` as last resort since they must never crash. [Source: architecture.md#Process-Patterns]
- **Retry**: NOT in scope for this story. Retry logic will be added when actual notification sending is implemented (Epic 5). Health checks are simple pass/fail. [Source: architecture.md#Retry-Pattern-for-Adapters]

### Teams Webhook Key Facts

- **Microsoft Teams Incoming Webhooks**: Accept HTTP POST requests with a JSON payload (MessageCard or Adaptive Card format)
- **Webhook URL pattern**: `https://*.webhook.office.com/webhookb2/...` — contains embedded tokens, treat as semi-sensitive
- **Health check strategy**: Send a POST with minimal `{}` body. Any HTTP response (including 400 Bad Request for malformed payload) confirms the server is reachable. Only connection failures indicate unhealthy status
- **httpx is already available**: Used in tests for `ASGITransport` — it's a project dependency. Use `httpx.AsyncClient` for the webhook health check
- **No Teams SDK dependency needed**: Direct HTTP POST via httpx is sufficient for webhook interactions. The Adaptive Card JSON payload will be implemented in Epic 5

### Health Endpoint Integration

The `/health` endpoint currently checks `database`, `llm`, `erp`, and `email` (4 services). This story adds `notification`, making it check 5 services total. The existing pattern in `health.py` handles this cleanly — just add one more dependency and service entry:

```python
@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_async_session),
    llm_adapter: OpenAICompatAdapter = Depends(get_llm_adapter),
    erp_adapter: OdooAdapter = Depends(get_erp_adapter),
    email_adapter: IMAPAdapter = Depends(get_email_adapter),
    notification_adapter: TeamsAdapter = Depends(get_notification_adapter),
) -> dict[str, object]:
    db_health = await _check_database(session)
    llm_health = await llm_adapter.health_check()
    erp_health = await erp_adapter.health_check()
    email_health = await email_adapter.health_check()
    notification_health = await notification_adapter.health_check()

    services = {
        "database": db_health,
        "llm": llm_health,
        "erp": erp_health,
        "email": email_health,
        "notification": notification_health,
    }
    # ... existing degradation logic unchanged
```

### Existing Code to Build On

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/config.py` | `NotificationSettings` with `channel` ("teams"), `teams_webhook_url` ("") | Already complete — use as-is |
| `src/quote_agent/exceptions.py` | `NotificationError(AdapterError)` | Already exists — use for typed errors |
| `src/quote_agent/api/health.py` | `/health` endpoint with `services` dict (currently 4 services) | Add `notification` key |
| `src/quote_agent/api/health.py` | `ServiceHealth` model with `status` + `error` | Reuse for notification health check return type |
| `src/quote_agent/adapters/notification/__init__.py` | Empty package placeholder (`"""Package notification."""`) | Populate with exports + `get_notification_adapter()` |
| `src/quote_agent/adapters/llm/__init__.py` | `get_llm_adapter()` pattern with `@lru_cache` | Copy this pattern for notification |
| `src/quote_agent/adapters/erp/protocol.py` | `ERPAdapter` Protocol with `@runtime_checkable` | Follow same structure for `NotificationAdapter` |
| `tests/conftest.py` | `create_test_app()`, `mock_healthy_adapter()`, env_vars fixture | Reuse — update `create_test_app()` to clear notification adapter cache |

### Testing Pattern

Mock httpx to avoid real webhook calls:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

# Healthy check
@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_notification_health_healthy(mock_client_cls, adapter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client
    result = await adapter.health_check()
    assert result.status == "healthy"

# Unhealthy check (connection error)
@patch("quote_agent.adapters.notification.teams.httpx.AsyncClient")
async def test_notification_health_unhealthy(mock_client_cls, adapter):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client_cls.return_value = mock_client
    result = await adapter.health_check()
    assert result.status == "unhealthy"
```

For health endpoint integration tests, use FastAPI dependency overrides (same pattern as previous stories):

```python
from quote_agent.adapters.notification import get_notification_adapter

app.dependency_overrides[get_notification_adapter] = lambda: mock_notification_adapter
```

**IMPORTANT**: Existing health tests (`tests/unit/test_health.py`, `test_erp_adapter.py`, `test_email_adapter.py`, `test_llm_adapter.py`) will need updating to also mock `get_notification_adapter` dependency after the health endpoint is extended. Same situation as Story 1.5 which had to update tests for `get_erp_adapter` and `get_email_adapter`.

### File Locations

```
ai-quote-agent/
├── src/quote_agent/
│   └── adapters/
│       └── notification/
│           ├── __init__.py              # MODIFY — add exports + get_notification_adapter()
│           ├── protocol.py              # NEW — NotificationAdapter Protocol class
│           ├── teams.py                 # NEW — TeamsAdapter implementation
│           └── models.py               # NEW — TeamsWebhookInfo DTO (+ stubs)
│   └── api/
│       └── health.py                   # MODIFY — add notification service
└── tests/
    ├── conftest.py                     # MODIFY — update create_test_app() for notification cache
    └── unit/
        ├── test_notification_adapter.py # NEW — notification adapter + health endpoint tests
        ├── test_health.py              # MODIFY — update to mock notification adapter
        ├── test_erp_adapter.py         # MODIFY — update health endpoint tests to mock notification
        ├── test_email_adapter.py       # MODIFY — update health endpoint tests to mock notification
        └── test_llm_adapter.py         # MODIFY — update health endpoint tests to mock notification
```

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Call real Teams webhook endpoints in unit tests | Mock `httpx.AsyncClient` |
| Log the full webhook URL (contains tokens) | Log only `urlparse(url).hostname` |
| Add `pymsteams` or other Teams SDK dependencies | Use `httpx` (already a project dependency) for direct HTTP POST |
| Return raw `dict` from adapter methods | Return typed `ServiceHealth` DTOs |
| Create sync methods on adapters | ALL adapter methods must be `async` |
| Implement full notification sending (Adaptive Cards, batching) | This story is CONFIG + HEALTH CHECK only — sending comes in Epic 5 |
| Create new `ServiceHealth` model | Import existing one from `quote_agent.api.health` |
| Eagerly connect to webhook on adapter init | Validate URL format on init, but only check connectivity in `health_check()` |
| Forget to update existing health tests | They will break once `/health` requires new notification adapter dependency |
| Accept `http://` URLs for webhooks | Validate HTTPS only — Teams webhooks require TLS |

### Previous Story Intelligence (Story 1.5)

- **ERP/Email adapter pattern is the blueprint**: Story 1.5 created `protocol.py` + `odoo.py`/`imap.py` + `models.py` + `__init__.py` with factory functions. Replicate this exact structure for notification.
- **Health check caching**: All adapters use `_last_health` + `_last_health_time` with 30s TTL. Use the same pattern.
- **Health endpoint extensibility**: The `services` dict was designed to accept new keys. Add `"notification"`.
- **Dependency override pattern**: Stories 1.4 and 1.5 used `app.dependency_overrides[get_*_adapter]` for testing — use same for `get_notification_adapter`.
- **Cache clearing**: Remember to clear `get_settings.cache_clear()` and `get_notification_adapter.cache_clear()` between tests.
- **Existing test updates required**: Story 1.5 had to update Story 1.3/1.4 health tests to mock the new ERP/email dependencies. Same will happen here — ALL existing health endpoint tests need `get_notification_adapter` mocks.
- **`create_test_app()` in conftest**: Must be updated to also clear the notification adapter cache.
- **`mock_healthy_adapter()` helper**: Already generic enough — works for notification adapter too.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Commits for Epic 1:
- `4a6b980` feat: add ERP and email adapter configuration with health checks (Story 1.5)
- `c3b1a5c` feat: add LLM provider adapter with OpenAI-compatible interface (Story 1.4)
- `98cc075` feat: add FastAPI server with health check and API v1 base endpoint (Story 1.3)
- `2482e07` feat: add PostgreSQL database foundation with async SQLAlchemy & Alembic migrations (Story 1.2)

### Dependencies to Add

**None new.** `httpx` is already a project dependency (used in tests for `ASGITransport`). No `uv add` needed.

### Scope Boundaries

- **IN scope**: Notification adapter Protocol + Teams implementation (health check only), health endpoint integration, typed DTOs, factory function, unit tests, URL format validation
- **OUT of scope**: Sending actual Teams Adaptive Cards (Epic 5), notification batching logic (Story 5.5), multiple notification channels simultaneously (Story 5.6), Slack/WhatsApp/email notification adapters (post-MVP), notification tone/content templates (UX-DR22 — Epic 5), retry/circuit breaker pattern (add when actual sending is implemented)

### References

- [Source: architecture.md#Structure-Patterns] — adapter organization (protocol.py + impl.py + models.py)
- [Source: architecture.md#Adapter-Protocol-Pattern] — Protocol class design, async methods, health_check
- [Source: architecture.md#Process-Patterns] — error handling, exception hierarchy
- [Source: architecture.md#Enforcement-Guidelines] — typed DTOs, no raw dict, mypy --strict
- [Source: architecture.md#Complete-Project-Directory-Structure] — file locations for notification/ adapter
- [Source: architecture.md#Log-Sanitization] — never log secrets or sensitive URLs
- [Source: epics.md#Story-1.6] — acceptance criteria, user story
- [Source: prd.md#FR33-36] — notification channel requirements
- [Source: prd.md#FR48] — IT operator can configure notification channel preferences
- [Source: prd.md#NFR-I3] — notification channel interface allows adding new channels via adapter implementation only
- [Source: prd.md#NFR-P5] — notification delivery < 30 seconds
- [Source: ux-design-specification.md] — Teams Adaptive Cards as primary notification surface (Epic 5 scope)
- [Source: _bmad-output/implementation-artifacts/1-5-configuration-connexions-erp-email.md] — previous story learnings, adapter pattern blueprint

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no blockers.

### Completion Notes List

- Created notification adapter following the established adapter pattern (protocol + implementation + models + factory)
- TeamsAdapter validates HTTPS webhook URL on init, raises ConfigurationError for invalid/empty URLs
- Health check uses httpx.AsyncClient POST with 5s timeout; any HTTP response = healthy, connection failure = unhealthy
- 30s health check caching with _last_health + _last_health_time (consistent with ERP/email adapters)
- URL security: only hostname logged via urlparse, never the full webhook URL (contains tokens)
- Health endpoint now checks 5 services: database, llm, erp, email, notification
- 8 new tests in test_notification_adapter.py; updated 4 existing test files to mock get_notification_adapter
- All 60 tests pass, ruff clean, mypy clean

### Change Log

- 2026-03-18: Implemented Story 1.6 — notification adapter with Teams webhook health check

### File List

New files:
- src/quote_agent/adapters/notification/models.py
- src/quote_agent/adapters/notification/protocol.py
- src/quote_agent/adapters/notification/teams.py
- tests/unit/test_notification_adapter.py

Modified files:
- src/quote_agent/adapters/notification/__init__.py
- src/quote_agent/api/health.py
- tests/conftest.py
- tests/unit/test_health.py
- tests/unit/test_erp_adapter.py
- tests/unit/test_email_adapter.py
- tests/unit/test_llm_adapter.py
- _bmad-output/implementation-artifacts/sprint-status.yaml
