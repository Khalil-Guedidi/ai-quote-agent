# Story 5.4: Résumé Batch Matinal & Rapport Hebdomadaire Manager

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales manager (Marc)**,
I want to receive a batch summary each morning and a weekly performance report,
So that I have visibility into the agent's activity without checking the system manually.

## Acceptance Criteria

1. **Given** the agent has processed multiple quotes overnight/morning, **When** the scheduled batch summary time is reached (configurable, default 08:00), **Then** a Teams Adaptive Card uses the `batch-summary` template: brand accent bar, count by confidence tier (X ready, Y need choice, Z need expertise), total processed, ERP queue link (UX-DR18).

2. **Given** it's Monday morning, **When** the weekly report is triggered, **Then** a Teams Adaptive Card uses the `manager-weekly` template: total quotes processed, average confidence, per-rep breakdown table (rep, quotes, accuracy %), weekly trend arrow + percentage (UX-DR19).

3. **Given** Marc sends a bot command requesting stats, **When** the command is processed, **Then** a `manager-stats` card is returned with the requested metrics and available commands (UX-DR20).

## Tasks / Subtasks

- [x] Task 1: Add `NotificationScheduleSettings` config and batch summary query service (AC: #1)
  - [x] 1.1 Add `NotificationScheduleSettings` to `config.py` with `batch_summary_hour: int = 8`, `batch_summary_minute: int = 0`, `weekly_report_day: int = 0` (Monday), `weekly_report_hour: int = 8`, `weekly_report_minute: int = 0`
  - [x] 1.2 Wire `notification_schedule: NotificationScheduleSettings` into `Settings`
  - [x] 1.3 Create `src/quote_agent/services/notification_stats.py` with async functions:
    - `get_daily_summary(session) -> DailySummary` — queries `quote_requests` for today's processed quotes, groups by confidence tier (high/medium/low based on `confidence` column + status)
    - `get_weekly_report(session) -> WeeklyReport` — queries `quote_requests` for last 7 days, computes total processed, average confidence, per-sender breakdown (rep = email sender), weekly trend vs previous week
  - [x] 1.4 Create Pydantic DTOs: `DailySummary(total, high_count, medium_count, low_count, date)`, `WeeklyReport(total, avg_confidence, rep_breakdown: list[RepStats], trend_pct, trend_direction, period_start, period_end)`, `RepStats(rep_name, quotes_count, avg_confidence_pct)`

- [x] Task 2: Build `_build_batch_summary_card()` and `_build_manager_weekly_card()` in `teams.py` (AC: #1, #2)
  - [x] 2.1 Add `_build_batch_summary_card()`: brand accent (`style="accent"`), "Q" bot header, UTC timestamp, casual French message ("Bonjour ! J'ai traité {total} devis. {high} prêts, {medium} besoin de ton choix, {low} besoin de ton expertise"), FactSet with tier counts + total, "Voir la file" OpenUrl action button to ERP queue
  - [x] 2.2 Add `_build_manager_weekly_card()`: brand accent (`style="accent"`), "Q" bot header, UTC timestamp, message ("Voici le récap de la semaine"), FactSet with total/avg confidence/trend, ColumnSet table for per-rep breakdown (rep name, quotes, accuracy %), "Voir la file" OpenUrl action button
  - [x] 2.3 Add `_build_manager_stats_card()`: brand accent, on-demand stats display with FactSet for requested metrics
  - [x] 2.4 Add dispatch branches in `_build_adaptive_card()` for `"batch-summary"`, `"manager-weekly"`, `"manager-stats"` card types

- [x] Task 3: Create `send_batch_summary()` and `send_weekly_report()` in a new notifier service (AC: #1, #2)
  - [x] 3.1 Create `src/quote_agent/services/scheduled_notifications.py` with:
    - `send_batch_summary(session, adapter, erp_settings) -> NotificationResult | None` — calls `get_daily_summary()`, builds NotificationPayload with `card_type="batch-summary"`, sends via adapter. Fire-and-forget pattern.
    - `send_weekly_report(session, adapter, erp_settings) -> NotificationResult | None` — calls `get_weekly_report()`, builds NotificationPayload with `card_type="manager-weekly"`, sends via adapter. Fire-and-forget pattern.
    - Both skip sending if no quotes to report (silence principle — "Nothing to process → No notification")

- [x] Task 4: Create CLI commands for batch summary and weekly report (AC: #1, #2, #3)
  - [x] 4.1 Create `src/quote_agent/cli/batch_notify.py` with:
    - `batch-summary` command: triggers `send_batch_summary()` immediately (for testing/manual trigger)
    - `weekly-report` command: triggers `send_weekly_report()` immediately (for testing/manual trigger)
    - `manager-stats` command: triggers on-demand stats and sends `manager-stats` card (AC: #3)
  - [x] 4.2 Register commands in `cli/main.py`

- [x] Task 5: Unit tests (AC: #1, #2, #3)
  - [x] 5.1 Test `_build_batch_summary_card()`: accent bar style, tier count FactSet, ERP link, message format
  - [x] 5.2 Test `_build_manager_weekly_card()`: accent bar, total/avg/trend FactSet, per-rep ColumnSet breakdown, ERP link
  - [x] 5.3 Test `_build_manager_stats_card()`: accent bar, stats FactSet, available commands display
  - [x] 5.4 Test `get_daily_summary()`: correct grouping by confidence tier, date filtering
  - [x] 5.5 Test `get_weekly_report()`: correct aggregation, rep breakdown, trend calculation
  - [x] 5.6 Test `send_batch_summary()`: success path, empty summary (no notification sent), failure (fire-and-forget)
  - [x] 5.7 Test `send_weekly_report()`: success path, empty report, failure
  - [x] 5.8 Test CLI commands: batch-summary, weekly-report, manager-stats invocations

## Dev Notes

### Architecture Patterns to Follow

- **Adapter 4-file pattern**: Extend existing `teams.py` for new card builders — do NOT create a new adapter file for notifications.
- **Card builder methods**: Add `_build_batch_summary_card()`, `_build_manager_weekly_card()`, `_build_manager_stats_card()` as private methods on `TeamsAdapter`, same pattern as `_build_quote_ready_card()`, `_build_multi_proposal_card()`, `_build_escalation_card()`.
- **Dispatch in `_build_adaptive_card()`**: Add `elif` branches for `"batch-summary"`, `"manager-weekly"`, `"manager-stats"` — follows existing `if/elif/else` chain at `teams.py:47-54`.
- **New service files allowed**: Unlike Stories 5.1-5.3 which extended existing nodes, this story creates *scheduled/on-demand* notifications that run OUTSIDE the LangGraph pipeline. Create new service files for stats queries and scheduled sending.
- **Fire-and-forget pattern**: Same pattern as `notifier.py` — catch all exceptions, log warnings, never crash.
- **Config pattern**: Follow existing `pydantic-settings` nested model pattern (see `ClassificationSettings`, `SearchCacheSettings`). Use `__` delimiter for env vars: `NOTIFICATION_SCHEDULE__BATCH_SUMMARY_HOUR=8`.

### Key Design Decision: NOT Inside the LangGraph Graph

Stories 5.1-5.3 are pipeline notifications sent as part of quote processing (graph nodes). Story 5.4 is fundamentally different:
- **Batch summary** aggregates ALL processed quotes and sends ONE notification at a scheduled time.
- **Weekly report** aggregates a full week of data.
- **Manager stats** is on-demand via CLI/bot command.

These are **service-layer operations**, not graph nodes. They query the database, build cards, and send notifications. They do NOT interact with `AgentState`.

### Card Design Specifications

**batch-summary card (UX-DR18):**
- Accent bar: `"style": "accent"` (brand blue)
- Header: `"Q — AI Quote Agent"` with `"weight": "Bolder"`, `"color": "Light"`
- Message: `f"Bonjour ! J'ai traité {total} devis. {high} prêts, {medium} besoin de ton choix, {low} besoin de ton expertise"` — casual French, tutoiement
- FactSet: `[{"title": "Prêts", "value": high}, {"title": "Choix nécessaire", "value": medium}, {"title": "Expertise nécessaire", "value": low}, {"title": "Total", "value": total}]`
- Action: `Action.OpenUrl` with `"title": "Voir la file ERP"`, URL = `{erp_settings.url}/web#model=sale.order&view_type=list`

**manager-weekly card (UX-DR19):**
- Accent bar: `"style": "accent"` (brand blue)
- Header: same as above
- Message: `f"Voici le récap de la semaine. {total} devis traités, confiance moyenne {avg_confidence}%"`
- FactSet: `[{"title": "Total traités", "value": total}, {"title": "Confiance moyenne", "value": f"{avg}%"}, {"title": "Tendance", "value": f"{'▲' if trend > 0 else '▼'} {abs(trend)}% vs semaine précédente"}]`
- ColumnSet per-rep breakdown: each row = rep name | quotes count | avg confidence %
- Action: same ERP queue link

**manager-stats card (UX-DR20):**
- Accent bar: `"style": "accent"` (brand blue)
- FactSet: requested stats (total, avg confidence, top reps)
- Additional TextBlock: "Commandes disponibles: stats jour, stats semaine, stats mois"

### Tone Rules (UX-DR22)

- Tutoiement (informal "tu")
- Short sentences, no corporate speak
- "Nothing to process → No notification" — never send empty summaries
- Percentages as integers: "87%" not "87.3%"
- Trends: arrow + percentage (e.g., "▲ +3% vs semaine précédente")

### Data Source: `quote_requests` Table

The batch summary and weekly report query the `quote_requests` table:
- **Status field**: `"pending"`, `"processed"`, `"error"` — filter on status != `"pending"` for completed work
- **Confidence field**: `float | None` — use confidence thresholds from `ConfidenceScoringSettings` (high_threshold=0.85, low_threshold=0.50) to classify into tiers
- **Created_at / Updated_at**: `TimestampMixin` columns — use for date range filtering
- **Client_name / Sender**: From `email_requests` table via `email_request_id` FK — for per-rep breakdown, use `email_requests.sender` as the rep identifier

### Query Logic

**Daily summary (`get_daily_summary`):**
```python
# Count quote_requests created/updated today, grouped by confidence tier
# high: confidence >= 0.85
# medium: 0.50 <= confidence < 0.85
# low: confidence < 0.50 OR confidence IS NULL
# Filter: status != 'pending' (only completed processing)
```

**Weekly report (`get_weekly_report`):**
```python
# Count quote_requests from last 7 days
# Compute avg(confidence) WHERE confidence IS NOT NULL
# Group by email_requests.sender for per-rep breakdown
# Compare with previous 7 days for trend
# trend_pct = ((this_week_total - prev_week_total) / prev_week_total * 100) if prev_week_total > 0 else 0
```

### Scheduling Implementation (MVP)

For MVP, scheduling is NOT automated. The CLI commands trigger reports manually. Automated scheduling (cron job or asyncio scheduler) is deferred to Story 5.5 (Règles de Timing & Batching). The config settings are added now to prepare for Story 5.5.

The CLI commands serve dual purpose:
1. Manual testing during development
2. Can be wired to system cron (`crontab -e`) for immediate automation

### Existing Code to Reuse (DO NOT reinvent)

| What | Where | Why |
|------|-------|-----|
| `TeamsAdapter._build_adaptive_card()` dispatch | `teams.py:45-54` | Add branches, don't restructure |
| `TeamsAdapter.send_notification()` | `teams.py:326-346` | Reuse as-is for sending |
| `NotificationPayload` DTO | `models.py:17-23` | Reuse as-is, `data` dict carries stats |
| `get_notification_adapter()` factory | `__init__.py` | Get cached adapter singleton |
| `ConfidenceScoringSettings` thresholds | `config.py:106-114` | Use `high_threshold`/`low_threshold` for tier classification |
| CLI registration pattern | `cli/main.py` | Register new commands same way as `notify-test` |
| `notify_test.py` CLI pattern | `cli/notify_test.py` | Follow same Click command + async pattern |
| `_get_session_factory()` | `models/base.py` | Get DB session for queries |

### Testing Standards

- **Quality gates**: `ruff check` + `mypy --strict` must pass.
- **Test count baseline**: 651 tests (after Story 5.3). Expect ~20-30 new tests.
- **Async tests**: Use `@pytest.mark.asyncio` + `AsyncMock`.
- **AC-N comments**: Tag each test with the acceptance criterion it verifies.
- **Card validation**: Assert on Adaptive Card JSON structure — accent style, body elements, FactSet facts, ColumnSet rows, action URL.
- **DB queries**: Use in-memory SQLite or mock SQLAlchemy session for stats query tests.
- **CLI tests**: Use Click's `CliRunner` for command invocation tests.
- **No E2E needed**: Scheduled notifications are service-layer; integration tests mock at webhook level.

### Previous Story Learnings (Stories 5.1-5.3)

- **`current_node` bug (5.2 review)**: Every function MUST set `current_node` to its actual node name. Not applicable here since we're not adding graph nodes, but keep the discipline for any state-returning functions.
- **Fire-and-forget pattern**: All notification sends must catch exceptions, log warnings, and never propagate errors. Copy the exact `try/except/logger.warning` pattern from `notifier.py`.
- **Card structure consistency**: All cards follow the same 5-layer structure: accent bar → bot avatar header → timestamp → content → action buttons. Follow this for the 3 new card types.
- **Dispatch pattern**: Add `elif` branches in `_build_adaptive_card()` — the `else` falls through to `_build_generic_card()`. Never rearrange existing branches.

### Project Structure Notes

**New files:**
- `src/quote_agent/services/notification_stats.py` — stats query functions + DTOs
- `src/quote_agent/services/scheduled_notifications.py` — batch summary + weekly report sending
- `src/quote_agent/cli/batch_notify.py` — CLI commands
- `tests/unit/test_notification_stats.py` — stats query tests
- `tests/unit/test_scheduled_notifications.py` — scheduled sending tests
- `tests/unit/test_batch_notify_cli.py` — CLI tests

**Modified files:**
- `src/quote_agent/config.py` — add `NotificationScheduleSettings`
- `src/quote_agent/adapters/notification/teams.py` — 3 new card builder methods + dispatch branches
- `src/quote_agent/cli/main.py` — register new CLI commands
- `tests/unit/test_notification_adapter.py` — new card builder tests

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.4]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — UX-DR18, UX-DR19, UX-DR20, UX-DR22, notification timing, card structure, batch summary flow, Marc weekly review journey]
- [Source: _bmad-output/planning-artifacts/prd.md — FR33-FR36, Journey 4 (Marc performance visibility)]
- [Source: _bmad-output/planning-artifacts/architecture.md — notification adapter pattern, batch processing, scheduling, PostgreSQL job queue]
- [Source: src/quote_agent/adapters/notification/teams.py — existing card builders, dispatch pattern]
- [Source: src/quote_agent/adapters/notification/models.py — NotificationPayload, NotificationResult DTOs]
- [Source: src/quote_agent/models/quote_request.py — QuoteRequest model with confidence and status fields]
- [Source: src/quote_agent/models/email_request.py — EmailRequest model with sender field for rep breakdown]
- [Source: src/quote_agent/config.py — existing settings pattern, confidence thresholds]
- [Source: docs/project-context.md — adapter pattern, async wrapping, config conventions, test naming]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No debug issues encountered.

### Completion Notes List

- Task 1: Added `NotificationScheduleSettings` to config.py with batch_summary_hour/minute, weekly_report_day/hour/minute. Created `notification_stats.py` with `get_daily_summary()` and `get_weekly_report()` async query functions + Pydantic DTOs (`DailySummary`, `WeeklyReport`, `RepStats`). Daily summary groups by confidence tiers (0.85/0.50 thresholds). Weekly report joins `email_requests.sender` for per-rep breakdown and computes trend vs previous week.
- Task 2: Added 3 card builder methods to `TeamsAdapter`: `_build_batch_summary_card()` (accent bar, tier FactSet, ERP link), `_build_manager_weekly_card()` (accent bar, summary FactSet with trend arrow, ColumnSet per-rep breakdown, ERP link), `_build_manager_stats_card()` (accent bar, stats FactSet, available commands TextBlock). Added dispatch branches in `_build_adaptive_card()`.
- Task 3: Created `scheduled_notifications.py` with `send_batch_summary()`, `send_weekly_report()`, and `send_manager_stats()`. All follow fire-and-forget pattern (try/except/logger.warning). Skip sending when no data (silence principle).
- Task 4: Created `batch_notify.py` CLI module with `batch-summary`, `weekly-report`, `manager-stats` commands. Registered all 3 in `cli/main.py`. Follows same async + Typer pattern as `notify_test.py`.
- Task 5: 47 new tests added (16 stats tests, 7 scheduled notification tests, 9 CLI tests, 15 card builder tests). All pass. Full regression: 698 passed, 0 failures.

### Change Log

- 2026-03-22: Story 5.4 implemented — batch summary, weekly report, and manager stats notifications (47 new tests, 698 total passing)
- 2026-03-22: Code review fixes — confidence thresholds injected from ConfidenceScoringSettings (M1), avg_confidence computed from weekly report instead of hardcoded 0 (L1), exposed `hostname` property on TeamsAdapter (L2)

### File List

**New files:**
- `src/quote_agent/services/notification_stats.py`
- `src/quote_agent/services/scheduled_notifications.py`
- `src/quote_agent/cli/batch_notify.py`
- `tests/unit/test_notification_stats.py`
- `tests/unit/test_scheduled_notifications.py`
- `tests/unit/test_batch_notify_cli.py`

**Modified files:**
- `src/quote_agent/config.py`
- `src/quote_agent/adapters/notification/teams.py`
- `src/quote_agent/cli/main.py`
- `tests/unit/test_notification_adapter.py`
