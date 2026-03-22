# Story 5.1: Notification Devis Prêt (High Confidence)

Status: done

## Story

As a **sales rep (Sophie)**,
I want to receive a Teams notification when a high-confidence quote is ready for review,
so that I know immediately when a draft is waiting in the ERP and can validate it quickly.

## Acceptance Criteria

1. **Given** the agent creates a high-confidence draft quote in Odoo, **When** draft creation succeeds, **Then** a Teams Adaptive Card is sent to Sophie within 30 seconds (NFR-P5), **And** the card uses the `quote-ready` template: green accent bar (`#16A34A`), bot avatar "Q", casual French message ("Salut ! Devis pour [Client] prêt..."), structured data (Client, Product, Quantity, Confidence %), "Voir dans l'ERP" action button (UX-DR15)

2. **Given** the notification is sent, **When** Sophie reads it, **Then** she can click "Voir dans l'ERP" to go directly to the draft quote in Odoo

3. **Given** the notification send fails (network error, timeout, webhook unreachable), **When** the failure occurs, **Then** the pipeline does NOT fail — the draft result is still returned, the error is logged with structured logging, and `final_action` remains `proceed_to_draft`

4. **Given** the agent pipeline reaches `draft_node` and creates a draft successfully, **When** the notify node runs, **Then** it uses the existing `TeamsAdapter.send_notification()` method with a `NotificationPayload` whose `card_type="quote-ready"` and `data` dict contains all structured fields

5. **Given** the notification feature is tested, **When** unit tests run, **Then** all new tests pass, existing 18 notification tests remain green, and `ruff check` + `mypy --strict` pass clean

## Tasks / Subtasks

- [x] Task 1: Extend `_build_adaptive_card` to support `quote-ready` card type (AC: #1)
  - [x] 1.1 Add a `_build_quote_ready_card(payload)` method to `TeamsAdapter` that builds a card with: green accent container (`#16A34A`), "Q" bot name, UTC timestamp, casual French message, FactSet with Client/Product/Quantity/Confidence, "Voir dans l'ERP" `Action.OpenUrl` button
  - [x] 1.2 Update `_build_adaptive_card` to dispatch to `_build_quote_ready_card` when `payload.card_type == "quote-ready"`, keep existing generic card as default fallback
  - [x] 1.3 Ensure the ERP link is built from `payload.data["erp_url"]` (constructed by caller from `settings.erp.url` + `/web#id={odoo_id}&model=sale.order`)

- [x] Task 2: Add `notify` node to the LangGraph pipeline (AC: #1, #3)
  - [x] 2.1 Create `src/quote_agent/agent/nodes/notifier.py` with an async `notify_quote_ready(state, notification_adapter, erp_settings)` function
  - [x] 2.2 This function: extracts `draft_result`, `raw_request`, `confidence`, `routing_decision` from state → builds `NotificationPayload(title="Devis prêt", message=casual_french_msg, card_type="quote-ready", data={client, product, quantity, confidence_pct, erp_url})` → calls `adapter.send_notification(payload)`
  - [x] 2.3 On send failure: log warning (structured), do NOT set `state["error"]` — notification failure must never block the pipeline
  - [x] 2.4 Return `{"notification_result": result, "current_node": "notify"}` (add `notification_result` to AgentState)

- [x] Task 3: Wire `notify` node into `graph.py` (AC: #1, #3)
  - [x] 3.1 Add `"notify"` node in `build_agent_graph` after `"draft"` node
  - [x] 3.2 Change edge: `draft → notify`, `notify → END` (instead of current `draft → END`)
  - [x] 3.3 Pass `get_notification_adapter()` as dependency to the notify node closure
  - [x] 3.4 Pass `settings.erp` to the notify node for ERP URL construction

- [x] Task 4: Update `AgentState` (AC: #4)
  - [x] 4.1 Add `notification_result: NotificationResult | None` to `AgentState` in `state.py`
  - [x] 4.2 Add runtime import for `NotificationResult` in state.py (same pattern as other imports)
  - [x] 4.3 Add `"notification_result": None` to `create_initial_state()`

- [x] Task 5: Unit tests (AC: #5)
  - [x] 5.1 Create `tests/unit/test_notifier_node.py` — test `notify_quote_ready`: success path (mock adapter returns success), failure path (mock adapter returns error → state still has no error), missing draft_result (graceful skip)
  - [x] 5.2 Add tests in `tests/unit/test_notification_adapter.py` for `_build_quote_ready_card`: verify green accent color, FactSet fields (Client, Product, Quantity, Confidence), "Voir dans l'ERP" OpenUrl action, casual French message format
  - [x] 5.3 Add test in `tests/unit/test_agent_graph.py` (or existing graph test file) verifying `notify` node is wired after `draft` and before END
  - [x] 5.4 Run full suite: `pytest -x -m 'not e2e'` — zero failures, zero regressions

## Dev Notes

### Architecture & Integration

- **Pipeline integration point**: The `notify` node runs AFTER `draft_node` succeeds. It is the last node before END in the high-confidence path: `... → compliance → draft → notify → END`
- **Non-blocking**: Notification failure must NEVER propagate as a pipeline error. Wrap the entire send in try/except, log the failure, and return a `NotificationResult(success=False, ...)`. The `final_action` stays `proceed_to_draft`
- **Only high-confidence path**: The notify node only executes after `draft_node`. For medium/low/out_of_scope, the pipeline still ends at the router (no notification yet — those are Stories 5.2, 5.3)

### Card Template: `quote-ready`

Adaptive Card v1.4 structure per UX spec (UX-DR15):
```json
{
  "type": "AdaptiveCard",
  "version": "1.4",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "body": [
    {"type": "Container", "style": "good", "bleed": true, "items": [
      {"type": "TextBlock", "text": "Q — AI Quote Agent", "weight": "Bolder", "color": "Light"}
    ]},
    {"type": "TextBlock", "text": "2026-03-22 14:30 UTC", "size": "Small", "isSubtle": true},
    {"type": "TextBlock", "text": "Salut ! Devis pour {client} prêt. Check quand t'as le temps.", "wrap": true},
    {"type": "FactSet", "facts": [
      {"title": "Client", "value": "{client_name}"},
      {"title": "Produit", "value": "{product_name}"},
      {"title": "Quantité", "value": "{quantity}"},
      {"title": "Confiance", "value": "{confidence}%"}
    ]}
  ],
  "actions": [
    {"type": "Action.OpenUrl", "title": "Voir dans l'ERP", "url": "{erp_url}"}
  ]
}
```

**Green accent**: Use `"style": "good"` on the accent Container (renders green in Teams). The hex `#16A34A` is for reference — Teams Adaptive Cards use semantic styles, not raw hex on containers.

**Tone rules** (UX-DR22): tutoiement, short sentences, never celebrate own work, no corporate speak. Example: "Salut ! Devis pour Durand prêt. Check quand t'as le temps." NOT "Great news! Quote successfully processed!"

### ERP URL Construction

Odoo web client URL pattern: `{settings.erp.url}/web#id={odoo_id}&model=sale.order&view_type=form`
- `settings.erp.url` comes from `ERPSettings.url` (e.g., `https://odoo.example.com`)
- `odoo_id` comes from `QuoteDraftResult.odoo_id` (integer)

### Existing Code to Reuse (DO NOT REINVENT)

| What | Where | How to reuse |
|------|-------|-------------|
| `TeamsAdapter.send_notification()` | `adapters/notification/teams.py` | Call directly — already handles httpx, timeouts, error wrapping |
| `NotificationPayload` DTO | `adapters/notification/models.py` | Use `card_type="quote-ready"`, put structured data in `data` dict |
| `NotificationResult` DTO | `adapters/notification/models.py` | Return type from send_notification, store in state |
| `get_notification_adapter()` | `adapters/notification/__init__.py` | Singleton factory — inject via closure in graph.py |
| `_build_adaptive_card` dispatch | `adapters/notification/teams.py` | Extend with card_type routing, don't replace |
| `QuoteDraftResult` | `adapters/erp/models.py` | Has `odoo_id` and `order_reference` — use for ERP URL and card data |
| `ERPSettings.url` | `config.py:47-53` | Base URL for Odoo, construct ERP deep link |
| Structured logging pattern | All nodes in `agent/nodes/*.py` | `logger.warning("...", extra={"context": {...}})` |

### Previous Story Intelligence (5.0a)

Key learnings from Story 5.0a:
- **Pydantic datetime import**: Use `# noqa: TC003` for runtime imports needed by Pydantic
- **Card structure**: Wrapped in `{"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": card}]}`
- **CLI mock target**: `quote_agent.adapters.notification.get_notification_adapter` (not the local import path)
- **Test count**: File currently has 18 tests, 464 lines — new tests add to this file
- **Ruff UP017**: Use `datetime.UTC` not `timezone.utc`

### Project Structure Notes

New file:
- `src/quote_agent/agent/nodes/notifier.py` — follows existing node pattern (see `classifier.py`, `router.py`, `confidence_scorer.py`)

Modified files:
- `src/quote_agent/adapters/notification/teams.py` — add `_build_quote_ready_card` + dispatch
- `src/quote_agent/agent/graph.py` — add notify node + rewire draft→notify→END
- `src/quote_agent/agent/state.py` — add `notification_result` field
- `tests/unit/test_notification_adapter.py` — add quote-ready card tests
- New: `tests/unit/test_notifier_node.py`

### Anti-Patterns to Avoid

- DO NOT create a separate notification service/orchestrator — the adapter is called directly from the node
- DO NOT make notification failure set `state["error"]` — it must be fire-and-forget with logging
- DO NOT use raw hex colors in Adaptive Card containers — use `"style": "good"` for green
- DO NOT hardcode French strings — but DO use casual tutoiement tone per UX spec
- DO NOT add batching/timing logic — that's Story 5.5
- DO NOT add medium/low confidence notification logic — those are Stories 5.2 and 5.3
- DO NOT modify the routing logic in `router.py` — the notify node sits AFTER draft, not in the router

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 5, Story 5.1]
- [Source: _bmad-output/planning-artifacts/architecture.md — Notification Adapter, Data Flow]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — UX-DR15, UX-DR21, UX-DR22, Teams Card Templates, Notification Patterns]
- [Source: _bmad-output/implementation-artifacts/5-0a-setup-teams-webhook-cli-notify-test.md — Previous story learnings]
- [Source: docs/project-context.md — Adapter pattern, async conventions, testing standards]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Full test suite: 623 passed, 2 skipped, 22 deselected (75s)
- Ruff check: All checks passed on all modified/new files
- Mypy --strict: Success, no issues found in 4 source files

### Completion Notes List

- ✅ Task 1: Refactored `_build_adaptive_card` into dispatcher with `_build_generic_card` (existing behavior) and `_build_quote_ready_card` (new quote-ready template with green accent `style=good`, FactSet, OpenUrl action)
- ✅ Task 2: Created `notifier.py` node — fire-and-forget pattern, builds `NotificationPayload` from state, catches all exceptions without setting `state["error"]`
- ✅ Task 3: Wired `notify` node after `draft` in graph.py: `draft → notify → END`. Uses `get_notification_adapter()` singleton and `settings.erp` via closure
- ✅ Task 4: Added `notification_result: NotificationResult | None` to `AgentState` and `create_initial_state()`
- ✅ Task 5: Added 6 new notification adapter tests (24 total), 5 notifier node tests, 1 graph wiring test. Updated state tests for new field. All 623 tests pass, ruff + mypy clean

### Change Log

- 2026-03-22: Story 5.1 implementation complete — quote-ready notification after high-confidence draft

### File List

New files:
- src/quote_agent/agent/nodes/notifier.py
- tests/unit/test_notifier_node.py

Modified files:
- src/quote_agent/adapters/notification/teams.py
- src/quote_agent/agent/graph.py
- src/quote_agent/agent/state.py
- tests/unit/test_notification_adapter.py
- tests/unit/test_agent_graph.py
- tests/unit/test_agent_state.py
- _bmad-output/implementation-artifacts/sprint-status.yaml
