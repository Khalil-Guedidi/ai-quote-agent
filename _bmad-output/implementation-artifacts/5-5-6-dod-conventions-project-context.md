# Story 5.5.6: DoD + Conventions in project-context.md

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Scrum Master (Bob) and Project Lead (Khalil)**,
I want the `docs/project-context.md` file updated with a formal Definition of Done, a copy-paste node safety checklist, codified E2E mandatory standards, and all conventions learned from Epics 4-5.5,
So that every future dev agent has an authoritative, up-to-date reference that prevents the recurring "floating agreement" pattern and codifies lessons that were previously lost between conversations.

## Acceptance Criteria

1. **Given** `docs/project-context.md` exists and is derived from Epics 1-3, **When** this story is complete, **Then** the document header states it covers Epics 1-5.5 and `last_updated` reflects today's date.

2. **Given** "CI green" was promised in the Epic 4 retro and lost as a floating agreement (confirmed lost again in Epic 5 retro — 4th consecutive confirmation that floating agreements die), **When** the DoD section is added, **Then** it includes as mandatory gates:
   - `uv run mypy --strict src/` — 0 issues
   - `uv run ruff check src/ tests/` — 0 issues
   - `uv run pytest tests/unit/ -v --tb=short` — 0 failures, 0 regressions
   - CI pipeline green (GitHub Actions) before merge
   - E2E tests passing for any story that modifies agent pipeline, adapters, or graph nodes

3. **Given** Story 5.2 introduced a copy-paste node bug (`current_node` not updated in 3 locations), **When** the conventions section is updated, **Then** a "Graph Node Checklist" subsection exists under conventions with the mandatory verification steps when creating or copying a graph node:
   - Update `current_node` in all state writes within the new node
   - Update routing function edge maps in `graph.py`
   - Add the node to `docs/graph-path-inventory.md`
   - Add at least one E2E test if the node creates a new path to END
   - Verify `final_action` value is unique and descriptive

4. **Given** 19 E2E tests were in silent failure for months (treated as "pre-existing" in every story instead of blockers — lesson from Epic 5 retro), **When** the E2E standards section is updated, **Then** it explicitly states:
   - E2E tests are gate-keepers: if they break, work stops until fixed
   - No mocked E2E acceptable (all real services)
   - Every new graph path to END must have a notification + E2E test
   - `NOTIFICATION__CHANNEL=log` mandatory in test environments (never send real Teams notifications)

5. **Given** Epics 4-5.5 introduced patterns not yet documented in project-context.md, **When** the document is updated, **Then** the following are added:
   - **Fire-and-forget notification pattern**: notification failure never blocks pipeline, never sets `state["error"]`
   - **Graph node pattern**: node function signature, state access, `current_node` setting, error handling with try/except returning state
   - **Notification adapter factory**: `get_notification_adapter()` with `@lru_cache(maxsize=1)`, routes by `settings.notification.channel`
   - **Scheduler pattern**: pure asyncio (no APScheduler/Celery), singleton via `@lru_cache`, conditional startup in FastAPI lifespan
   - **Post-pipeline error check**: `_send_error_notification()` in `process.py` for error states after `graph.ainvoke()`

6. **Given** the test count has grown significantly since Epics 1-3, **When** the Quality Gates section is updated, **Then** the test counts reflect current state: 781 unit tests, 28 E2E tests (22 pipeline + 6 graph paths), and the cache clearing list includes `get_notification_adapter` and `get_erp_adapter` (currently noted as TODO in the file).

7. **Given** new pitfalls were discovered in Epics 4-5, **When** the Known Pitfalls section is updated, **Then** it includes:
   - **Copy-paste node constants**: when duplicating a node, `current_node` and routing constants silently carry old values — always search-and-replace
   - **Fire-and-forget error masking**: notification errors in fire-and-forget nodes are caught and logged but never surface — check notification logs explicitly during testing
   - **Medium-confidence requires realistic data**: can't be triggered with 3-5 products, needs variant-rich catalogue with genuine ambiguity

## Tasks / Subtasks

- [x] Task 1: Add formal Definition of Done section (AC: #2)
  - [x] 1.1 Add a `## Definition of Done (DoD)` section after `## Quality Gates`
  - [x] 1.2 Include the 5 mandatory gates: mypy strict, ruff, pytest unit, CI green, E2E (when applicable)
  - [x] 1.3 Include scope note: "E2E gate applies to stories touching agent/, adapters/, search/, or graph nodes"
  - [x] 1.4 Include the anti-pattern note: "CI green is a gate, not a nice-to-have — floating agreements confirmed lost 4x"

- [x] Task 2: Add Graph Node Checklist (AC: #3)
  - [x] 2.1 Add `### Graph Node Checklist` under Conventions section
  - [x] 2.2 Document the 5-point checklist for new/copied graph nodes
  - [x] 2.3 Reference Story 5.2 copy-paste bug as rationale (without being verbose)

- [x] Task 3: Update E2E standards (AC: #4)
  - [x] 3.1 Update `### E2E Test Requirements` subsection under Quality Gates
  - [x] 3.2 Add gate-keeper rule: "if E2E breaks, work stops"
  - [x] 3.3 Add graph path rule: "every path to END → notification + E2E test"
  - [x] 3.4 Add `NOTIFICATION__CHANNEL=log` requirement for test environments

- [x] Task 4: Document new patterns from Epics 4-5.5 (AC: #5)
  - [x] 4.1 Add `### Fire-and-Forget Notification Pattern` under Established Patterns
  - [x] 4.2 Add `### Graph Node Pattern` under Established Patterns (node signature, state access, current_node, error handling)
  - [x] 4.3 Add notification adapter factory to the adapter listing (6th adapter)
  - [x] 4.4 Add `### Scheduler Pattern` under Established Patterns
  - [x] 4.5 Add post-pipeline error check pattern reference

- [x] Task 5: Update test counts and cache clearing (AC: #6)
  - [x] 5.1 Update test count in Quality Gates: 781 unit, 28 E2E
  - [x] 5.2 Update cache clearing list: add `get_notification_adapter.cache_clear()` and `get_erp_adapter.cache_clear()` as active (remove the TODO comment)
  - [x] 5.3 Update the adapter count from 5 to 6 (notification was already listed but verify consistency)

- [x] Task 6: Add new Known Pitfalls (AC: #7)
  - [x] 6.1 Add copy-paste node constants pitfall
  - [x] 6.2 Add fire-and-forget error masking pitfall
  - [x] 6.3 Add medium-confidence realistic data pitfall

- [x] Task 7: Update document header and metadata (AC: #1)
  - [x] 7.1 Update header line: "Derived from Epics 1-5.5 implementation and retrospectives"
  - [x] 7.2 Add last-updated date comment at top or in header

- [x] Task 8: Quality gates (AC: all)
  - [x] 8.1 `uv run mypy --strict src/` — 0 issues
  - [x] 8.2 `uv run ruff check src/ tests/` — 0 issues
  - [x] 8.3 `uv run pytest tests/unit/ -v --tb=short` — 0 regressions (780 pass, 1 pre-existing)
  - [x] 8.4 Verify project-context.md is valid markdown, no broken references
  - [x] 8.5 Verify Quick Reference section at top is updated to reflect all new additions

## Dev Notes

### The Problem (from Epic 4 + 5 Retros)

Three issues converge in this story:

1. **Floating agreements die** — "CI green in DoD" promised in Epic 4 retro, confirmed lost in Epic 5 retro. 4th consecutive confirmation: only items tracked as stories survive. This story IS the fix.

2. **Copy-paste node bug** — Story 5.2 had `current_node` set to "notify" instead of "notify_proposals" in 3 locations. Caught by code review, invisible to tests. Needs a documented checklist so dev agents don't repeat this.

3. **E2E tests were decoration, not gate-keepers** — 19/22 E2E tests failed silently for months. Same deferred-problem pattern as CI/CD across Epics 1-3. Now fixed (Story 5.5.2), but the standard was never codified.

### This is a Documentation-Only Story

No production code changes. Only `docs/project-context.md` is modified. Quality gates still apply (mypy, ruff, pytest) to verify no regressions — but there should be none since no source code is touched.

### Current State of project-context.md

**File**: `docs/project-context.md` (~553 lines)
**Current scope**: "Derived from Epics 1-3 implementation and retrospectives"
**Sections**: Quick Reference, Established Patterns (9 subsections), Known Pitfalls (17 entries), Conventions (5 subsections), Quality Gates (4 subsections), Decisions (1 entry), Tech Stack Summary

**What's missing** (this story adds):
- No formal DoD section — quality gates exist but without explicit "gate-keeper" language
- No graph node checklist — adapter pattern is well-documented but graph nodes are not
- E2E requirements exist but don't codify "gate-keeper" or "work stops" rules
- Patterns from Epics 4-5.5 are not documented (fire-and-forget, scheduler, post-pipeline error check)
- Test count is stale (shows 775 unit + 22 E2E, now 781 unit + 28 E2E)
- Cache clearing list has TODO comment for `get_erp_adapter` and `get_notification_adapter`
- Header says "Epics 1-3" but we're at Epic 5.5

### Where to Add New Sections

Follow the existing document structure:
- **DoD** → new section AFTER `## Quality Gates` (it's the natural next step: gates → definition of done)
- **Graph Node Checklist** → under `## Conventions` after `### Project Structure`
- **New patterns** → under `## Established Patterns` after existing subsections
- **New pitfalls** → at the end of `## Known Pitfalls`
- **Test count updates** → in-place edits within `## Quality Gates`
- **Cache clearing** → in-place edit within `### Settings Cache Clearing`

### What NOT To Do

- **DO NOT** restructure or rewrite existing sections — only add and update
- **DO NOT** touch any source code — this is documentation only
- **DO NOT** add verbose explanations — match the existing terse, reference-style tone
- **DO NOT** duplicate information already in the document — reference existing sections
- **DO NOT** add patterns that are already documented (adapter pattern, LLM structured output, etc.)
- **DO NOT** remove existing content — only add or update values
- **DO NOT** change section ordering except for adding the new DoD section

### Key Source References for New Content

| Content | Source |
|---------|--------|
| DoD gates | `docs/project-context.md#Quality-Gates` (existing gates) + Epic 4 retro action item #3 |
| Graph node checklist | Epic 5 retro tech debt #2 + Story 5.2 bug description |
| E2E gate-keeper rule | Epic 5 retro lesson #2 |
| Fire-and-forget pattern | Story 5.1 implementation, `src/quote_agent/agent/nodes/notifier.py` |
| Graph node pattern | `src/quote_agent/agent/nodes/classifier.py` (canonical example) |
| Scheduler pattern | Story 5.5 implementation, `src/quote_agent/services/notification_scheduler.py` |
| Post-pipeline error check | Story 5.5.5 Task 4, `src/quote_agent/cli/process.py` |
| Current test counts | Story 5.5.5 completion (781 unit, 6 graph E2E + 22 existing E2E) |

### Tone and Style Guide

Match the existing project-context.md style:
- **Terse, reference-style** — bullet points, code snippets, tables
- **No narrative prose** — this is a lookup document, not documentation
- **Code examples** — short, real examples from the codebase (not hypothetical)
- **Pitfall format** — title, one-line problem description, **Fix**: one-line solution
- **Convention format** — rule statement, optional code snippet or example

### Previous Story Learnings (Story 5.5.5)

- `create_graph()` + `graph.ainvoke(AgentState(...))` is the canonical pattern
- 14 distinct paths mapped from START to END in graph-path-inventory.md
- Post-pipeline error check implemented in `process.py` (Option B — minimal graph disruption)
- 781 unit tests passing, 0 regressions across 94 source files
- `NOTIFICATION__CHANNEL=log` forces `LogAdapter` usage in tests — prevents real Teams notifications

### Git Intelligence (Recent Commits)

```
f77ea8c feat: exhaustive graph path audit, fix silent drops, force log notifs in tests (Story 5.5.5)
9f7150e feat: add 50K scale E2E tests with NFR measurement (Story 5.5.4)
1d07e54 feat: seed Odoo with realistic data, fix ERP redirect and catalog coherence (Story 5.5.3)
9f962f4 fix: verify 22 E2E tests pass, remove all unittest.mock from E2E (Story 5.5.2)
845af9f fix: route review-rejected and compliance-blocked quotes through notify_rejection node (Story 5.5.1)
```

All 5 previous Epic 5.5 stories are tech stabilization — this story codifies the lessons from all of them.

### Project Structure Notes

- Only file modified: `docs/project-context.md`
- No new files created
- No source code changes
- Alignment: this story updates the central dev reference to match current project state

### References

- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Action-Items — item #6 "Update DoD + conventions in project-context.md"]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Lessons-Learned — §2 E2E gate-keepers, §4 floating agreements, §5 code review, §7 graph path audit]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Technical-Debt — #2 copy-paste node constants]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Team-Agreements — 8 permanent standards]
- [Source: _bmad-output/implementation-artifacts/5-5-5-audit-exhaustif-paths-graph.md — completion notes, test counts, cache clearing]
- [Source: _bmad-output/implementation-artifacts/5-5-2-fix-19-e2e-tests-en-echec.md — E2E test fix context]
- [Source: docs/project-context.md — current state, sections to update]
- [Source: docs/graph-path-inventory.md — path inventory for graph node checklist reference]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — documentation-only story, no debugging required.

### Completion Notes List

- Added formal Definition of Done section with 5 mandatory gates and anti-pattern note about floating agreements
- Added Graph Node Checklist (5 items) under Conventions with Story 5.2 rationale
- Updated E2E Test Requirements with gate-keeper rule, graph path rule, and NOTIFICATION__CHANNEL=log requirement
- Added 4 new patterns: Fire-and-Forget Notification, Graph Node, Scheduler, Post-Pipeline Error Check
- Updated adapter count from 5 to 6, test count to 781 unit + 28 E2E
- Updated cache clearing list: added get_erp_adapter and get_notification_adapter (removed TODO comment)
- Added 3 new Known Pitfalls: copy-paste node constants, fire-and-forget error masking, medium-confidence realistic data
- Updated header to "Epics 1-5.5" with last_updated: 2026-03-23
- Updated Quick Reference with new entries for all additions
- Quality gates: mypy 0 issues, ruff 0 issues, 780/781 unit tests pass (1 pre-existing failure in test_config.py)
- Code review fix: corrected adapter count from "6 types" to "5 types" in project structure comment (5 adapter categories, 6 implementations)

### Change Log

- 2026-03-23: Story 5.5.6 — Updated docs/project-context.md with DoD, graph node checklist, E2E standards, 4 new patterns, 3 new pitfalls, updated counts and cache clearing

### File List

- docs/project-context.md (modified — all changes)
