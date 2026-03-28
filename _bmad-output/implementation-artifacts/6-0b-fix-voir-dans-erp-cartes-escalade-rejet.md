# Story 6.0b: Fix "Voir dans l'ERP" sur Cartes Escalade/Rejet

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the "Voir dans l'ERP" link to be contextually appropriate on escalation and rejection notification cards,
So that I'm not presented with a useless link when no draft quote exists in Odoo.

## Context

On escalation (low confidence, out-of-scope) and rejection (compliance block, self-review reject) notification cards, the "Voir dans l'ERP" button links to the generic sale orders list (`/erp/sale-orders`). This is useless to Sophie: no draft was created for these requests, so there's nothing relevant to see in the orders list. The link is misleading and breaks trust.

**Current behavior:** All escalation/rejection cards show "Voir dans l'ERP" linking to the generic orders list — the same link regardless of context.

**Target behavior:** Escalation/rejection cards replace "Voir dans l'ERP" with "Voir la demande" linking to the original email request view, or hide the ERP link entirely when no draft exists.

**Why it matters:** This is a UX bug visible to the end user. Sophie clicks "Voir dans l'ERP" expecting to see something related to the request she just got notified about, but lands on a generic orders list with no connection to the escalated/rejected request.

Found during Epic 5.5 stabilization, designated as foundation story for Epic 6 (2026-03-28).

## Acceptance Criteria

1. **AC-1: Escalation cards have contextual action**
   Given a notification card for an escalation (low confidence or out-of-scope)
   When no draft quote has been created in the ERP
   Then the "Voir dans l'ERP" link is replaced with "Voir la demande" linking to the email request detail page
   Or the ERP link is hidden entirely (no dead-end link)

2. **AC-2: Rejection cards have contextual action**
   Given a notification card for a rejection (compliance block or self-review reject)
   When no draft quote has been created in the ERP
   Then the "Voir dans l'ERP" link is replaced with "Voir la demande" linking to the email request detail page
   Or the ERP link is hidden entirely (no dead-end link)

3. **AC-3: High/medium confidence cards unchanged (no regression)**
   Given a notification card for a high-confidence (quote-ready) or medium-confidence (multi-proposal) quote
   When a draft quote exists or proposals were generated
   Then the "Voir dans l'ERP" link continues to work exactly as before

4. **AC-4: E2E tests validate link behavior per tier**
   Given the fix is applied
   When E2E tests covering notification cards run
   Then all pass and the link behavior is validated for each confidence tier

5. **AC-5: Quality gates pass**
   Given the fix is applied
   When quality checks run
   Then `uv run mypy --strict src/` reports 0 issues
   And `uv run ruff check src/ tests/` reports 0 issues
   And `uv run pytest tests/unit/ -v --tb=short` reports 0 failures

## Tasks / Subtasks

- [x] Task 1: Decide on replacement action for escalation/rejection cards (AC: #1, #2)
  - [x] 1.1 Determine available context at notification time: is `quote_request_id` or `email_request_id` in state?
  - [x] 1.2 Check if an email request detail page exists in the API (`/api/email-requests/{id}`)
  - [x] 1.3 If no request detail page exists, the simplest fix is to **remove the action button entirely** from escalation/rejection cards
  - [x] 1.4 If a request detail page exists, create a redirect endpoint `/erp/email-request/{id}` (similar to existing `/erp/sale-order/{id}`) — N/A: no detail page exists, used approach 1.3

- [x] Task 2: Update notifier nodes to pass contextual link (AC: #1, #2)
  - [x] 2.1 In `notify_escalation()` (notifier.py:150-227): removed `erp_url` from payload data entirely (also removed `get_settings` import and `base_url` computation)
  - [x] 2.2 In `notify_rejection()` (notifier.py:230-319): same change — removed `erp_url`, `get_settings`, and `base_url`

- [x] Task 3: Update Teams card builder (AC: #1, #2)
  - [x] 3.1 In `_build_escalation_card()` (teams.py:248-335): conditionally render the action button based on whether `data.get("erp_url")` is truthy
  - [x] 3.2 If replacing with "Voir la demande": use a different `data` key (e.g., `request_url`) and different button title — N/A: used "remove button" approach

- [x] Task 4: Verify high/medium cards unchanged (AC: #3)
  - [x] 4.1 Confirm `notify_quote_ready()` and `notify_multi_proposal()` are untouched — verified, no changes made
  - [x] 4.2 Run existing unit tests for quote-ready and multi-proposal cards — all pass (799 total)

- [x] Task 5: Update unit tests (AC: #1, #2, #5)
  - [x] 5.1 Update `test_notifier_node.py` escalation/rejection tests: assert `"erp_url" not in payload.data`
  - [x] 5.2 Update `test_notification_adapter.py` escalation card tests: replaced `test_build_escalation_card_has_erp_link` with `test_build_escalation_card_no_action_when_no_erp_url`
  - [x] 5.3 Add test: `test_build_escalation_card_has_action_when_erp_url_present` — escalation card with `erp_url` in data renders action button (backwards-compatible behavior)
  - [x] 5.4 Add test: rejection card with no `erp_url` in data renders without action button — covered by `test_build_escalation_card_no_action_when_no_erp_url` since rejection uses `card_type="escalation"`

- [x] Task 6: Run quality gates (AC: #5)
  - [x] 6.1 `uv run ruff check src/ tests/` — 0 issues
  - [x] 6.2 `uv run ruff format --check src/ tests/` — 0 issues on modified files
  - [x] 6.3 `uv run mypy --strict src/` — 0 issues
  - [x] 6.4 `uv run pytest tests/unit/ -v --tb=short` — 799 passed, 0 failures

## Dev Notes

### The Bug

The root cause is in **two places**:

1. **Notifier nodes** (`src/quote_agent/agent/nodes/notifier.py`):
   - `notify_escalation()` (line 192): builds `erp_url = f"{base_url}/erp/sale-orders"` — a generic orders list link
   - `notify_rejection()` (line 280): same generic link
   - Both send this URL in the payload `data["erp_url"]`

2. **Teams card builder** (`src/quote_agent/adapters/notification/teams.py`):
   - `_build_escalation_card()` (line 328-334): unconditionally renders "Voir dans l'ERP" action button using `data["erp_url"]`
   - Both escalation and rejection cards use `card_type="escalation"` so they share the same builder

The **quote-ready** card correctly links to the specific draft: `/erp/sale-order/{odoo_id}` — this is not broken.

The **multi-proposal** card links to the generic orders list — this is acceptable since the agent may have created draft candidates. Not in scope for this story.

### Recommended Fix: Remove the Action Button

The simplest and most honest fix is to **remove the "Voir dans l'ERP" action button** from escalation/rejection cards entirely. No draft was created, so there's nothing to "voir dans l'ERP".

**In notifier.py:**
- `notify_escalation()`: stop including `erp_url` in payload data
- `notify_rejection()`: stop including `erp_url` in payload data

**In teams.py:**
- `_build_escalation_card()`: only include the `actions` array if `data.get("erp_url")` is truthy

This is a 2-file, ~10-line change. No new endpoints, no new models, no business logic changes.

### Alternative: "Voir la demande" Link

If Khalil prefers the card to link to the original email request, this requires:
1. Adding the `email_request_id` or `quote_request_id` to `AgentState` (verify it's available)
2. Creating a new redirect endpoint in `erp_redirect.py`
3. Passing the request URL instead of ERP URL in the payload

More complex but provides a better UX. **Wait for Khalil's decision before implementing this alternative.**

### Files to Modify

**2 source files:**
- `src/quote_agent/agent/nodes/notifier.py` — remove `erp_url` from escalation/rejection payloads
- `src/quote_agent/adapters/notification/teams.py` — conditional action button rendering in `_build_escalation_card()`

**2 test files:**
- `tests/unit/test_notifier_node.py` — update escalation/rejection assertions
- `tests/unit/test_notification_adapter.py` — update escalation card action assertions

**0 new files required** (for the "remove button" approach).

### What NOT to Do

- Do NOT change `notify_quote_ready()` or `notify_multi_proposal()` — they work correctly
- Do NOT change `_build_quote_ready_card()` or `_build_multi_proposal_card()` — no regression
- Do NOT create a new card_type — rejection already uses `card_type="escalation"` and that's fine
- Do NOT add new API endpoints unless Khalil chooses the "Voir la demande" alternative
- Do NOT change the ERP redirect endpoints (`erp_redirect.py`) — they work correctly for their use cases

### Key Code Locations

| Concept | File | Lines |
|---------|------|-------|
| Escalation notifier (builds erp_url) | `notifier.py` | 189-192 |
| Rejection notifier (builds erp_url) | `notifier.py` | 277-280 |
| Escalation card builder (renders button) | `teams.py` | 248-335 |
| Quote-ready notifier (correct, don't touch) | `notifier.py` | 19-81 |
| Multi-proposal notifier (correct, don't touch) | `notifier.py` | 84-147 |
| ERP redirect endpoints | `erp_redirect.py` | 1-36 |
| Notifier unit tests | `test_notifier_node.py` | full file |
| Card builder unit tests | `test_notification_adapter.py` | ~503-825 |

### Graph Paths Affected

From `docs/graph-path-inventory.md`:
- **Path 3** (low-confidence escalation): ... → route → notify_escalation → END
- **Path 4** (out-of-scope escalation): ... → route → notify_escalation → END
- **Path 5** (compliance block): ... → compliance → notify_rejection → END
- **Path 6** (review rejection): ... → compliance → notify_rejection → END
- **Path 7** (route fallback): ... → route → notify_escalation → END

Paths 1 (high-confidence draft) and 2 (medium-confidence proposals) are NOT affected.

### Previous Story Intelligence

**From Story 6.0a (done):**
- `asyncio.run()` refactored to `main.py` — all CLI implementation files now export async functions
- 21 pre-existing test failures were fixed (self_reviewer mock dispatch, router threshold, notification health check method, worker config .env leak)
- Quality gates: mypy strict 0 issues, ruff 0 issues, 799 unit tests passing
- Pattern confirmed: `main.py` sync wrapper → `asyncio.run()` → async implementation

### Anti-Pattern Prevention

- **Do NOT add `erp_url` with empty string**: An empty URL in an Action.OpenUrl is worse than no button — Teams may show a broken link
- **Do NOT use conditional rendering based on card_type**: The escalation card builder is shared by both escalation and rejection. Use `data.get("erp_url")` presence as the signal
- **Do NOT suppress the button in the notifier by sending `erp_url: ""`**: Remove the key entirely from the payload data dict

### Project Structure Notes

- Follows existing adapter pattern: card builders in `teams.py`, notification logic in `notifier.py`
- `LogAdapter` in `adapters/notification/log.py` also receives the payload — verify it handles missing `erp_url` gracefully (it logs payload as-is, no issue)
- Tests follow `test_{behavior}_when_{condition}()` naming convention

### References

- [Source: _bmad-output/implementation-artifacts/epic-5-5-retro-2026-03-28.md] — UX bug identified during stabilization
- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.0b] — AC and user story
- [Source: src/quote_agent/agent/nodes/notifier.py] — notification node implementations
- [Source: src/quote_agent/adapters/notification/teams.py] — Teams card builders
- [Source: src/quote_agent/api/erp_redirect.py] — ERP redirect endpoints
- [Source: docs/graph-path-inventory.md] — all graph paths from START to END
- [Source: docs/project-context.md#Fire-and-Forget Notification Pattern] — notification nodes never block pipeline

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation with no debugging required.

### Completion Notes List

- Decision: Removed "Voir dans l'ERP" action button entirely from escalation/rejection cards (approach 1.3). No `email_request_id` in `AgentState` and no `/api/email-requests/{id}` endpoint exists, so "Voir la demande" alternative was not viable without new infrastructure.
- `notify_escalation()`: removed `get_settings()` import, `base_url` computation, and `erp_url` from payload data dict.
- `notify_rejection()`: same removal — `get_settings()`, `base_url`, and `erp_url` removed from payload.
- `_build_escalation_card()` in teams.py: changed from unconditional `"actions"` key to conditional — only includes action button if `data.get("erp_url")` is truthy. This preserves backwards compatibility if `erp_url` is ever added back.
- Updated `_escalation_payload()` test fixture to accept `with_erp_url` parameter (default `False`).
- Removed "escalation" from `_CARD_TYPES_WITH_ACTIONS` structural consistency test set since escalation cards no longer unconditionally have actions.
- All 799 unit tests pass. mypy strict 0 issues. ruff 0 issues.

### Change Log

- 2026-03-28: Implemented Story 6.0b — removed misleading "Voir dans l'ERP" button from escalation/rejection notification cards. 2 source files, 2 test files modified. No new files.

### File List

- `src/quote_agent/agent/nodes/notifier.py` — removed `erp_url` from escalation and rejection payloads
- `src/quote_agent/adapters/notification/teams.py` — conditional action button rendering in `_build_escalation_card()`
- `tests/unit/test_notifier_node.py` — updated escalation/rejection assertions to verify `erp_url` absence
- `tests/unit/test_notification_adapter.py` — replaced/added escalation card action tests, updated fixture and structural consistency set
