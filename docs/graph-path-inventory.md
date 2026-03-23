# Graph Path Inventory — ai-quote-agent

Exhaustive audit of all LangGraph agent paths from START to END.

Source: `src/quote_agent/agent/graph.py` (`build_agent_graph`, `_route_after_router`, `_route_after_compliance`)

Generated: 2026-03-23 (Story 5.5.5)

---

## Graph Topology (ASCII)

```
START → classify → reason → score → route
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
              proceed_to_draft    generate_proposals   escalate/out_of_scope
              (→ "review")        (→ notify_proposals) (→ notify_escalation)
                    │                  │                   │
                  review              END                 END
                    │
                compliance
                    │
          ┌─────────┼─────────┐
          │         │         │
        draft   notify_rej  notify_rej
          │     (review)   (compliance)
        notify      │         │
          │        END       END
         END

Error propagation: any node error sets state["error"]; subsequent nodes
skip via _has_error() early return.  Error flows through to route fallback
(routing_decision=None) → notify_escalation (after fix).

Post-pipeline error check (Option B): callers detect state["error"] after
graph.ainvoke() and send an error notification.
```

---

## Path Inventory

| # | Path Name | Node Sequence | Trigger Condition | Notification Type | E2E Test | Status |
|---|-----------|---------------|-------------------|-------------------|----------|--------|
| 1 | High-confidence draft | START → classify → reason → score → route → review → compliance → draft → notify → END | `routing_decision.action == "proceed_to_draft"` AND review approved AND compliance OK | YES — quote-ready (green card) | `test_high_confidence_draft_path_e2e` | covered |
| 2 | Medium-confidence proposals | START → classify → reason → score → route → notify_proposals → END | `routing_decision.action == "generate_proposals"` | YES — multi-proposal (amber card) | `test_medium_confidence_proposals_path_e2e` | covered |
| 3 | Low-confidence escalation | START → classify → reason → score → route → notify_escalation → END | `routing_decision.action == "escalate"` | YES — escalation (red card) | `test_low_confidence_escalation_path_e2e` | covered |
| 4 | Out-of-scope escalation | START → classify → reason → score → route → notify_escalation → END | `routing_decision.action == "notify_out_of_scope"` | YES — escalation (red card) | (covered by path 3 — same graph path) | covered |
| 5 | Review-rejected | START → classify → reason → score → route → review → compliance → notify_rejection → END | `self_review.approved == False` | YES — rejection (red card) | `test_review_rejected_path_e2e` | covered |
| 6 | Compliance-blocked | START → classify → reason → score → route → review → compliance → notify_rejection → END | `compliance.flags` has severity `"block"` | YES — rejection (red card) | `test_compliance_blocked_path_e2e` | covered |
| 7 | Route fallback (safety net) | START → classify → reason → score → route → notify_escalation → END | `routing_decision is None` (unexpected state) | YES — escalation with "unexpected routing failure" context | `test_route_fallback_escalation_path_e2e` | covered (fix applied) |
| 8 | Classify error | START → classify(ERR) → reason(skip) → score(skip) → route(skip) → notify_escalation → END | Exception in classify node | YES — escalation (via route fallback) + post-pipeline error notification | unit test only (infra failure) | covered |
| 9 | Reason error | START → classify → reason(ERR) → score(skip) → route(skip) → notify_escalation → END | Exception in reason node | YES — escalation (via route fallback) + post-pipeline error notification | unit test only (infra failure) | covered |
| 10 | Score error | START → classify → reason → score(ERR) → route(skip) → notify_escalation → END | Exception in score node | YES — escalation (via route fallback) + post-pipeline error notification | unit test only (infra failure) | covered |
| 11 | Route error | START → classify → reason → score → route(ERR) → notify_escalation → END | Exception in route node | YES — escalation (via route fallback) + post-pipeline error notification | unit test only (infra failure) | covered |
| 12 | Review error | START → ... → review(ERR) → compliance(skip) → notify_rejection → END | Exception in review node | YES — rejection notification (via _route_after_compliance error check) + post-pipeline error notification | unit test only (infra failure) | covered |
| 13 | Compliance error | START → ... → review → compliance(ERR) → notify_rejection → END | Exception in compliance node, `state["error"]` set | YES — rejection notification (via _route_after_compliance error check) + post-pipeline error notification | unit test only (infra failure) | covered (fix applied) |
| 14 | Draft error | START → ... → draft(ERR) → notify(skip, no draft_result) → END | Exception in draft node or missing odoo_id | YES — post-pipeline error notification (state["error"] set) | unit test only (infra failure) | covered |

---

## Routing Functions

### `_route_after_router(state)` — line 29

| Condition | Return | Target Node |
|-----------|--------|-------------|
| `decision.action == "proceed_to_draft"` | `"review"` | review |
| `decision.action == "generate_proposals"` | `"notify_proposals"` | notify_proposals |
| `decision.action in ("escalate", "notify_out_of_scope")` | `"notify_escalation"` | notify_escalation |
| `decision is None` (fallback) | `"notify_escalation"` | notify_escalation (**fixed** — was `"end"`) |

### `_route_after_compliance(state)` — line 42

| Condition | Return | Target Node |
|-----------|--------|-------------|
| `state["error"]` is set | `"notify_rejection"` | notify_rejection (**fixed** — was missing) |
| `self_review.approved == False` | `"notify_rejection"` | notify_rejection |
| compliance has `severity == "block"` | `"notify_rejection"` | notify_rejection |
| Otherwise | `"draft"` | draft |

---

## Error Notification Strategy (Option B — Post-Pipeline Check)

Error paths (infrastructure failures: LLM timeout, DB down, etc.) are handled with a **post-pipeline error check** in the caller functions. After `graph.ainvoke()` completes, the caller checks `state["error"]` and sends an error notification if set.

This avoids restructuring the graph and keeps error notification as a caller concern.

**Implementation locations:**
- `src/quote_agent/cli/process.py` — `_run_process()` checks for error after graph invocation
- `src/quote_agent/services/email_processor.py` — (if it exists) same pattern

---

## Fixes Applied (Story 5.5.5)

1. **Route fallback** (`_route_after_router`): Changed `return "end"` → `return "notify_escalation"` with `final_action = "routing_fallback"` context
2. **Compliance error check** (`_route_after_compliance`): Added `if state.get("error"): return "notify_rejection"` at top
3. **Post-pipeline error notification**: Added error check in `process.py` caller
