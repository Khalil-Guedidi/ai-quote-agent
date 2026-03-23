# Story 5.5.5: Audit Exhaustif des Paths du Graph

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **technical lead (Khalil) and architect (Winston)**,
I want an exhaustive audit of all LangGraph agent paths to END — documenting notification coverage, identifying gaps, and adding missing E2E tests,
So that no quote request can silently disappear without notification and every path has verified test coverage.

## Acceptance Criteria

1. **Given** the agent graph in `src/quote_agent/agent/graph.py`, **When** the audit produces a path inventory document, **Then** every distinct path from START to END is listed with: node sequence, trigger condition, notification type (or explicit "silent — justified because…"), and E2E test reference.

2. **Given** the path inventory, **When** a path reaches END without sending a notification, **Then** either (a) it is an error path with a new `notify_error` node added that sends an escalation card with error context, or (b) it has an explicit justification comment in the code explaining why silence is acceptable.

3. **Given** the 5 happy paths (high-confidence draft, medium-confidence proposals, low-confidence escalation, review-rejected, compliance-blocked), **When** the audit completes, **Then** each has at least one dedicated E2E test that exercises the real graph pipeline (no mocks) and asserts the correct `final_action` value.

4. **Given** the error paths (classify error, reason error, score error, route error, review error, compliance error, draft error), **When** the audit identifies silent error paths, **Then** either a `notify_error` node is added or each error path has a documented justification + E2E test verifying the error is logged.

5. **Given** the route fallback path (`_route_after_router` returning `"end"` when `routing_decision is None`), **When** this edge case is analyzed, **Then** it routes to `notify_escalation` (with context "unexpected routing failure") instead of silently ending.

6. **Given** the `_route_after_compliance` function, **When** it receives a state with `error` field set (from compliance node exception), **Then** it routes to `notify_rejection` (not silently to draft or end), and this behavior is covered by a test.

7. **Given** all audit findings, **When** the path inventory is written to `docs/graph-path-inventory.md`, **Then** it includes a table with columns: Path Name, Node Sequence, Trigger, Notification Type, E2E Test, Status (covered/gap).

## Tasks / Subtasks

- [x] Task 1: Map all graph paths from source code (AC: #1, #7)
  - [x] 1.1 Read `src/quote_agent/agent/graph.py` — extract all nodes, edges, conditional routing functions
  - [x] 1.2 Trace every path from START to END through conditional branches
  - [x] 1.3 For each path, document: node sequence, trigger condition, notification sent (yes/no/type)
  - [x] 1.4 Cross-reference with `src/quote_agent/agent/nodes/notifier.py` to verify notification types
  - [x] 1.5 Write initial path inventory to `docs/graph-path-inventory.md`

- [x] Task 2: Fix route fallback silent path (AC: #5)
  - [x] 2.1 In `_route_after_router()` (graph.py ~line 29-39), change the fallback `return "end"` to `return "notify_escalation"`
  - [x] 2.2 Ensure the escalation node receives enough context from state to explain "unexpected routing — no decision from router"
  - [x] 2.3 Add conditional edge mapping if not present: `"notify_escalation"` in the route node's edge map (removed dead `"end"` mapping)
  - [x] 2.4 Add unit test: `test_none_routing_decision_routes_to_notify_escalation()` (updated existing test)

- [x] Task 3: Fix `_route_after_compliance` error-state gap (AC: #6)
  - [x] 3.1 In `_route_after_compliance()` (graph.py ~line 42-54), add error check at the TOP: `if state.get("error"): return "notify_rejection"`
  - [x] 3.2 Add unit test: `test_error_state_routes_to_notify_rejection()`

- [x] Task 4: Decide error-path notification strategy (AC: #2, #4)
  - [x] 4.1 Analyze the 7 error paths (classify/reason/score/route/review/compliance/draft exceptions)
  - [x] 4.2 **Decision: Option B** — post-pipeline error check in caller (minimal graph disruption)
  - [x] 4.3 Implemented Option B with `_send_error_notification()` in process.py
  - [x] 4.4 Added error notification call in `src/quote_agent/cli/process.py` (only caller of graph.ainvoke)
  - [x] 4.5 Added unit tests: `test_process_sends_error_notification_when_error_in_state`, `test_process_no_error_notification_when_no_error`

- [x] Task 5: Add missing E2E tests for untested paths (AC: #3)
  - [x] 5.1 Create `tests/e2e/test_graph_paths_e2e.py` — dedicated file for path coverage
  - [x] 5.2 E2E test: `test_high_confidence_draft_path_e2e` — exact reference query → `proceed_to_draft` → `notify` (green card)
  - [x] 5.3 E2E test: `test_medium_confidence_proposals_path_e2e` — ambiguous query → `generate_proposals` → `notify_proposals` (amber card)
  - [x] 5.4 E2E test: `test_low_confidence_escalation_path_e2e` — out-of-scope query → `escalate` → `notify_escalation` (red card)
  - [x] 5.5 E2E test: `test_review_rejected_path_e2e` — craft a request that triggers self-review rejection → `notify_rejection`
  - [x] 5.6 E2E test: `test_compliance_blocked_path_e2e` — craft a request with sanctioned entity → `notify_rejection`
  - [x] 5.7 E2E test: `test_route_fallback_escalation_path_e2e` — verify the route fallback fix sends escalation
  - [x] 5.8 Each test asserts: correct `final_action`, notification result present, no `state["error"]` (for happy paths)

- [x] Task 6: Update path inventory with test references (AC: #7)
  - [x] 6.1 Update `docs/graph-path-inventory.md` with E2E test references for each path
  - [x] 6.2 Mark each path as covered/gap
  - [x] 6.3 Add ASCII diagram of the graph with all paths annotated

- [x] Task 7: Quality gates (AC: all)
  - [x] 7.1 `uv run mypy --strict src/` — 0 issues (94 source files)
  - [x] 7.2 `uv run ruff check src/ tests/` — 0 issues
  - [x] 7.3 `uv run pytest tests/unit/ -v --tb=short` — 781 passed, 0 regressions
  - [x] 7.4 Existing E2E tests unaffected: scale 5/5 passing, graph paths E2E passing
  - [x] 7.5 New path E2E tests pass: `tests/e2e/test_graph_paths_e2e.py` — all passing against real services

## Dev Notes

### The Problem (from Epic 5 Retro, Lesson #7)

"Graph path exhaustivity must be audited — review-rejected was a 5th path to END that nobody inventoried. Every path must have: notification (or explicit justification) + E2E test coverage."

Story 5.5.1 fixed the review-rejected and compliance-blocked silent drops by adding a `notify_rejection` node. But the full graph was never systematically audited. This story completes that audit.

### Current Graph Structure (from source analysis)

```
START → classify → reason → score → route
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
              proceed_to_draft    generate_proposals   escalate/out_of_scope
                    │                  │                   │
                  review         notify_proposals    notify_escalation
                    │                  │                   │
                compliance            END                END
                    │
          ┌─────────┼─────────┐
          │         │         │
        draft   notify_rej  notify_rej
          │     (review)   (compliance)
        notify      │         │
          │        END       END
         END
```

### Known Path Inventory (11 paths identified)

| # | Path | Notification | E2E Test | Status |
|---|------|-------------|----------|--------|
| 1 | High-confidence → draft → notify | YES (green) | Scale test only | Gap: needs dedicated E2E |
| 2 | Medium-confidence → notify_proposals | YES (amber) | Scale tier test only | Gap: needs dedicated E2E |
| 3 | Low-confidence → notify_escalation | YES (red) | None | Gap |
| 4 | Review-rejected → notify_rejection | YES (red) | None | Gap |
| 5 | Compliance-blocked → notify_rejection | YES (red) | None | Gap |
| 6 | Route fallback → END | NO (silent!) | None | **FIX NEEDED** |
| 7 | Classify error → route early-return → END | NO (silent) | None | Gap — needs decision |
| 8 | Reason error → route early-return → END | NO (silent) | None | Gap — needs decision |
| 9 | Score error → route early-return → END | NO (silent) | None | Gap — needs decision |
| 10 | Route error → END | NO (silent) | None | Gap — needs decision |
| 11 | Draft error → END | NO (silent) | None | Gap — needs decision |

### Production Code Changes (Minimal)

This story modifies production code in 2-3 places:

1. **`graph.py` — `_route_after_router()`**: Change fallback `return "end"` to `return "notify_escalation"` (1 line)
2. **`graph.py` — `_route_after_compliance()`**: Add error check at top (2-3 lines)
3. **Error notification caller** (Option B): Add post-pipeline error check in `process.py` or `email_processor.py` (~10 lines)

### E2E Test Strategy

All new E2E tests go in `tests/e2e/test_graph_paths_e2e.py`. They exercise the real graph via `create_graph()` + `graph.ainvoke()` — same pattern as `test_scale_50k_e2e.py` but with targeted inputs to trigger specific paths.

**Triggering specific paths with real services:**
- **High-confidence**: exact product reference match (e.g., `"FLT-50um-10L/min-RRO"`)
- **Medium-confidence**: ambiguous category query with many variants (needs enough products seeded)
- **Low-confidence/out-of-scope**: service request, not a product (e.g., `"prestation de nettoyage"`)
- **Review-rejected**: requires crafting a request that passes routing but fails self-review validation — tricky with real LLM. May need a product reference that doesn't exist in DB (catalog hallucination trigger) or a quantity that fails plausibility
- **Compliance-blocked**: requires a request mentioning a sanctioned entity from OFAC/EU/UN lists
- **Route fallback**: requires routing_decision to be None — may need to temporarily test with a mocked router state, or verify the fix makes this path unreachable (then document as "dead code — fallback safety net")

**Important:** E2E tests use ALL real services. No `unittest.mock` in E2E (project standard since Story 5.5.2). If a path is impossible to trigger reliably with real services, document why and provide a unit test as alternative coverage.

### What NOT To Do

- **DO NOT** restructure the entire graph — changes are surgical (2-3 locations)
- **DO NOT** add a global error-handling wrapper node — Option B (post-pipeline check) is simpler
- **DO NOT** use `unittest.mock` in E2E tests — all real services
- **DO NOT** change the fire-and-forget notification pattern — notification failure still must not block pipeline
- **DO NOT** modify existing notification card formats — reuse escalation card type for error paths
- **DO NOT** add retry logic for error paths — that's a different concern (existing retry is in adapters)
- **DO NOT** create new CLI commands — use existing graph API for tests

### Key Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| Agent graph | `src/quote_agent/agent/graph.py` | `create_graph()`, `_route_after_router()`, `_route_after_compliance()` |
| Agent state | `src/quote_agent/agent/state.py` | `AgentState` TypedDict |
| Notifier nodes | `src/quote_agent/agent/nodes/notifier.py` | `notify_quote_ready()`, `notify_multi_proposal()`, `notify_escalation()`, `notify_rejection()` |
| Router node | `src/quote_agent/agent/nodes/router.py` | `route_by_confidence()` |
| Self-reviewer | `src/quote_agent/agent/nodes/self_reviewer.py` | 4-step validation |
| Compliance checker | `src/quote_agent/agent/nodes/compliance_checker.py` | Sanctions + export control |
| Draft node | `src/quote_agent/agent/nodes/draft.py` | ERP quote creation |
| CLI process | `src/quote_agent/cli/process.py` | Pipeline caller (Option B target) |
| Email processor | `src/quote_agent/services/email_processor.py` | Email pipeline caller |
| E2E conftest | `tests/e2e/conftest.py` | Shared E2E fixtures, skip markers |
| Scale tests | `tests/e2e/test_scale_50k_e2e.py` | Reference for graph invocation pattern |
| Unit graph tests | `tests/unit/test_agent_graph.py` | Existing unit tests for routing logic |

### Previous Story Learnings (Story 5.5.4)

- `create_graph()` + `graph.ainvoke(AgentState(...))` is the canonical pattern for programmatic pipeline invocation
- `test_confidence_tier_diversity_50k_e2e` asserts >= 2 distinct `final_action` values — good pattern but weak assertion. This story should assert specific `final_action` per test.
- Medium-confidence triggers reliably with ambiguous queries on 50K catalogue
- Session-scoped fixtures for expensive setup (embedding, bulk loading)
- NFR metrics helper (`tests/e2e/helpers/nfr_metrics.py`) available for timing measurements

### Previous Story Learnings (Story 5.5.1)

- `notify_rejection` node was added to handle review-rejected and compliance-blocked paths
- The routing logic in `_route_after_compliance()` checks `self_review.approved` and `compliance.flags` severity
- Card type for rejection is `"escalation"` (red accent) with title variants: "Escalade — Rejet auto-review" or "Escalade — Blocage conformité"
- The conditional edge map is: `{"draft": "draft", "notify_rejection": "notify_rejection", "end": END}`

### Project Structure Notes

- New file: `tests/e2e/test_graph_paths_e2e.py` — dedicated graph path E2E tests
- New file: `docs/graph-path-inventory.md` — path inventory document
- Modified file: `src/quote_agent/agent/graph.py` — route fallback fix + compliance error check
- Possibly modified: `src/quote_agent/cli/process.py` or `src/quote_agent/services/email_processor.py` (Option B error notification)
- No changes to notification card formats or adapter pattern

### References

- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Lessons-Learned §7 — "Graph path exhaustivity must be audited"]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Epic-5.5 — Story 5.5.5 definition]
- [Source: _bmad-output/implementation-artifacts/5-5-1-fix-review-rejected-silent-drop.md — notify_rejection implementation]
- [Source: _bmad-output/implementation-artifacts/5-5-4-canari-50k-pipeline-a-echelle.md — graph invocation pattern]
- [Source: src/quote_agent/agent/graph.py — create_graph(), routing functions]
- [Source: src/quote_agent/agent/nodes/notifier.py — all notification node implementations]
- [Source: docs/project-context.md#Quality-Gates — mypy strict, ruff, pytest requirements]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Unit test regression: `test_skips_notification_when_no_routing_decision` failed after notify_escalation was updated to send fallback notifications instead of skipping. Updated test to `test_sends_fallback_escalation_when_no_routing_decision`.

### Completion Notes List

- **Task 1**: Mapped 14 distinct paths from START to END. Created `docs/graph-path-inventory.md` with full path table, routing function analysis, and ASCII diagram.
- **Task 2**: Fixed route fallback — `_route_after_router()` now returns `"notify_escalation"` instead of `"end"` when `routing_decision` is None. Updated `notify_escalation()` to handle None routing_decision by sending fallback escalation with error context. Removed dead `"end"` mapping from route edge map. Route node now sets `final_action = "routing_fallback"` on error state.
- **Task 3**: Fixed `_route_after_compliance()` — added `if state.get("error"): return "notify_rejection"` at top so error state from review/compliance exceptions routes to rejection notification instead of silently continuing to draft.
- **Task 4**: Implemented Option B (post-pipeline error check) — added `_send_error_notification()` in `process.py` that sends an escalation-type notification when `state["error"]` is set after graph invocation.
- **Task 5**: Created `tests/e2e/test_graph_paths_e2e.py` with 6 E2E tests covering all major paths: high-confidence draft, medium-confidence proposals, low-confidence escalation, review-rejected, compliance-blocked, and route fallback verification.
- **Task 6**: Path inventory document written with test references, status (covered/gap), and ASCII diagram.
- **Task 7**: All quality gates pass — mypy strict 0 issues (94 files), ruff 0 issues, 781 unit tests passing (0 regressions). E2E tests require real services (PostgreSQL, LLM, Odoo).

### File List

**New files:**
- `docs/graph-path-inventory.md` — exhaustive path inventory with 14 paths documented
- `tests/e2e/test_graph_paths_e2e.py` — 6 E2E tests for graph path coverage

**Modified files:**
- `src/quote_agent/agent/graph.py` — route fallback fix (`_route_after_router`), compliance error check (`_route_after_compliance`), route node error context, edge map cleanup
- `src/quote_agent/agent/nodes/notifier.py` — `notify_escalation()` now handles None routing_decision with fallback escalation
- `src/quote_agent/cli/process.py` — added `_send_error_notification()` and post-pipeline error check
- `tests/unit/test_agent_graph.py` — updated route fallback test, added compliance error test, updated classify error test
- `tests/unit/test_cli_process.py` — added error notification tests
- `tests/unit/test_notifier_node.py` — updated escalation missing routing test

### Change Log

- 2026-03-23: Story 5.5.5 implemented — exhaustive graph path audit, 3 production fixes (route fallback, compliance error, post-pipeline error notification), 6 new E2E tests, path inventory document
- 2026-03-23: Code review — fixed path #12 doc error in graph-path-inventory.md (review error routes to notify_rejection, not draft). 0 HIGH, 1 MEDIUM fixed, 2 LOW accepted. Status → done.
