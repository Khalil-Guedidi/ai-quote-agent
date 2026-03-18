# Story 2.1: Reception Email via IMAP

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to automatically receive incoming quote request emails from the mail server,
So that I don't have to forward or manually trigger processing for each request.

## Acceptance Criteria

1. **AC-2.1.1**: Agent detects and retrieves new emails within its polling cycle
   - Given the IMAP connection is configured and active
   - When a new email arrives in the monitored folder
   - Then the agent detects and retrieves the email within its polling cycle
   - And the email is persisted in the `email_requests` table with status `received`
   - And no email is ever lost (acknowledged and tracked to completion or explicit failure)

2. **AC-2.1.2**: Resilience — exponential backoff and circuit breaker on IMAP failure
   - Given the IMAP server is temporarily unavailable
   - When the agent attempts to poll
   - Then it retries with exponential backoff (1s -> 2s -> 4s, max 3 retries)
   - And an alert is raised after circuit breaker threshold (5 consecutive failures)

## Tasks / Subtasks

- [x] Task 1: Create `email_requests` SQLAlchemy model + Alembic migration (AC: 1)
  - [x] 1.1: Create `src/quote_agent/models/email_request.py` with `EmailRequest` model
    - Table: `email_requests`
    - Columns: `id` (UUID PK), `message_id` (unique, the IMAP Message-ID header), `subject`, `sender`, `recipients` (JSON list), `raw_content` (text), `folder` (str), `status` (str, default `received`), `error_message` (optional text), `received_at` (datetime from email Date header), `created_at`, `updated_at` (via TimestampMixin)
    - Index on `message_id` (unique) for deduplication
    - Index on `status` for queue-style polling
  - [x] 1.2: Register model in `models/__init__.py` for Alembic auto-detection
  - [x] 1.3: Generate Alembic migration: `uv run alembic revision --autogenerate -m "add email_requests table"`
  - [x] 1.4: Test migration up/down: `uv run alembic upgrade head` / `uv run alembic downgrade -1`

- [x] Task 2: Create `IncomingEmail` DTO in adapter models (AC: 1)
  - [x] 2.1: Add `IncomingEmail` Pydantic model to `src/quote_agent/adapters/email/models.py`
    - Fields: `message_id` (str), `subject` (str), `sender` (str), `recipients` (list[str]), `raw_content` (str), `received_at` (datetime | None)
  - [x] 2.2: Export from `__init__.py`

- [x] Task 3: Extend `EmailAdapter` protocol + `IMAPAdapter` with `fetch_new_emails()` (AC: 1)
  - [x] 3.1: Add `async def fetch_new_emails(self) -> list[IncomingEmail]` to `EmailAdapter` protocol
  - [x] 3.2: Implement in `IMAPAdapter`:
    - Connect via `imaplib.IMAP4_SSL` (existing pattern, wrapped with `asyncio.to_thread`)
    - Search for UNSEEN emails in configured folder
    - Fetch each email (RFC822), parse with `email.message_from_bytes` (stdlib)
    - Extract: Message-ID, Subject, From, To/Cc, Date, body (prefer text/plain, fallback text/html stripped)
    - Mark fetched emails as SEEN on the IMAP server
    - Return list of `IncomingEmail`
  - [x] 3.3: Handle IMAP errors — raise `EmailConnectionError` on connection/auth failures

- [x] Task 4: Implement polling loop with backoff and circuit breaker (AC: 1, 2)
  - [x] 4.1: Create `src/quote_agent/services/email_poller.py` with `EmailPollerService`
    - Async polling loop: `while running: fetch -> persist -> sleep(poll_interval)`
    - Uses `EmailSettings.poll_interval` (default 60s) for sleep between polls
  - [x] 4.2: Implement exponential backoff on IMAP failure: 1s -> 2s -> 4s, max 3 retries per poll attempt
  - [x] 4.3: Implement circuit breaker: after 5 consecutive failures, log alert and pause polling for 60s before retrying
  - [x] 4.4: Persist each fetched email to `email_requests` table via async session
    - Deduplicate by `message_id` — skip if already exists
    - Set `status = "received"` on insert
  - [x] 4.5: Add structured JSON logging for each poll: emails found, emails persisted, errors

- [x] Task 5: Integrate poller into application lifecycle (AC: 1)
  - [x] 5.1: Start `EmailPollerService` as background task in FastAPI lifespan (`main.py`)
  - [x] 5.2: Graceful shutdown — cancel polling task on app shutdown, log final state
  - [x] 5.3: Add poller status to `/health` endpoint (optional — shows last poll time, emails processed count)

- [x] Task 6: Write tests (AC: 1, 2)
  - [x] 6.1: Unit tests for `EmailRequest` model (fields, defaults, constraints)
  - [x] 6.2: Unit tests for `IncomingEmail` DTO (validation, serialization)
  - [x] 6.3: Unit tests for `IMAPAdapter.fetch_new_emails()` — mock `imaplib.IMAP4_SSL`
    - Test: fetches UNSEEN emails, parses correctly, marks as SEEN
    - Test: empty mailbox returns empty list
    - Test: connection failure raises `EmailConnectionError`
    - Test: auth failure raises `EmailConnectionError`
  - [x] 6.4: Unit tests for `EmailPollerService`
    - Test: successful poll -> emails persisted with status `received`
    - Test: duplicate `message_id` is skipped (deduplication)
    - Test: IMAP failure triggers exponential backoff (1s, 2s, 4s)
    - Test: 5 consecutive failures triggers circuit breaker (60s pause)
    - Test: circuit breaker resets after successful poll
    - Test: graceful shutdown cancels polling task
  - [x] 6.5: Update existing health endpoint tests if poller status is added

## Dev Notes

### Architecture Compliance

- **Adapter pattern**: Extend existing `protocol.py` / `imap.py` / `models.py` — do NOT create new adapter files. Follow the exact pattern from Epic 1 (Protocol + Implementation + DTOs + Factory). [Source: architecture.md#Adapter-Pattern, epic-1-retro]
- **Database model**: `src/quote_agent/models/email_request.py` — exactly as specified in architecture directory structure. Use `Base` + `TimestampMixin` from `models/base.py`. [Source: architecture.md#Complete-Project-Directory-Structure]
- **Service layer**: `src/quote_agent/services/email_poller.py` — new service for polling orchestration. Architecture specifies services for orchestration logic. [Source: architecture.md#Services-Layer]
- **Sync IMAP via asyncio.to_thread**: Continue using stdlib `imaplib` wrapped with `asyncio.to_thread()`. This pattern is established in the codebase (Story 1.5) and avoids adding a new dependency. Do NOT use `aioimaplib` — it adds complexity and the health check already uses this approach. [Source: epic-1-retro#Established-Patterns]
- **Retry pattern**: Exponential backoff 1s -> 2s -> 4s, max 3 retries. Circuit breaker at 5 consecutive failures, service marked "down" for 60s. [Source: architecture.md#Retry-Pattern-for-Adapters]
- **Exception hierarchy**: Use existing `EmailConnectionError(AdapterError)` for IMAP failures. [Source: src/quote_agent/exceptions.py]

### Existing Code to Extend

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/adapters/email/protocol.py` | `health_check()` only, comment says "Future: fetch_emails" | Add `fetch_new_emails()` method |
| `src/quote_agent/adapters/email/imap.py` | `IMAPAdapter` with health check, `asyncio.to_thread` pattern | Add `fetch_new_emails()` implementation |
| `src/quote_agent/adapters/email/models.py` | `IMAPHealthInfo` only, comment says "Future: IncomingEmail" | Add `IncomingEmail` DTO |
| `src/quote_agent/adapters/email/__init__.py` | Exports `EmailAdapter`, factory | Add `IncomingEmail` export |
| `src/quote_agent/models/base.py` | `Base`, `TimestampMixin`, async session | Reuse as-is |
| `src/quote_agent/models/__init__.py` | Package init | Register `EmailRequest` for Alembic |
| `src/quote_agent/config.py` | `EmailSettings` with `poll_interval=60` | Reuse as-is — settings already exist |
| `src/quote_agent/exceptions.py` | `EmailConnectionError` | Reuse as-is |
| `src/quote_agent/main.py` | FastAPI lifespan, exception handlers | Add poller background task to lifespan |
| `tests/unit/test_email_adapter.py` | 7 tests for health check | Add `fetch_new_emails` tests in same file |

### Technical Implementation Details

**Email parsing** — Use stdlib `email` module (`email.message_from_bytes`, `email.utils.parsedate_to_datetime`). Extract:
- `Message-ID` header for deduplication (critical — this is the unique identifier)
- `Subject`, `From`, `To`, `Cc` headers
- `Date` header parsed to datetime
- Body: prefer `text/plain` part, fallback to `text/html` with tag stripping (basic — full cleaning is Story 2.2)

**IMAP fetch sequence** (sync, run via `asyncio.to_thread`):
```python
conn = IMAP4_SSL(server, port)
conn.login(user, password)
conn.select(folder)
_, msg_ids = conn.search(None, "UNSEEN")
for msg_id in msg_ids[0].split():
    _, data = conn.fetch(msg_id, "(RFC822)")
    conn.store(msg_id, "+FLAGS", "\\Seen")
conn.logout()
```

**Deduplication** — `message_id` column with unique constraint. On insert, catch `IntegrityError` and skip. This is idempotent — polling the same email twice is safe.

**Polling loop** (simplified):
```python
async def run(self):
    while self._running:
        try:
            emails = await self._adapter.fetch_new_emails()
            await self._persist_emails(emails)
            self._consecutive_failures = 0
        except EmailConnectionError:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 5:
                logger.error("Circuit breaker triggered")
                await asyncio.sleep(60)
            else:
                backoff = 2 ** (self._consecutive_failures - 1)
                await asyncio.sleep(backoff)
            continue
        await asyncio.sleep(self._poll_interval)
```

### Project Structure Notes

New files:
- `src/quote_agent/models/email_request.py` — SQLAlchemy model
- `src/quote_agent/services/email_poller.py` — polling service
- `alembic/versions/{hash}_add_email_requests_table.py` — auto-generated migration

Modified files:
- `src/quote_agent/adapters/email/protocol.py` — add `fetch_new_emails`
- `src/quote_agent/adapters/email/imap.py` — implement `fetch_new_emails`
- `src/quote_agent/adapters/email/models.py` — add `IncomingEmail`
- `src/quote_agent/adapters/email/__init__.py` — export `IncomingEmail`
- `src/quote_agent/models/__init__.py` — register `EmailRequest`
- `src/quote_agent/main.py` — start/stop poller in lifespan
- `tests/unit/test_email_adapter.py` — add fetch tests

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Use `aioimaplib` or any new IMAP library | Use stdlib `imaplib` + `asyncio.to_thread()` (established pattern) |
| Create a new adapter file for fetching | Extend existing `imap.py` — it's the same adapter |
| Store raw email as bytes/blob | Store as text (str) — simpler, searchable |
| Use IMAP IDLE for push notifications | Use simple polling with `poll_interval` — sufficient for 300 quotes/day |
| Hardcode retry/backoff values | Use constants at module level (like `_HEALTH_CHECK_TIMEOUT` pattern) |
| Catch bare `except Exception` in polling | Catch `EmailConnectionError` specifically, let unexpected errors propagate |
| Create email_requests table manually | Use Alembic migration — the project has this set up since Story 1.2 |
| Use `datetime.now()` for timestamps | Use `server_default=func.now()` in SQLAlchemy (established pattern) |
| Import `EmailRequest` model at top of poller | Use lazy import or pass session factory — avoid circular imports |
| Mock database in poller unit tests | Mock the session and adapter — no real DB in unit tests (integration tests in `tests/integration/`) |

### Scope Boundaries

- **IN scope**: IMAP fetch UNSEEN, parse to DTO, persist to DB, polling loop, backoff, circuit breaker, deduplication, graceful shutdown, unit tests
- **OUT of scope**: Email content cleaning (Story 2.2), structured data extraction (Story 2.3), multi-request splitting (Story 2.4), prompt injection defense (Story 2.5), attachment handling (not in MVP), IMAP IDLE push, email filtering/routing rules

### Previous Story Intelligence (Epic 1 Retrospective)

- **Adapter pattern is locked**: Protocol + Implementation + DTOs + Factory. Do not deviate.
- **asyncio.to_thread() for sync stdlib**: Proven pattern for imaplib, xmlrpc. Continue using it.
- **Health check caching (30s TTL)**: Keep existing health check. Poller is separate from health check.
- **Pydantic + mocking friction**: Use class-level patching, not instance-level, when mocking Pydantic models.
- **Test helpers in conftest**: Use `conftest.py` shared fixtures. Add new fixtures for email-specific mocking.
- **Runtime vs dev dependency audit**: No new dependencies needed for this story (stdlib `email` + `imaplib`).
- **Integration test segregation**: Poller integration tests (with real DB) go in `tests/integration/`, not `tests/unit/`.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Last commits:
- `fcd7aec` docs: add Epic 1 retrospective and update sprint status
- `46d08d5` feat: add CI/CD pipeline with GitHub Actions (Story 1.8)
- `56af67e` feat: add Docker deployment and CLI tools (Story 1.7)

68 tests pass, 95% coverage, mypy clean on 41 files, ruff clean. CI pipeline operational.

### References

- [Source: architecture.md#Email-Processing-Extraction] — FR1-4, inbound pipeline
- [Source: architecture.md#Complete-Project-Directory-Structure] — email_request.py, email adapter, services
- [Source: architecture.md#Retry-Pattern-for-Adapters] — exponential backoff, circuit breaker
- [Source: architecture.md#Data-Architecture] — PostgreSQL, SQLAlchemy, Alembic
- [Source: architecture.md#Naming-Patterns] — snake_case tables, columns
- [Source: architecture.md#Error-Format] — structured errors
- [Source: architecture.md#AgentState] — raw_email field in agent state
- [Source: epics.md#Story-2.1] — acceptance criteria, user story
- [Source: epic-1-retro-2026-03-18.md] — established patterns, lessons learned, Epic 2 prep
- [Source: src/quote_agent/adapters/email/] — existing adapter code to extend
- [Source: src/quote_agent/models/base.py] — Base, TimestampMixin, async session

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Fixed `from __future__ import annotations` conflict with SQLAlchemy `Mapped[datetime]` — moved `datetime` import to runtime in `base.py`
- Fixed Pydantic `IncomingEmail` requiring runtime `datetime` import (cannot be under TYPE_CHECKING)
- Fixed mypy errors: used `isinstance(payload, bytes)` type narrowing for `get_payload(decode=True)` return type

### Completion Notes List

- ✅ Task 1: Created `EmailRequest` model with UUID PK, unique `message_id`, JSON recipients, status index. Alembic migration generated and tested (up/down).
- ✅ Task 2: Created `IncomingEmail` Pydantic DTO with all specified fields. Exported from package `__init__.py`.
- ✅ Task 3: Extended `EmailAdapter` protocol with `fetch_new_emails()`. Implemented in `IMAPAdapter` using `imaplib.IMAP4_SSL` + `asyncio.to_thread()`. Handles UNSEEN search, RFC822 fetch, email parsing (Message-ID, Subject, From, To/Cc, Date, body with text/plain preference and HTML fallback), marks as SEEN. Raises `EmailConnectionError` on failures.
- ✅ Task 4: Created `EmailPollerService` with async polling loop, exponential backoff (1s→2s→4s), circuit breaker (5 failures → 60s pause), deduplication by `message_id` (query + IntegrityError fallback), structured logging.
- ✅ Task 5: Integrated poller into FastAPI lifespan — starts as background task on startup, graceful shutdown with task cancellation on app shutdown. Poller state exposed via `app.state.email_poller`.
- ✅ Task 6: Added 20 new unit tests (88 total, 0 regressions). Tests cover EmailRequest model, IncomingEmail DTO, fetch_new_emails (success, empty, connection error, auth error), EmailPollerService (persist, dedup, backoff, circuit breaker, reset, shutdown, properties).

### Change Log

- 2026-03-18: Story 2.1 implementation complete — IMAP email reception pipeline with polling, backoff, circuit breaker, and persistence
- 2026-03-18: Code review fixes — H1: savepoints in _persist_emails to prevent rollback data loss; M1: folder passed as constructor param instead of accessing adapter internals; M2: separated SEEN marking from fetch (mark after persistence to prevent email loss on crash); M3: added broad exception handling in run() for non-IMAP errors; M4: rewrote poller tests to exercise actual run() method; L1: removed unused _MAX_RETRIES constant; added mark_emails_seen + test for unexpected error resilience (91 tests, 0 regressions)

### File List

New files:
- `src/quote_agent/models/email_request.py`
- `src/quote_agent/services/email_poller.py`
- `alembic/versions/70880be8dd5d_add_email_requests_table.py`
- `tests/unit/test_email_request_model.py`
- `tests/unit/test_email_poller.py`

Modified files:
- `src/quote_agent/models/base.py` — moved datetime import to runtime for SQLAlchemy Mapped compatibility
- `src/quote_agent/models/__init__.py` — registered EmailRequest for Alembic
- `src/quote_agent/adapters/email/protocol.py` — added fetch_new_emails() to protocol
- `src/quote_agent/adapters/email/imap.py` — implemented fetch_new_emails() with email parsing
- `src/quote_agent/adapters/email/models.py` — added IncomingEmail DTO
- `src/quote_agent/adapters/email/__init__.py` — added IncomingEmail export
- `src/quote_agent/main.py` — integrated poller into lifespan (startup/shutdown)
- `alembic/env.py` — added EmailRequest import for autogenerate
- `tests/unit/test_email_adapter.py` — added fetch_new_emails and IncomingEmail tests
