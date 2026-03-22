# Story 5.3: Notification d'Escalade (Low Confidence)

Status: done

## Story

As a **sales rep (Sophie)**,
I want to receive a Teams notification with enriched context when the agent escalates a request,
So that I understand why the agent couldn't process it and have the context I need to handle it manually.

## Acceptance Criteria

1. **Given** the agent classifies a request as low confidence (`action="escalate"`) or out-of-scope (`action="notify_out_of_scope"`), **When** escalation is triggered, **Then** a Teams Adaptive Card uses the escalation template: red accent bar, bot avatar "Q", honest message ("Celui-là est compliqué..."), context section (what was understood, what is uncertain, suggested next steps), ERP link button (UX-DR17, FR35).

2. **Given** the escalation card is sent, **When** Sophie reads it, **Then** the context explains: what was understood, what is uncertain, and why the agent couldn't proceed (FR15).

3. **Given** the routing decision is `escalate` or `notify_out_of_scope`, **When** the pipeline reaches the end, **Then** a notification is sent instead of silently ending the pipeline.

4. **Given** notification delivery fails, **When** the pipeline completes, **Then** the failure is logged but never blocks the pipeline or sets `state["error"]` (fire-and-forget pattern, same as Story 5.1 and 5.2).

## Tasks / Subtasks

- [x] Task 1: Build `_build_escalation_card()` in `teams.py` (AC: #1, #2)
  - [x] 1.1 Add `"escalation"` branch in `_build_adaptive_card()` dispatch
  - [x] 1.2 Build card: red accent (`style="attention"`), "Q" bot header, UTC timestamp
  - [x] 1.3 Render message: casual French ("Celui-là est compliqué...")
  - [x] 1.4 Render context section: "Ce que j'ai compris" (understood), "Ce qui est flou" (uncertain)
  - [x] 1.5 Render suggested next steps as a bullet list
  - [x] 1.6 Add "Voir dans l'ERP" OpenUrl action button
- [x] Task 2: Create `notify_escalation()` in `notifier.py` (AC: #3, #4)
  - [x] 2.1 Build NotificationPayload with `card_type="escalation"`, context from `state["routing_decision"].escalation_context`
  - [x] 2.2 Handle `notify_out_of_scope` case: when `escalation_context` is None, build fallback context from `state["classification"].reasons`
  - [x] 2.3 Wrap in fire-and-forget try/except (identical pattern to `notify_quote_ready` and `notify_multi_proposal`)
  - [x] 2.4 Return `{"notification_result": result, "current_node": "notify_escalation"}`
- [x] Task 3: Wire escalation notification into the graph (AC: #3)
  - [x] 3.1 Add new `notify_escalation_node` in `graph.py` calling `notify_escalation()`
  - [x] 3.2 Change routing: `_route_after_router` — both `escalate` AND `notify_out_of_scope` → `notify_escalation` → END
  - [x] 3.3 Update conditional edges mapping to include `"notify_escalation": "notify_escalation"`
  - [x] 3.4 Keep existing high-confidence and medium-confidence paths unchanged
- [x] Task 4: Unit tests (AC: #1, #2, #3, #4)
  - [x] 4.1 Test `_build_escalation_card()`: red accent, context sections rendered, ERP link present
  - [x] 4.2 Test `notify_escalation()`: success path (with escalation_context), success path (out_of_scope — no escalation_context), failure path (fire-and-forget), missing routing_decision
  - [x] 4.3 Test graph wiring: `escalate` route → `notify_escalation` → END, `notify_out_of_scope` route → `notify_escalation` → END
  - [x] 4.4 Test card schema: validate Adaptive Card v1.4 structure, context TextBlocks, action URL

## Dev Notes

### Architecture Patterns to Follow

- **Adapter 4-file pattern**: Extend existing files (`teams.py`, `notifier.py`) — do NOT create new adapter files.
- **Card builder method**: Add `_build_escalation_card(self, payload)` as a private method on `TeamsAdapter`, same pattern as `_build_quote_ready_card()` and `_build_multi_proposal_card()`.
- **Dispatch in `_build_adaptive_card()`**: Add `elif payload.card_type == "escalation"` branch — follows existing `if/elif/else` chain at `teams.py:47-52`.
- **Fire-and-forget node**: Copy `notify_multi_proposal()` pattern exactly: catch all exceptions, log warnings, never set `state["error"]`.
- **`current_node` value**: Must be `"notify_escalation"` (matching the graph node name) — Story 5.2 code review caught a bug where `notify_multi_proposal` was returning `"notify"` instead of `"notify_proposals"`. Do NOT repeat this mistake.

### Card Design (UX-DR17)

- **Accent bar**: Use `"style": "attention"` for red (Teams semantic style for critical/attention).
- **Header**: `"Q — AI Quote Agent"` with `"weight": "Bolder"`, `"color": "Light"` — identical to existing cards.
- **Message**: `f"Celui-là est compliqué. {client_name} demande quelque chose que je ne suis pas sûr de comprendre."` — casual French, tutoiement, admits uncertainty honestly.
- **Context display**: Use `Container` sections for structured context:
  - **"Ce que j'ai compris"** label (`TextBlock`, weight "Bolder") + understood text (`TextBlock`, wrap True)
  - **"Ce qui est flou"** label (`TextBlock`, weight "Bolder") + uncertain text (`TextBlock`, wrap True, isSubtle True)
  - **"Prochaines étapes suggérées"** label (`TextBlock`, weight "Bolder") + each step as a `TextBlock` with bullet prefix ("• ")
- **Action button**: `Action.OpenUrl` with `"title": "Voir dans l'ERP"` — link to ERP sale order list (no specific quote since no draft exists). Use `{erp_settings.url}/web#model=sale.order&view_type=list` as the base URL.

### Payload Data Structure

The `NotificationPayload.data` dict for escalation should contain:
```python
{
    "client": client_name,
    "understood": escalation_context.understood,
    "uncertain": escalation_context.uncertain,
    "suggested_next_steps": escalation_context.suggested_next_steps,
    "confidence_pct": str(round(routing_decision.confidence * 100)),
    "erp_url": f"{erp_settings.url}/web#model=sale.order&view_type=list",
}
```

### Handling `notify_out_of_scope` (No EscalationContext)

The router builds `EscalationContext` only for `action="escalate"` (low confidence). For `action="notify_out_of_scope"`, `escalation_context` is `None` (see `router.py:52-57`).

The `notify_escalation()` function must handle this gracefully:
```python
routing_decision = state.get("routing_decision")
if routing_decision is None:
    # Graceful skip
    return {"notification_result": None, "current_node": "notify_escalation"}

escalation_ctx = routing_decision.escalation_context
if escalation_ctx is not None:
    understood = escalation_ctx.understood
    uncertain = escalation_ctx.uncertain
    steps = escalation_ctx.suggested_next_steps
else:
    # Fallback for out_of_scope — build context from classification
    classification = state.get("classification")
    understood = "; ".join(classification.reasons) if classification else "Demande classée hors périmètre"
    uncertain = "Cette demande ne correspond pas au périmètre de l'agent (pas un produit catalogue)"
    steps = ["Traiter la demande manuellement", "Vérifier si le client a besoin d'un autre service"]
```

### Graph Wiring Changes

Current routing in `graph.py:29-37`:
```python
def _route_after_router(state):
    decision = state.get("routing_decision")
    if decision is not None:
        if decision.action == "proceed_to_draft":
            return "review"
        if decision.action == "generate_proposals":
            return "notify_proposals"
    return "end"  # ← escalate + out_of_scope still go to END silently
```

**Required change**: Route escalation and out_of_scope to a notification node:
```python
def _route_after_router(state):
    decision = state.get("routing_decision")
    if decision is not None:
        if decision.action == "proceed_to_draft":
            return "review"
        if decision.action == "generate_proposals":
            return "notify_proposals"
        if decision.action in ("escalate", "notify_out_of_scope"):
            return "notify_escalation"
    return "end"
```

Then update `graph.add_conditional_edges("route", ...)` mapping:
```python
{
    "review": "review",
    "notify_proposals": "notify_proposals",
    "notify_escalation": "notify_escalation",
    "end": END,
}
```

Add new node and edge:
```python
graph.add_node("notify_escalation", notify_escalation_node)
graph.add_edge("notify_escalation", END)
```

### Existing Code to Reuse (DO NOT reinvent)

| What | Where | Why |
|------|-------|-----|
| `TeamsAdapter._build_adaptive_card()` dispatch | `teams.py:45-52` | Add branch, don't restructure |
| `notify_multi_proposal()` fire-and-forget pattern | `notifier.py:72-123` | Copy pattern for `notify_escalation()` |
| `RoutingDecision.escalation_context` | `router.py:35` | Already populated for escalate action |
| `EscalationContext` model (understood, uncertain, steps) | `router.py:20-25` | Read-only, do not modify |
| `NotificationPayload` DTO | `models.py:17-23` | Reuse as-is, `data` dict carries context |
| `graph.py` node wrapper pattern | `graph.py:255-261` | Same try/except wrapper for new node |
| Health check, send_notification, logging | `teams.py` | No changes needed to these methods |

### Testing Standards

- **Quality gates**: `ruff check` + `mypy --strict` must pass.
- **Test count baseline**: 636 tests (after Story 5.2). Expect ~12-18 new tests.
- **Mock pattern**: Mock `quote_agent.adapters.notification.get_notification_adapter` (source path, not local import).
- **Async tests**: Use `@pytest.mark.asyncio` + `AsyncMock`.
- **AC-N comments**: Tag each test with the acceptance criterion it verifies (e.g., `# AC-1: red accent`).
- **Card validation**: Assert on Adaptive Card JSON structure — accent style, body elements, context sections, action URL.
- **Graph tests**: Update existing routing tests (`test_escalate_routes_to_end` → `test_escalate_routes_to_notify_escalation`, `test_notify_out_of_scope_routes_to_end` → `test_notify_out_of_scope_routes_to_notify_escalation`).
- **Full path test**: Add a full graph execution test for escalation path (like `test_generate_proposals_routes_through_notify_proposals`).
- **E2E**: No new E2E test needed for this story (notification is mocked at the webhook level in integration tests).

### Previous Story Learnings (Story 5.2 Code Review)

- **Bug found**: `current_node` was set to `"notify"` instead of `"notify_proposals"` in 3 locations. Every node MUST set `current_node` to its actual graph node name — for this story use `"notify_escalation"`.
- **Testing**: Graph execution tests should assert `current_node` matches the expected node name.
- **Pattern**: The `notify_proposals_node` wrapper in graph.py catches exceptions and returns `{"notification_result": None, "current_node": "notify_proposals"}` — follow this exact pattern for `notify_escalation_node`.

### Project Structure Notes

- All changes stay within existing module boundaries:
  - `src/quote_agent/adapters/notification/teams.py` — new card builder method + dispatch branch
  - `src/quote_agent/agent/nodes/notifier.py` — new `notify_escalation()` function
  - `src/quote_agent/agent/graph.py` — routing change + new node + edge
  - `tests/unit/test_notification_adapter.py` — card builder tests
  - `tests/unit/test_notifier_node.py` — node tests
  - `tests/unit/test_agent_graph.py` — updated routing tests + full path test
- No new files, no new dependencies, no new models needed.
- Do NOT modify `router.py` — the `EscalationContext` and routing logic are correct as-is.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.3]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Escalation card design, tone rules, card structure consistency]
- [Source: _bmad-output/planning-artifacts/prd.md — FR14, FR15, FR35]
- [Source: src/quote_agent/agent/nodes/router.py — RoutingDecision, EscalationContext, escalate/out_of_scope routing]
- [Source: src/quote_agent/adapters/notification/teams.py — existing card builders, dispatch pattern]
- [Source: src/quote_agent/agent/nodes/notifier.py — fire-and-forget pattern, notify_multi_proposal]
- [Source: src/quote_agent/agent/graph.py — current routing and node wiring]
- [Source: src/quote_agent/agent/nodes/confidence_scorer.py — ConfidenceResult, ProductConfidence models]
- [Source: src/quote_agent/agent/nodes/classifier.py — ClassificationResult, complexity levels]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debugging needed.

### Completion Notes List

- ✅ Task 1: Built `_build_escalation_card()` with red accent (`style="attention"`), 3 context Container sections (understood, uncertain, suggested steps), casual French message, and ERP OpenUrl action button.
- ✅ Task 2: Created `notify_escalation()` following exact fire-and-forget pattern from `notify_multi_proposal()`. Handles both `escalate` (with `EscalationContext`) and `notify_out_of_scope` (fallback from `classification.reasons`). Sets `current_node="notify_escalation"` correctly (learned from Story 5.2 bug).
- ✅ Task 3: Updated `_route_after_router()` to route `escalate` and `notify_out_of_scope` to `notify_escalation` instead of END. Added `notify_escalation_node` wrapper, conditional edge mapping, and edge to END.
- ✅ Task 4: 15 new tests (6 card builder, 8 notifier node, 1 graph compilation). Updated 2 existing graph routing tests and 2 full-path execution tests to verify notify_escalation path. Total: 651 tests passing, 0 regressions.

### Change Log

- 2026-03-22: Implemented Story 5.3 — escalation notification for low-confidence and out-of-scope routing. 15 new tests added (636 → 651).

### File List

- src/quote_agent/adapters/notification/teams.py (modified — added `_build_escalation_card()` + dispatch branch)
- src/quote_agent/agent/nodes/notifier.py (modified — added `notify_escalation()`)
- src/quote_agent/agent/graph.py (modified — routing change, new node, new edge)
- tests/unit/test_notification_adapter.py (modified — 6 new escalation card tests)
- tests/unit/test_notifier_node.py (modified — 8 new escalation notifier tests)
- tests/unit/test_agent_graph.py (modified — updated routing tests + full path tests + compilation test)
