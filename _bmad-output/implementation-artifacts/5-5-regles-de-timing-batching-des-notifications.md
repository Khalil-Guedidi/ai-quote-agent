# Story 5.5: Règles de Timing & Batching des Notifications

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want notifications to be intelligently timed and batched,
So that I'm not overwhelmed by a flood of individual notifications during busy periods.

## Acceptance Criteria

1. **Given** more than 5 quotes are processed within 10 minutes, **When** notifications would normally be sent individually, **Then** they are batched into a single summary notification instead (UX-DR32).

2. **Given** any notification scenario, **When** timing rules are applied, **Then** no more than 1 notification per minute is sent to the same user (UX-DR32) **And** individual quote notifications are immediate, batch summaries are scheduled, system status is per-state-change (UX-DR31).

3. **Given** the agent has nothing to process, **When** no quotes are in the queue, **Then** no notification is sent (silence — UX-DR22).

4. **Given** a configurable batch summary schedule (default 08:00 daily), **When** the scheduled time is reached, **Then** a daily batch summary is sent automatically without manual CLI trigger.

5. **Given** a configurable weekly report schedule (default Monday 08:00), **When** the scheduled time is reached, **Then** a weekly manager report is sent automatically without manual CLI trigger.

## Tasks / Subtasks

- [x] Task 1: Implement notification rate limiter (AC: #2)
  - [x]1.1 Create `src/quote_agent/services/notification_throttle.py` with `NotificationThrottle` class
  - [x]1.2 Track last notification timestamp per recipient using an in-memory dict (`dict[str, float]` with `time.monotonic()`)
  - [x]1.3 Implement `can_send(recipient: str) -> bool` — returns `False` if last send was < 60 seconds ago
  - [x]1.4 Implement `record_send(recipient: str) -> None` — updates the timestamp for a recipient
  - [x]1.5 Implement `time_until_allowed(recipient: str) -> float` — returns seconds remaining until next allowed send (0.0 if allowed now)

- [x] Task 2: Implement notification batcher for burst detection (AC: #1)
  - [x]2.1 Add `NotificationBatchSettings` to `config.py`: `burst_threshold: int = 5`, `burst_window_seconds: int = 600` (10 min), `rate_limit_seconds: int = 60`
  - [x]2.2 Create `NotificationBatcher` class in `notification_throttle.py` (same file, cohesive concerns)
  - [x]2.3 Track incoming quote notification events per recipient using a deque of timestamps (`dict[str, deque[float]]`)
  - [x]2.4 Implement `should_batch(recipient: str) -> bool` — returns `True` if recipient has > `burst_threshold` events within `burst_window_seconds`
  - [x]2.5 Implement `record_event(recipient: str) -> None` — adds current timestamp to the recipient's deque, prunes entries older than `burst_window_seconds`
  - [x]2.6 Implement `get_pending_count(recipient: str) -> int` — returns count of events in current burst window
  - [x]2.7 Implement `flush(recipient: str) -> int` — clears the recipient's event deque and returns the count that was flushed

- [x] Task 3: Integrate throttle + batcher into the pipeline notification path (AC: #1, #2)
  - [x]3.1 Create `src/quote_agent/services/notification_dispatcher.py` as the single entry point for all pipeline notifications
  - [x]3.2 Implement `dispatch_quote_notification(state: AgentState, adapter: TeamsAdapter, erp_settings: ERPSettings, throttle: NotificationThrottle, batcher: NotificationBatcher) -> dict[str, object]`
  - [x]3.3 Flow: `record_event()` → check `should_batch()` → if batching, defer (return without sending individual card) → if not batching, check `can_send()` → if rate-limited, defer → else `send_notification()` + `record_send()`
  - [x]3.4 When batching is active and burst window expires (or on next scheduled batch summary), the batched notifications are included in the next batch summary card
  - [x]3.5 Wire `dispatch_quote_notification()` into the existing notifier nodes (`notify_quote_ready`, `notify_multi_proposal`, `notify_escalation`) — replace direct `adapter.send_notification()` calls with dispatcher
  - [x]3.6 Pass throttle + batcher as singleton instances (module-level, same lifecycle as adapter singletons)

- [x] Task 4: Implement asyncio scheduler for automated daily/weekly sends (AC: #4, #5)
  - [x]4.1 Create `src/quote_agent/services/notification_scheduler.py` with `NotificationScheduler` class
  - [x]4.2 Use `asyncio.create_task()` + `asyncio.sleep()` loop pattern (no external dependency like APScheduler)
  - [x]4.3 Implement `start()` — calculates time until next batch summary and weekly report, spawns background tasks
  - [x]4.4 Implement `stop()` — cancels background tasks gracefully
  - [x]4.5 Implement `_run_daily_loop()` — sleeps until configured hour:minute, calls `send_batch_summary()`, repeats daily
  - [x]4.6 Implement `_run_weekly_loop()` — sleeps until configured day+hour:minute, calls `send_weekly_report()`, repeats weekly
  - [x]4.7 Use `NotificationScheduleSettings` from config (already exists: `batch_summary_hour`, `batch_summary_minute`, `weekly_report_day`, `weekly_report_hour`, `weekly_report_minute`)
  - [x]4.8 Add `_seconds_until(hour, minute, day=None) -> float` helper to calculate sleep duration
  - [x]4.9 Fire-and-forget: wrap each scheduled send in try/except, log errors, never crash the loop

- [x] Task 5: Wire scheduler into application lifecycle (AC: #4, #5)
  - [x]5.1 Add `scheduler_enabled: bool = True` to `NotificationScheduleSettings` (can disable for tests/dev)
  - [x]5.2 Start scheduler in FastAPI `lifespan` context manager (start on startup, stop on shutdown)
  - [x]5.3 If `scheduler_enabled` is `False` or `notification.teams_webhook_url` is empty, skip scheduler startup (log info message)
  - [x]5.4 Add `scheduler-status` CLI command to check if scheduler would run and when next sends are due

- [x] Task 6: Unit tests (AC: #1, #2, #3, #4, #5)
  - [x]6.1 Test `NotificationThrottle`: `can_send()` returns True initially, False after send within 60s, True after 60s elapsed
  - [x]6.2 Test `NotificationThrottle`: `time_until_allowed()` returns correct remaining seconds
  - [x]6.3 Test `NotificationBatcher`: `should_batch()` returns False for <= 5 events, True for > 5 within window
  - [x]6.4 Test `NotificationBatcher`: events older than window are pruned on `record_event()`
  - [x]6.5 Test `NotificationBatcher`: `flush()` clears deque and returns correct count
  - [x]6.6 Test `dispatch_quote_notification()`: normal flow sends immediately
  - [x]6.7 Test `dispatch_quote_notification()`: rate-limited flow defers notification
  - [x]6.8 Test `dispatch_quote_notification()`: burst flow (>5 in 10 min) switches to batching
  - [x]6.9 Test `NotificationScheduler._seconds_until()`: correct calculation for same-day future, next-day, specific weekday
  - [x]6.10 Test `NotificationScheduler`: start/stop lifecycle (tasks created and cancelled)
  - [x]6.11 Test scheduler skip when `scheduler_enabled=False` or empty webhook URL
  - [x]6.12 Test silence principle: no notification when nothing to process
  - [x]6.13 Test config: `NotificationBatchSettings` loads from env vars with `__` delimiter

## Dev Notes

### Architecture: In-Memory Throttle + Batcher (No Database)

The rate limiter and batcher use **in-memory data structures** (dicts + deques), NOT database tables. Rationale:
- Single-tenant MVP with one app instance — no cross-instance coordination needed
- Notification throttling is ephemeral state — if the app restarts, the 60-second and 10-minute windows reset, which is acceptable behavior
- No additional DB migration, no table overhead for what is fundamentally a transient concern
- Architecture doc specifies "PostgreSQL job table + asyncio" for task processing, but notification throttling is NOT a job — it's a rate gate

If horizontal scaling is needed later (multiple instances), this can be migrated to a Redis-backed or PostgreSQL-backed solution.

### Key Design Decisions

**Dispatcher as coordination layer**: The `NotificationDispatcher` sits between the LangGraph notifier nodes and the `TeamsAdapter`. Nodes continue to determine WHICH notification to send (quote-ready, multi-proposal, escalation), but the dispatcher controls WHEN and WHETHER to send it.

**No new card types needed**: When batching kicks in, the deferred individual notifications are absorbed into the next daily batch summary (already implemented in Story 5.4). No new "burst-batch" card type — reuse `batch-summary`.

**Scheduler pattern**: Pure asyncio (`sleep` + loop) instead of APScheduler/Celery. This matches the architecture decision of "PostgreSQL job table + asyncio" — minimize external dependencies. The scheduler is a lightweight background task, not a full job queue.

**Singleton throttle/batcher**: Module-level instances via factory functions with `@lru_cache(maxsize=1)`, matching the adapter pattern. This ensures all notification paths share the same rate state.

### Existing Code to Reuse (DO NOT reinvent)

| What | Where | Why |
|------|-------|-----|
| `notify_quote_ready()`, `notify_multi_proposal()`, `notify_escalation()` | `agent/nodes/notifier.py` | Wire dispatcher INTO these — don't restructure them |
| `TeamsAdapter.send_notification()` | `adapters/notification/teams.py` | Reuse as-is — dispatcher calls this after throttle/batch checks |
| `send_batch_summary()` | `services/scheduled_notifications.py` | Scheduler calls this at configured time |
| `send_weekly_report()` | `services/scheduled_notifications.py` | Scheduler calls this at configured time |
| `NotificationScheduleSettings` | `config.py` | Already has `batch_summary_hour`, `batch_summary_minute`, `weekly_report_day/hour/minute` |
| `NotificationPayload` + `NotificationResult` DTOs | `adapters/notification/models.py` | Reuse as-is |
| `get_notification_adapter()` factory | `adapters/notification/__init__.py` | Get cached adapter singleton |
| `_get_session_factory()` | `models/base.py` | Get DB session for scheduled queries |
| `get_settings()` | `config.py` | Access all config |
| Fire-and-forget pattern | `notifier.py`, `scheduled_notifications.py` | Copy exact `try/except/logger.warning` pattern |
| CLI registration pattern | `cli/main.py` | Register `scheduler-status` command same way |
| Click/Typer command pattern | `cli/batch_notify.py` | Follow same pattern for new CLI command |

### Integration Points

**Notifier nodes** (`agent/nodes/notifier.py`):
- Currently call `adapter.send_notification(payload)` directly
- After this story: call `dispatcher.dispatch_quote_notification(...)` which checks throttle/batch before calling `adapter.send_notification()`
- The dispatcher returns the same `dict[str, object]` state update that nodes return today — transparent to the LangGraph graph

**FastAPI lifespan** (`main.py`):
- Add scheduler start/stop to the existing `lifespan` async context manager
- Scheduler startup is conditional: only if `scheduler_enabled=True` AND `teams_webhook_url != ""`

**Configuration** (`config.py`):
- Add `NotificationBatchSettings` nested model to `Settings`
- Add `scheduler_enabled: bool = True` to `NotificationScheduleSettings`
- Env vars: `NOTIFICATION_BATCH__BURST_THRESHOLD=5`, `NOTIFICATION_BATCH__BURST_WINDOW_SECONDS=600`, `NOTIFICATION_BATCH__RATE_LIMIT_SECONDS=60`, `NOTIFICATION_SCHEDULE__SCHEDULER_ENABLED=true`

### Scheduler Implementation Detail

```python
async def _seconds_until(hour: int, minute: int, *, target_weekday: int | None = None) -> float:
    """Calculate seconds from now until the next occurrence of hour:minute (and optionally weekday).

    Uses UTC. If the target time has already passed today, returns seconds until tomorrow (or next week).
    target_weekday: 0=Monday, 6=Sunday (same as datetime.weekday())
    """
```

```python
async def _run_daily_loop(self) -> None:
    """Run the daily batch summary on schedule, forever."""
    while True:
        wait = _seconds_until(self._settings.batch_summary_hour, self._settings.batch_summary_minute)
        await asyncio.sleep(wait)
        try:
            async with self._session_factory() as session:
                await send_batch_summary(session, self._adapter, self._erp_settings)
        except Exception:
            logger.warning("Scheduled batch summary failed", exc_info=True)
```

### Rate Limiting Implementation Detail

The throttle tracks per-recipient sends using `time.monotonic()` for clock-immune timing:

```python
class NotificationThrottle:
    def __init__(self, rate_limit_seconds: float = 60.0) -> None:
        self._rate_limit = rate_limit_seconds
        self._last_send: dict[str, float] = {}

    def can_send(self, recipient: str) -> bool:
        last = self._last_send.get(recipient)
        if last is None:
            return True
        return (time.monotonic() - last) >= self._rate_limit
```

**Recipient identification**: For the MVP (single Teams webhook), the "recipient" is the webhook URL hostname (already exposed as `TeamsAdapter.hostname` property from Story 5.4). In a future multi-channel setup, this becomes channel+user_id.

### Burst Detection Implementation Detail

```python
class NotificationBatcher:
    def __init__(self, burst_threshold: int = 5, burst_window_seconds: float = 600.0) -> None:
        self._threshold = burst_threshold
        self._window = burst_window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def should_batch(self, recipient: str) -> bool:
        self._prune(recipient)
        return len(self._events[recipient]) > self._threshold

    def _prune(self, recipient: str) -> None:
        cutoff = time.monotonic() - self._window
        events = self._events[recipient]
        while events and events[0] < cutoff:
            events.popleft()
```

### Testing Standards

- **Quality gates**: `ruff check` + `mypy --strict` must pass.
- **Test count baseline**: 698 tests (after Story 5.4). Expect ~25-35 new tests.
- **Async tests**: Use `@pytest.mark.asyncio` + `AsyncMock` for async functions.
- **AC-N comments**: Tag each test with the acceptance criterion it verifies.
- **Time mocking**: Use `unittest.mock.patch("time.monotonic")` for deterministic throttle/batcher tests. Do NOT use `asyncio.sleep()` in tests — mock it.
- **Scheduler tests**: Test `_seconds_until()` with mocked `datetime.now(UTC)`. Test start/stop lifecycle with mocked asyncio tasks.
- **No E2E needed**: Throttling and scheduling are service-layer concerns; unit tests with mocked adapters are sufficient.

### Tone Rules (UX-DR22) — Applies to Any New Messages

- Tutoiement (informal "tu")
- Short sentences, no corporate speak
- "Nothing to process → No notification" (silence principle)
- Percentages as integers: "87%" not "87.3%"

### Previous Story Learnings (Story 5.4)

- **Fire-and-forget mandatory**: All notification sends must catch exceptions, log warnings, and never propagate errors. Copy the exact `try/except/logger.warning` pattern.
- **Card dispatch pattern**: Add `elif` branches in `_build_adaptive_card()` — the `else` falls through to `_build_generic_card()`. Never rearrange existing branches.
- **Config pattern**: Follow existing `pydantic-settings` nested model pattern. Use `__` delimiter for env vars.
- **Scheduling deferred from 5.4**: Story 5.4 explicitly stated "scheduling is NOT automated. The CLI commands trigger reports manually. Automated scheduling is deferred to Story 5.5." — this is that story.
- **Test baseline**: 698 tests passing after Story 5.4.

### Git Intelligence (Recent Commits)

Last 5 commits are all Epic 5 Stories (5.0a through 5.4). Pattern: each story adds new service files + extends `teams.py` card builders + CLI commands + unit tests. The codebase is stable and all 698 tests pass.

### Project Structure Notes

**New files:**
- `src/quote_agent/services/notification_throttle.py` — `NotificationThrottle` + `NotificationBatcher` classes
- `src/quote_agent/services/notification_dispatcher.py` — `dispatch_quote_notification()` coordination layer
- `src/quote_agent/services/notification_scheduler.py` — `NotificationScheduler` with asyncio background tasks
- `tests/unit/test_notification_throttle.py` — throttle + batcher tests
- `tests/unit/test_notification_dispatcher.py` — dispatcher integration tests
- `tests/unit/test_notification_scheduler.py` — scheduler lifecycle + timing tests

**Modified files:**
- `src/quote_agent/config.py` — add `NotificationBatchSettings`, add `scheduler_enabled` to `NotificationScheduleSettings`
- `src/quote_agent/agent/nodes/notifier.py` — wire dispatcher into notification nodes
- `src/quote_agent/main.py` — add scheduler to FastAPI lifespan
- `src/quote_agent/cli/main.py` — register `scheduler-status` command
- `tests/unit/test_notification_adapter.py` — may need adjustments if notifier nodes change

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.5]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — UX-DR22, UX-DR31, UX-DR32 (timing rules, batching, silence)]
- [Source: _bmad-output/planning-artifacts/prd.md — FR33-FR36 (notification requirements)]
- [Source: _bmad-output/planning-artifacts/architecture.md — notification adapter pattern, asyncio task processing, graceful degradation]
- [Source: src/quote_agent/adapters/notification/teams.py — existing card builders, send_notification()]
- [Source: src/quote_agent/agent/nodes/notifier.py — pipeline notification nodes to integrate dispatcher with]
- [Source: src/quote_agent/services/scheduled_notifications.py — send_batch_summary(), send_weekly_report() for scheduler to call]
- [Source: src/quote_agent/services/notification_stats.py — query functions used by scheduled sends]
- [Source: src/quote_agent/config.py — NotificationScheduleSettings already has batch_summary_hour/minute, weekly_report_day/hour/minute]
- [Source: docs/project-context.md — adapter pattern, async wrapping, config conventions, test naming]
- [Source: _bmad-output/implementation-artifacts/5-4-resume-batch-matinal-rapport-hebdomadaire-manager.md — previous story learnings, file list, scheduling deferral note]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- Task 1: Implemented `NotificationThrottle` class with `can_send()`, `record_send()`, `time_until_allowed()` — per-recipient rate limiting using `time.monotonic()` for clock-immune timing.
- Task 2: Implemented `NotificationBatcher` class with `record_event()`, `should_batch()`, `get_pending_count()`, `flush()` — burst detection with configurable threshold and window. Added `NotificationBatchSettings` to config.
- Task 3: Created `dispatch_quote_notification()` dispatcher as coordination layer. Wired into all 3 notifier nodes (`notify_quote_ready`, `notify_multi_proposal`, `notify_escalation`) with backward-compatible optional throttle/batcher params. Module-level singleton instances created in `build_agent_graph()`.
- Task 4: Implemented `NotificationScheduler` with pure asyncio background loops. `_seconds_until()` helper calculates next occurrence with UTC and weekday support. Fire-and-forget error handling in loops.
- Task 5: Wired scheduler into FastAPI `lifespan` (conditional start on `scheduler_enabled=True` + webhook configured). Added `scheduler-status` CLI command. Added `scheduler_enabled` to `NotificationScheduleSettings`.
- Task 6: 36 new unit tests covering throttle (7), batcher (8+2 config), dispatcher (7), scheduler timing (5), scheduler lifecycle (4), scheduler skip (3). All 734 tests pass (698 baseline + 36 new).

### Change Log

- 2026-03-22: Story 5.5 implementation — notification throttle, batcher, dispatcher, scheduler, CLI command, 36 tests
- 2026-03-22: Code review fixes — renamed `_seconds_until` → `seconds_until` (public API), DRY scheduler startup via `should_run()`, removed defensive `getattr`

### File List

**New files:**
- `src/quote_agent/services/notification_throttle.py`
- `src/quote_agent/services/notification_dispatcher.py`
- `src/quote_agent/services/notification_scheduler.py`
- `src/quote_agent/cli/scheduler_status.py`
- `tests/unit/test_notification_throttle.py`
- `tests/unit/test_notification_dispatcher.py`
- `tests/unit/test_notification_scheduler.py`

**Modified files:**
- `src/quote_agent/config.py` — added `NotificationBatchSettings`, added `scheduler_enabled` to `NotificationScheduleSettings`
- `src/quote_agent/agent/nodes/notifier.py` — added optional throttle/batcher params, wired dispatcher
- `src/quote_agent/agent/graph.py` — instantiate throttle/batcher singletons, pass to notify nodes
- `src/quote_agent/main.py` — added scheduler start/stop to FastAPI lifespan
- `src/quote_agent/cli/main.py` — registered `scheduler-status` command
- `tests/unit/test_agent_graph.py` — added `_make_settings_mock()` helper for proper mock settings
