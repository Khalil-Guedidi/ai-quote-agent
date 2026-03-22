# Story 5.6: Adapter Pattern Multi-Canal & Consistance

Status: done

## Story

As an **IT operator (Laurent)**,
I want the notification system to use an adapter pattern supporting multiple channels,
So that new channels (Slack, email, webhook) can be added without modifying the core notification logic.

## Acceptance Criteria

1. **Given** the notification adapter Protocol is defined
   **When** the Teams adapter sends a notification
   **Then** it follows the Protocol interface (`send_notification`, `health_check`)
   **And** all cards follow the structural consistency rules: accent bar + bot avatar "Q" + casual French tone + structured data + action buttons (UX-DR21)

2. **Given** the notification system is configured for Teams
   **When** a new channel (e.g., Slack) needs to be added later
   **Then** only a new adapter implementation is required — no changes to core logic (FR36)

3. **Given** the agent's tone is consistent across all notifications
   **When** any card is generated
   **Then** it uses tutoiement, short sentences, admits uncertainty when relevant, never uses corporate speak (UX-DR22)

## Tasks / Subtasks

- [x] Task 1: Refactor `get_notification_adapter()` factory to support multi-channel routing (AC: #2)
  - [x] 1.1 Add `channel` field to `NotificationSettings` config (already exists as `channel: str = "teams"`)
  - [x] 1.2 Update `get_notification_adapter()` in `__init__.py` to route by `settings.notification.channel` value
  - [x] 1.3 Return type must be `NotificationAdapter` (Protocol), not concrete `TeamsAdapter`
  - [x] 1.4 Raise `ConfigurationError` for unknown channel values
  - [x] 1.5 Keep `@lru_cache` singleton behavior

- [x] Task 2: Add a `LogAdapter` as second adapter implementation — proving extensibility (AC: #2)
  - [x] 2.1 Create `src/quote_agent/adapters/notification/log.py`
  - [x] 2.2 Implement `LogAdapter` class satisfying `NotificationAdapter` Protocol
  - [x] 2.3 `send_notification()` logs the payload via structured logger (level INFO, component `notification.log`)
  - [x] 2.4 `health_check()` always returns `ServiceHealth(status="healthy")`
  - [x] 2.5 Returns `NotificationResult(success=True, status_code=200, timestamp=...)`
  - [x] 2.6 Useful for dev/test environments where Teams webhook is unavailable

- [x] Task 3: Validate structural consistency across all card types (AC: #1, #3)
  - [x] 3.1 Write unit tests asserting every card type built by `TeamsAdapter` contains: accent bar container as first body element, "Q — AI Quote Agent" TextBlock, UTC timestamp TextBlock
  - [x] 3.2 Write unit tests asserting all card types that have actions include an "Action.OpenUrl" with French label
  - [x] 3.3 Verify tone compliance in existing card message templates (tutoiement, no corporate speak)

- [x] Task 4: Ensure all consumers use Protocol type, not concrete class (AC: #2)
  - [x] 4.1 Update `api/health.py` — type annotation should reference `NotificationAdapter` Protocol
  - [x] 4.2 Update `services/notification_dispatcher.py` — if it references `TeamsAdapter` directly, change to Protocol
  - [x] 4.3 Update `agent/graph.py` — notification node instantiation should work with any adapter
  - [x] 4.4 Update `cli/batch_notify.py` — use `get_notification_adapter()` return typed as Protocol
  - [x] 4.5 Verify no `isinstance(adapter, TeamsAdapter)` checks exist in core logic

- [x] Task 5: Add `format_card` to Protocol and implement (AC: #1)
  - [x] 5.1 Evaluate whether `format_card` belongs in the Protocol — the epic AC mentions it, but `_build_adaptive_card` is Teams-specific (Adaptive Cards don't exist in Slack/email)
  - [x] 5.2 Decision: Do NOT add `format_card` to Protocol. Card formatting is channel-specific. The Protocol contract is `send_notification(payload) -> result` — each adapter formats internally. Document this decision in code comment.

- [x] Task 6: Unit tests (AC: #1, #2, #3)
  - [x] 6.1 Test `get_notification_adapter()` returns `TeamsAdapter` when `channel="teams"`
  - [x] 6.2 Test `get_notification_adapter()` returns `LogAdapter` when `channel="log"`
  - [x] 6.3 Test `get_notification_adapter()` raises `ConfigurationError` for `channel="unknown"`
  - [x] 6.4 Test `LogAdapter` satisfies `NotificationAdapter` Protocol (`isinstance` check)
  - [x] 6.5 Test `LogAdapter.send_notification()` returns success result
  - [x] 6.6 Test `LogAdapter.health_check()` returns healthy
  - [x] 6.7 Test structural consistency: parametrized test across all 7 card types asserting common structure
  - [x] 6.8 Test that `dispatch_quote_notification` works with `LogAdapter` (no Teams dependency)

## Dev Notes

### Architecture: Adapter Pattern Completion

This story **completes** the adapter pattern for notifications. The Protocol (`NotificationAdapter`) and Teams implementation (`TeamsAdapter`) already exist and are fully functional from Stories 5.0a–5.5. The work here is:

1. **Make the factory channel-agnostic** — currently `get_notification_adapter()` hardcodes `TeamsAdapter`
2. **Add a second adapter** (`LogAdapter`) to prove the pattern works
3. **Ensure all consumers depend on Protocol, not concrete class**
4. **Validate structural consistency** across all existing card types

### Existing Code to Reuse — DO NOT RECREATE

| Component | Path | Status |
|-----------|------|--------|
| `NotificationAdapter` Protocol | `src/quote_agent/adapters/notification/protocol.py` | EXISTS — 2 methods: `health_check()`, `send_notification()` |
| `TeamsAdapter` | `src/quote_agent/adapters/notification/teams.py` | EXISTS — 585 lines, 7 card builders, fully working |
| `NotificationPayload` DTO | `src/quote_agent/adapters/notification/models.py` | EXISTS — fields: title, message, card_type, data |
| `NotificationResult` DTO | `src/quote_agent/adapters/notification/models.py` | EXISTS — fields: success, status_code, error, timestamp |
| `NotificationSettings` config | `src/quote_agent/config.py` | EXISTS — fields: channel (default "teams"), teams_webhook_url |
| Factory function | `src/quote_agent/adapters/notification/__init__.py` | EXISTS — needs refactoring (currently hardcodes TeamsAdapter) |
| `notification_dispatcher.py` | `src/quote_agent/services/notification_dispatcher.py` | EXISTS — `dispatch_quote_notification()` orchestrates throttle/batch/send |
| Existing tests | `tests/unit/test_notification_adapter.py` | EXISTS — health, config, send, card structure, Protocol compliance |

### Critical: What NOT To Do

- **DO NOT** rewrite `TeamsAdapter` — it is complete and tested
- **DO NOT** add Slack/email/webhook adapters — those are post-MVP (Phase 2 in PRD roadmap). Only add `LogAdapter` as proof of extensibility
- **DO NOT** add `format_card` to the Protocol — card formatting is channel-specific. Adaptive Cards are Teams-only. Each adapter handles its own formatting internally via `send_notification(payload)`
- **DO NOT** modify card templates or tone — all 7 card types are already validated in Stories 5.1–5.4
- **DO NOT** touch throttle/batcher/dispatcher/scheduler — those are done in Story 5.5 and work at a higher level above the adapter

### Key Design Decision: format_card

The epic AC mentions `format_card` as part of the Protocol interface. However, after implementation of Stories 5.1–5.5, it's clear that card formatting is inherently channel-specific:
- Teams uses Adaptive Cards (JSON schema)
- Slack would use Block Kit (different JSON schema)
- Email would use HTML
- Webhook would use plain JSON

The correct abstraction is: `send_notification(payload: NotificationPayload) -> NotificationResult`. Each adapter transforms the universal `NotificationPayload` into its channel-specific format internally. This is already how `TeamsAdapter` works — `_build_adaptive_card()` is a private method.

### Factory Refactoring Pattern

Current (`__init__.py` line 27-33):
```python
@lru_cache(maxsize=1)
def get_notification_adapter() -> TeamsAdapter:  # ← concrete return type
    from quote_agent.adapters.notification.teams import TeamsAdapter
    from quote_agent.config import get_settings
    return TeamsAdapter(get_settings().notification)
```

Target:
```python
@lru_cache(maxsize=1)
def get_notification_adapter() -> NotificationAdapter:  # ← Protocol return type
    from quote_agent.config import get_settings
    settings = get_settings().notification
    if settings.channel == "teams":
        from quote_agent.adapters.notification.teams import TeamsAdapter
        return TeamsAdapter(settings)
    if settings.channel == "log":
        from quote_agent.adapters.notification.log import LogAdapter
        return LogAdapter()
    msg = f"Unknown notification channel: {settings.channel}"
    raise ConfigurationError(msg)
```

### Card Structural Consistency Rules (UX-DR21)

Every Teams Adaptive Card MUST have (verify in tests):
1. First body element: `Container` with accent style (color varies by card type)
2. Inside container: `TextBlock` with `"Q — AI Quote Agent"`, `weight: "Bolder"`, `color: "Light"`
3. Second body element: `TextBlock` with UTC timestamp, `size: "Small"`, `isSubtle: True`
4. Third body element: `TextBlock` with `payload.message`, `wrap: True`
5. Cards with links: `actions` array with `Action.OpenUrl` and French label

Card type → accent style mapping:
| Card Type | Container Style | UX Reference |
|-----------|----------------|--------------|
| quote-ready | `good` (green) | UX-DR15 |
| multi-proposal | `warning` (amber) | UX-DR16 |
| escalation | `attention` (red) | UX-DR17 |
| batch-summary | `accent` (blue) | UX-DR18 |
| manager-weekly | `accent` (blue) | UX-DR19 |
| manager-stats | `accent` (blue) | UX-DR20 |
| generic/test | `accent` (blue) | — |

### Tone Rules (UX-DR22)

- Tutoiement (informal "tu") — agent is a colleague, not a service
- Short sentences, no corporate speak
- Admit uncertainty openly: "je suis pas sûr", "c'est compliqué"
- Never celebrate: no "Great news!" or "Successfully processed!"
- Never apologize excessively: "Ce cas est difficile" not "Désolé"

### Consumer Usage Points to Update

All locations importing or using `get_notification_adapter()`:

| File | Line(s) | Current Usage | Change Needed |
|------|---------|---------------|---------------|
| `api/health.py` | 16, 53 | Import + DI | Type annotation → `NotificationAdapter` |
| `main.py` | 61, 64 | Scheduler startup | Should work via Protocol — verify |
| `cli/notify_test.py` | 17, 19 | CLI test command | Should work via Protocol — verify |
| `cli/batch_notify.py` | 17, 22, 32, 37, 47, 51 | Batch/weekly/stats | Should work via Protocol — verify |
| `agent/graph.py` | 76, 260, 268, 276 | Notifier nodes | Should work via Protocol — verify |

### Testing Standards

- Test file: `tests/unit/test_notification_adapter.py` (extend existing file)
- Or new file: `tests/unit/test_notification_log_adapter.py` for LogAdapter-specific tests
- Naming: `test_{behavior}_when_{condition}()`
- Use `pytest.mark.parametrize` for card structural consistency across all 7 types
- Mock `get_settings()` for factory routing tests — use `unittest.mock.patch`
- No real HTTP calls in unit tests

### Previous Story Learnings (from Stories 5.0a–5.5)

- `ServiceHealth` import: `from quote_agent.api.health import ServiceHealth`
- `ConfigurationError` import: `from quote_agent.exceptions import ConfigurationError`
- Structured logging convention: `logger = logging.getLogger(__name__)`
- `@lru_cache` requires clearing in tests: `get_notification_adapter.cache_clear()`
- `NotificationSettings` only has 2 fields: `channel` (str) and `teams_webhook_url` (str)
- Tests use `httpx` mocking via `respx` or `unittest.mock.patch` on `httpx.AsyncClient`

### Project Structure — Files to Create/Modify

**Create:**
- `src/quote_agent/adapters/notification/log.py` — LogAdapter implementation

**Modify:**
- `src/quote_agent/adapters/notification/__init__.py` — factory routing + return type
- `tests/unit/test_notification_adapter.py` — add structural consistency + factory routing tests

**Verify (no changes expected):**
- `src/quote_agent/adapters/notification/protocol.py` — should remain as-is
- `src/quote_agent/adapters/notification/teams.py` — should remain as-is
- `src/quote_agent/adapters/notification/models.py` — should remain as-is

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.6]
- [Source: _bmad-output/planning-artifacts/architecture.md — Adapter Pattern, Notification section]
- [Source: _bmad-output/planning-artifacts/architecture.md — Naming Patterns, Structure Patterns]
- [Source: _bmad-output/planning-artifacts/prd.md — FR33-FR36]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — UX-DR15 to UX-DR22, UX-DR31/32]
- [Source: src/quote_agent/adapters/notification/ — existing implementation]
- [Source: docs/project-context.md — established patterns from Epics 1-4]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Existing CLI tests used `mock_adapter._hostname` (private attr) — updated to `mock_adapter.hostname` (public property) to align with `getattr(adapter, "hostname", ...)` pattern used in consumer code.
- mypy strict flagged `adapter.hostname` on `NotificationAdapter` Protocol — resolved with `getattr(adapter, "hostname", ...)` pattern in dispatcher, scheduler, batch_notify, and notify_test.

### Completion Notes List

- ✅ Task 1: Factory refactored — routes by `settings.notification.channel`, returns `NotificationAdapter` Protocol type, raises `ConfigurationError` for unknown channels, keeps `@lru_cache` singleton.
- ✅ Task 2: `LogAdapter` created — satisfies Protocol, logs payloads via structured logger, returns success results, provides `hostname` property for throttle/batcher compatibility.
- ✅ Task 3: Structural consistency validated — parametrized tests across all 7 card types asserting accent bar, bot avatar "Q", timestamp, and Action.OpenUrl with French labels.
- ✅ Task 4: All consumers updated to Protocol type — health.py, notification_dispatcher.py, notifier.py, batch_notify.py, notify_test.py, notification_scheduler.py, scheduled_notifications.py. Zero `isinstance(adapter, TeamsAdapter)` checks in core logic. Used `getattr(adapter, "hostname", ...)` for mypy-safe hostname access.
- ✅ Task 5: `format_card` design decision documented in protocol.py docstring — card formatting is channel-specific, not part of Protocol contract.
- ✅ Task 6: 34 new tests added (87 total in file). Factory routing (3), LogAdapter (4), structural consistency parametrized across 7 card types (26), dispatcher with LogAdapter (1). All 768 unit tests pass, 0 regressions.

### Change Log

- 2026-03-22: Story 5.6 implemented — adapter pattern multi-channel routing, LogAdapter, consumer Protocol migration, structural consistency tests

### File List

**Created:**
- `src/quote_agent/adapters/notification/log.py`

**Modified:**
- `src/quote_agent/adapters/notification/__init__.py`
- `src/quote_agent/adapters/notification/protocol.py`
- `src/quote_agent/api/health.py`
- `src/quote_agent/services/notification_dispatcher.py`
- `src/quote_agent/services/notification_scheduler.py`
- `src/quote_agent/services/scheduled_notifications.py`
- `src/quote_agent/agent/nodes/notifier.py`
- `src/quote_agent/cli/batch_notify.py`
- `src/quote_agent/cli/notify_test.py`
- `tests/unit/test_notification_adapter.py`
