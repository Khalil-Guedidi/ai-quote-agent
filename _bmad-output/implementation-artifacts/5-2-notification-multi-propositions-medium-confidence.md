# Story 5.2: Notification Multi-Propositions (Medium Confidence)

Status: done

## Story

As a **sales rep (Sophie)**,
I want to receive a Teams notification with multiple product proposals when the agent is uncertain,
So that I can quickly pick the right option instead of searching the catalog myself.

## Acceptance Criteria

1. **Given** the agent generates 2-5 proposals for an ambiguous request, **When** the notification is sent, **Then** a Teams Adaptive Card uses the multi-proposal template: amber accent bar, bot avatar "Q", message ("Pas sûr à 100% sur le produit. Voici mes [N] options"), each option with product name, brief reasoning, and individual confidence score, ERP link button (UX-DR16).

2. **Given** Sophie receives the multi-proposal card, **When** she reviews the options, **Then** she can identify the correct product from the proposals and navigate to the ERP to finalize (FR34).

3. **Given** the routing decision is `generate_proposals` (medium tier), **When** the pipeline reaches the end, **Then** a notification is sent instead of proceeding to draft creation.

4. **Given** notification delivery fails, **When** the pipeline completes, **Then** the failure is logged but never blocks the pipeline or sets `state["error"]` (fire-and-forget pattern, same as Story 5.1).

## Tasks / Subtasks

- [x] Task 1: Build `_build_multi_proposal_card()` in `teams.py` (AC: #1)
  - [x] 1.1 Add `"multi-proposal"` branch in `_build_adaptive_card()` dispatch
  - [x] 1.2 Build card: amber accent (`style="warning"`), "Q" bot header, UTC timestamp
  - [x] 1.3 Render each proposal as a ColumnSet row: product name (bold), reasoning (subtle), confidence %
  - [x] 1.4 Add "Voir dans l'ERP" OpenUrl action button
- [x] Task 2: Create `notify_multi_proposal()` in `notifier.py` (AC: #3, #4)
  - [x] 2.1 Build NotificationPayload with `card_type="multi-proposal"`, proposals from `state["routing_decision"].proposals`
  - [x] 2.2 Wrap in fire-and-forget try/except (identical pattern to `notify_quote_ready`)
  - [x] 2.3 Return `{"notification_result": result, "current_node": "notify"}`
- [x] Task 3: Wire medium-confidence notification into the graph (AC: #3)
  - [x] 3.1 Add new `notify_proposals_node` in `graph.py` calling `notify_multi_proposal()`
  - [x] 3.2 Change routing: `_route_after_router` medium path → `notify_proposals` → END instead of direct END
  - [x] 3.3 Keep existing high-confidence path: `draft → notify → END` unchanged
- [x] Task 4: Unit tests (AC: #1, #2, #3, #4)
  - [x] 4.1 Test `_build_multi_proposal_card()`: amber accent, proposals rendered, ERP link present
  - [x] 4.2 Test `notify_multi_proposal()`: success path, failure path (fire-and-forget), missing routing_decision
  - [x] 4.3 Test graph wiring: medium-confidence route goes through notify_proposals → END
  - [x] 4.4 Test card schema: validate Adaptive Card v1.4 structure, FactSet/ColumnSet format

## Dev Notes

### Architecture Patterns to Follow

- **Adapter 4-file pattern**: Extend existing files (`teams.py`, `models.py`, `notifier.py`) — do NOT create new adapter files.
- **Card builder method**: Add `_build_multi_proposal_card(self, payload)` as a private method on `TeamsAdapter`, same pattern as `_build_quote_ready_card()`.
- **Dispatch in `_build_adaptive_card()`**: Add `elif payload.card_type == "multi-proposal"` branch — follows existing `if/else` chain at `teams.py:47-50`.
- **Fire-and-forget node**: Copy `notify_quote_ready()` pattern exactly: catch all exceptions, log warnings, never set `state["error"]`.

### Card Design (UX-DR16)

- **Accent bar**: Use `"style": "warning"` for amber (Teams semantic style, not raw hex).
- **Header**: `"Q — AI Quote Agent"` with `"weight": "Bolder"`, `"color": "Light"` — identical to existing cards.
- **Message**: `f"Pas sûr à 100% sur le produit. Voici mes {len(proposals)} options"` — casual French, tutoiement.
- **Proposals display**: Use a `ColumnSet` for each proposal with 3 columns:
  - Column 1: Product name (`TextBlock`, weight "Bolder")
  - Column 2: Match reasoning (`TextBlock`, isSubtle True)
  - Column 3: Confidence % (`TextBlock`, weight "Bolder")
- **Action button**: `Action.OpenUrl` with `"title": "Voir dans l'ERP"` — link to ERP order entry (not a specific quote since no draft exists yet). Use `{erp_settings.url}/web#model=sale.order&view_type=list` as the base URL.

### Payload Data Structure

The `NotificationPayload.data` dict for multi-proposal should contain:
```python
{
    "client": client_name,
    "proposals": [
        {
            "name": product.name,
            "reference": product.reference,
            "confidence_pct": str(round(product.confidence * 100)),
            "match_quality": product.match_quality,
        }
        for product in routing_decision.proposals
    ],
    "erp_url": f"{erp_settings.url}/web#model=sale.order&view_type=list",
}
```

Source: `ProductConfidence` model has fields `product_id`, `reference`, `name`, `confidence`, `match_quality`, `rank` — see `confidence_scorer.py:54-62`.

### Graph Wiring Changes

Current routing in `graph.py:29-35`:
```python
def _route_after_router(state):
    decision = state.get("routing_decision")
    if decision is not None and decision.action == "proceed_to_draft":
        return "review"
    return "end"  # ← medium + low + out_of_scope all go to END
```

**Required change**: Split the "end" path:
```python
def _route_after_router(state):
    decision = state.get("routing_decision")
    if decision is not None:
        if decision.action == "proceed_to_draft":
            return "review"
        if decision.action == "generate_proposals":
            return "notify_proposals"
    return "end"
```

Then update `graph.add_conditional_edges("route", ...)` mapping to include `{"review": "review", "notify_proposals": "notify_proposals", "end": END}`.

Add new node and edge:
```python
graph.add_node("notify_proposals", notify_proposals_node)
graph.add_edge("notify_proposals", END)
```

### Existing Code to Reuse (DO NOT reinvent)

| What | Where | Why |
|------|-------|-----|
| `TeamsAdapter._build_adaptive_card()` dispatch | `teams.py:45-59` | Add branch, don't restructure |
| `notify_quote_ready()` fire-and-forget pattern | `notifier.py:19-69` | Copy pattern for `notify_multi_proposal()` |
| `RoutingDecision.proposals` (list of `ProductConfidence`) | `router.py:34` | Already populated by router for medium tier |
| `NotificationPayload` DTO | `models.py:17-23` | Reuse as-is, `data` dict carries proposals |
| `graph.py` node wrapper pattern | `graph.py:245-251` | Same try/except wrapper for new node |
| Health check, send_notification, logging | `teams.py` | No changes needed to these methods |

### Testing Standards

- **Quality gates**: `ruff check` + `mypy --strict` must pass.
- **Test count baseline**: 623 tests (after Story 5.1). Expect ~10-15 new tests.
- **Mock pattern**: Mock `quote_agent.adapters.notification.get_notification_adapter` (source path, not local import).
- **Async tests**: Use `@pytest.mark.asyncio` + `AsyncMock`.
- **AC-N comments**: Tag each test with the acceptance criterion it verifies (e.g., `# AC-1: amber accent`).
- **Card validation**: Assert on Adaptive Card JSON structure — accent style, body elements, proposals count, action URL.
- **E2E**: No new E2E test needed for this story (notification is mocked at the webhook level in integration tests).

### Project Structure Notes

- All changes stay within existing module boundaries:
  - `src/quote_agent/adapters/notification/teams.py` — new card builder method
  - `src/quote_agent/agent/nodes/notifier.py` — new `notify_multi_proposal()` function
  - `src/quote_agent/agent/graph.py` — routing change + new node + edge
  - `tests/unit/test_notification_adapter.py` — card builder tests
  - `tests/unit/test_notifier_node.py` — node tests
  - `tests/unit/test_router.py` — verify routing decision unchanged (no regression)
- No new files, no new dependencies, no new models needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.2]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — UX-DR16, UX-DR21, UX-DR22]
- [Source: _bmad-output/planning-artifacts/architecture.md — Notification adapter pattern, confidence tier routing]
- [Source: _bmad-output/planning-artifacts/prd.md — FR34]
- [Source: src/quote_agent/agent/nodes/router.py — RoutingDecision, ProductConfidence, medium tier logic]
- [Source: src/quote_agent/adapters/notification/teams.py — existing card builders, dispatch pattern]
- [Source: src/quote_agent/agent/nodes/notifier.py — fire-and-forget pattern]
- [Source: src/quote_agent/agent/graph.py — current routing and node wiring]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- No debugging sessions needed — all tests passed on first implementation.

### Completion Notes List
- Task 1: Added `_build_multi_proposal_card()` to `TeamsAdapter` with amber accent (style=warning), ColumnSet proposal rows (name/reasoning/confidence%), "Voir dans l'ERP" OpenUrl action. Dispatch added in `_build_adaptive_card()`.
- Task 2: Created `notify_multi_proposal()` in notifier.py following exact fire-and-forget pattern from `notify_quote_ready()`. Builds `NotificationPayload` with `card_type="multi-proposal"` and proposals from `state["routing_decision"].proposals`.
- Task 3: Updated `_route_after_router()` to route `generate_proposals` → `notify_proposals` node instead of END. Added `notify_proposals_node` wrapper and `notify_proposals → END` edge. High-confidence path unchanged.
- Task 4: 13 new tests added across 3 test files (6 card builder, 6 notifier node, 1 graph compilation + updated 2 existing graph tests). All 636 tests pass with 0 regressions.
- Quality gates: ruff check passes, mypy strict passes on all changed files (pre-existing issue in sentence_transformers.py unrelated).

### Change Log
- 2026-03-22: Story 5.2 implementation complete — multi-proposal notification for medium-confidence routing

### File List
- src/quote_agent/adapters/notification/teams.py (modified — added _build_multi_proposal_card, dispatch branch)
- src/quote_agent/agent/nodes/notifier.py (modified — added notify_multi_proposal function)
- src/quote_agent/agent/graph.py (modified — updated routing, added notify_proposals node + edge)
- tests/unit/test_notification_adapter.py (modified — 6 new multi-proposal card tests)
- tests/unit/test_notifier_node.py (modified — 6 new multi-proposal notifier tests)
- tests/unit/test_agent_graph.py (modified — updated routing tests, added notify_proposals wiring test)
