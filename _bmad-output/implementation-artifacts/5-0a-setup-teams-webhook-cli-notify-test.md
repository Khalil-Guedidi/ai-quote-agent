# Story 5.0a: Setup Teams Webhook + CLI `notify-test`

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **project lead (Khalil)**,
I want a CLI command `notify-test` that sends a test Teams Adaptive Card via the configured webhook,
So that I can manually verify the notification channel works before building Epic 5's notification features.

## Acceptance Criteria

1. **AC-1: `send_notification()` method on TeamsAdapter**
   Given the TeamsAdapter already exists with `health_check()` only
   When `send_notification(payload: NotificationPayload)` is called
   Then it POSTs a Teams Adaptive Card JSON to the configured webhook URL via httpx
   And returns a `NotificationResult` with delivery status, HTTP status code, and timestamp
   And wraps httpx errors into `NotificationError` (already defined in `exceptions.py`)

2. **AC-2: NotificationPayload and NotificationResult DTOs**
   Given the notification models file has placeholder comments for Epic 5
   When the DTOs are created in `adapters/notification/models.py`
   Then `NotificationPayload` contains: `title: str`, `message: str`, `card_type: str` (default "test"), `data: dict[str, Any]` (default empty)
   And `NotificationResult` contains: `success: bool`, `status_code: int | None`, `error: str | None`, `timestamp: datetime`

3. **AC-3: NotificationAdapter Protocol updated**
   Given the Protocol currently only defines `health_check()`
   When `send_notification` is added
   Then `async def send_notification(self, payload: NotificationPayload) -> NotificationResult: ...` is added to the Protocol
   And the Protocol import in `__init__.py` re-exports `NotificationPayload` and `NotificationResult`

4. **AC-4: Teams Adaptive Card formatting**
   Given a `NotificationPayload` is provided
   When `TeamsAdapter.send_notification()` builds the card JSON
   Then it produces a valid Adaptive Card schema with: type="AdaptiveCard", version="1.4", body with TextBlock elements
   And uses the structural consistency pattern: accent color container (top bar) + bot name "Q" + timestamp + message body
   And the test card uses brand accent color (not confidence-tier specific)

5. **AC-5: CLI `notify-test` command**
   Given the CLI entry point at `cli/main.py`
   When the user runs `uv run quote-agent notify-test`
   Then it sends a test notification via `TeamsAdapter.send_notification()`
   And displays: delivery status (success/failure), HTTP status code, webhook hostname (never full URL)
   And supports `--message` option to customize the test message (default: "Test notification from AI Quote Agent")
   And supports `--json` flag for JSON output (same pattern as other CLI commands)

6. **AC-6: Unit tests**
   Given all new code
   When tests are run
   Then `send_notification()` has tests for: successful delivery, connection error, timeout, invalid payload
   And CLI `notify-test` has tests for: success output, failure output, JSON output, custom message
   And the updated Protocol is verified (TeamsAdapter still satisfies `NotificationAdapter`)
   And code passes `ruff check` and `mypy --strict`

7. **AC-7: CI green**
   Given all changes
   When the CI pipeline runs
   Then all existing tests still pass (0 regressions)
   And new tests pass
   And `ruff check` and `mypy --strict` pass

## Tasks / Subtasks

- [x] Task 1: Add `NotificationPayload` and `NotificationResult` DTOs (AC: #2)
  - [x] 1.1 Add `NotificationPayload(BaseModel)` to `adapters/notification/models.py`
  - [x] 1.2 Add `NotificationResult(BaseModel)` to `adapters/notification/models.py`
  - [x] 1.3 Update `__init__.py` to re-export both DTOs

- [x] Task 2: Update `NotificationAdapter` Protocol (AC: #3)
  - [x] 2.1 Add `send_notification` method signature to `protocol.py`
  - [x] 2.2 Add `NotificationPayload`/`NotificationResult` imports (use TYPE_CHECKING)

- [x] Task 3: Implement `send_notification()` on TeamsAdapter (AC: #1, #4)
  - [x] 3.1 Add `_build_adaptive_card(payload: NotificationPayload) -> dict[str, Any]` private method
  - [x] 3.2 Build Adaptive Card JSON: type="AdaptiveCard", `$schema`, version="1.4", body with TextBlock elements
  - [x] 3.3 Card structure: colored container (accent bar) → "Q" bot name TextBlock → timestamp → message TextBlock
  - [x] 3.4 Implement `send_notification()`: POST card JSON to webhook, return `NotificationResult`
  - [x] 3.5 Error handling: catch httpx exceptions → `NotificationResult(success=False, error=str(exc))`
  - [x] 3.6 Timeout: reuse `_HEALTH_CHECK_TIMEOUT` (5s) or define a `_SEND_TIMEOUT`

- [x] Task 4: Create CLI `notify-test` command (AC: #5)
  - [x] 4.1 Create `cli/notify_test.py` with implementation function
  - [x] 4.2 Use `asyncio.run()` pattern (same as other 9 CLI commands)
  - [x] 4.3 Display: success/failure, HTTP status, webhook hostname (use `_hostname` from adapter)
  - [x] 4.4 Add `--message` option (default: "Test notification from AI Quote Agent")
  - [x] 4.5 Add `--json` flag for structured JSON output
  - [x] 4.6 Register command in `cli/main.py` using same lazy-import pattern

- [x] Task 5: Unit tests (AC: #6)
  - [x] 5.1 Tests for `send_notification()`: success (mock httpx 200), connection error, timeout
  - [x] 5.2 Tests for `_build_adaptive_card()`: verify Adaptive Card schema structure
  - [x] 5.3 Tests for CLI `notify-test`: success output, failure output, JSON flag, custom message
  - [x] 5.4 Protocol compliance: TeamsAdapter still satisfies NotificationAdapter with new method
  - [x] 5.5 Verify `ruff check` and `mypy --strict` pass

- [x] Task 6: CI verification (AC: #7)
  - [x] 6.1 Run full test suite, verify 0 regressions
  - [x] 6.2 Verify CI pipeline passes

## Dev Notes

### Architecture Compliance

- **Adapter pattern**: TeamsAdapter already follows the 4-file pattern (`protocol.py`, `models.py`, `teams.py`, `__init__.py`). This story extends it — no structural changes.
- **Singleton factory**: `get_notification_adapter()` already uses `@lru_cache(maxsize=1)`. No changes needed.
- **Health endpoint**: Already integrated in `/health`. No changes needed.
- **Exception class**: `NotificationError(AdapterError)` already exists in `exceptions.py`. Use it for send failures that should propagate.

### Existing Code to Extend (NOT Reinvent)

- `adapters/notification/teams.py` — add `send_notification()` and `_build_adaptive_card()` methods to existing `TeamsAdapter` class
- `adapters/notification/models.py` — add DTOs below existing `TeamsWebhookInfo`; replace the "Future DTOs" comments
- `adapters/notification/protocol.py` — add method to existing Protocol; replace the "Future methods" comment
- `adapters/notification/__init__.py` — add re-exports for new DTOs
- `cli/main.py` — register new command using same pattern as `draft_create`, `erp_read`, etc.
- `tests/unit/test_notification_adapter.py` — add new test cases to existing test file

### CLI Pattern (MUST Follow)

All 10 existing CLI commands use the same pattern:
1. Implementation in `cli/{command_name}.py` (the actual logic)
2. Registration in `cli/main.py` via `@app.command()` with lazy import of implementation
3. `asyncio.run()` to call async code from sync Typer command
4. `--json` flag on every command
5. `typer.echo()` for output, `typer.style()` for colors, `typer.Exit(code=1)` for errors

### Teams Adaptive Card Schema

Use Adaptive Card schema version 1.4. The card JSON structure for a test notification:

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.4",
  "body": [
    {
      "type": "Container",
      "style": "accent",
      "items": [{"type": "TextBlock", "text": "Q — AI Quote Agent", "weight": "Bolder", "color": "Light"}]
    },
    {"type": "TextBlock", "text": "{{timestamp}}", "size": "Small", "isSubtle": true},
    {"type": "TextBlock", "text": "{{message}}", "wrap": true}
  ]
}
```

Teams incoming webhooks expect the card wrapped in an `attachments` array:
```json
{
  "type": "message",
  "attachments": [
    {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": { ... adaptive card ... }
    }
  ]
}
```

### Httpx Usage

TeamsAdapter already uses `httpx.AsyncClient` for health checks. Reuse same pattern:
```python
async with httpx.AsyncClient() as client:
    response = await client.post(self._webhook_url, json=payload, timeout=timeout)
```

The `health_check()` currently sends `json={}` (empty body). `send_notification()` sends the full card payload.

### Security: Never Expose Webhook URL

The adapter already stores `self._hostname` (parsed from URL). Use this in CLI output and logs. Never print the full webhook URL — it's a secret.

### What NOT to Do

- Do NOT create a new file for card templates yet — inline the card building in `_build_adaptive_card()`. Template files come in Stories 5.1-5.3.
- Do NOT add notification batching, timing, or scheduling — that's Story 5.5.
- Do NOT add multi-channel support — that's Story 5.6.
- Do NOT add `format_card()` to the Protocol yet — that's Story 5.6.
- Do NOT refactor `asyncio.run()` in CLI — that's deferred tech debt.

### Previous Story Intelligence

Story 4.8 (last story in Epic 4) established the LangGraph pipeline with 9 CLI commands. Key patterns:
- Every CLI command follows the exact same structure (lazy import, `asyncio.run()`, `--json` flag)
- Tests mock external dependencies at the httpx/adapter level
- `from __future__ import annotations` in every file
- Absolute imports only

### Project Structure Notes

Files to create:
- `src/quote_agent/cli/notify_test.py` — new CLI command implementation

Files to modify:
- `src/quote_agent/adapters/notification/models.py` — add DTOs
- `src/quote_agent/adapters/notification/protocol.py` — add send method
- `src/quote_agent/adapters/notification/teams.py` — add send implementation + card builder
- `src/quote_agent/adapters/notification/__init__.py` — add re-exports
- `src/quote_agent/cli/main.py` — register notify-test command
- `tests/unit/test_notification_adapter.py` — add new tests

### References

- [Source: _bmad-output/planning-artifacts/architecture.md — adapters/notification/ structure, lines 559-564]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Teams Adaptive Card Templates, lines 1089-1102]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Card structure consistency, lines 1262-1268]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Notification Patterns (Teams), lines 1245-1260]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Agent tone rules, lines 1181-1186]
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-22.md — Foundation story 5.0a definition, lines 118-123]
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-22.md — "Project Lead must see the product", line 159]
- [Source: docs/project-context.md — Adapter pattern, lines 30-68]
- [Source: docs/project-context.md — Quality gates (mypy strict, ruff, pytest), lines 460-506]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Pydantic `datetime` import: required `# noqa: TC003` runtime import (not TYPE_CHECKING) due to `from __future__ import annotations`
- Ruff UP017: migrated `timezone.utc` → `datetime.UTC` across all files
- CLI mock target: `quote_agent.adapters.notification.get_notification_adapter` (not `cli.notify_test.get_notification_adapter` — lazy import inside async function)

### Completion Notes List

- Added `NotificationPayload` and `NotificationResult` Pydantic DTOs to `models.py`
- Extended `NotificationAdapter` Protocol with `send_notification()` method
- Implemented `TeamsAdapter.send_notification()` with Adaptive Card v1.4 JSON builder
- Card structure: accent container (brand bar) → "Q" bot name → UTC timestamp → message body
- Error handling wraps httpx exceptions into `NotificationResult(success=False, error=...)`
- Created `cli/notify_test.py` with `--message` and `--json` flags following existing CLI pattern
- Registered `notify-test` command in `cli/main.py` (11th CLI command)
- Added 10 new tests (18 total in file): send_notification success/error/timeout, card schema/body structure, protocol compliance, CLI success/failure/json/custom-message
- Full suite: 609 passed, 0 failures, 0 regressions
- `ruff check` and `mypy --strict` pass clean

### File List

- `src/quote_agent/adapters/notification/models.py` — modified (added NotificationPayload, NotificationResult DTOs)
- `src/quote_agent/adapters/notification/protocol.py` — modified (added send_notification to Protocol)
- `src/quote_agent/adapters/notification/teams.py` — modified (added _build_adaptive_card, send_notification, _SEND_TIMEOUT)
- `src/quote_agent/adapters/notification/__init__.py` — modified (added re-exports for new DTOs)
- `src/quote_agent/cli/notify_test.py` — new (CLI notify-test command implementation)
- `src/quote_agent/cli/main.py` — modified (registered notify-test command)
- `tests/unit/test_notification_adapter.py` — modified (added 10 new tests)

### Change Log

- 2026-03-22: Story 5.0a implemented — Teams webhook send_notification + CLI notify-test command with 10 new unit tests
