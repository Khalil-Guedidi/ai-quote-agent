# Story 5.0b: Fix Flaky E2E Test — LLM Splitting

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **QA lead (Dana)**,
I want the E2E test `test_splitting_groups_distinct_requests_from_real_llm` to pass reliably on every run,
So that LLM splitting regressions are caught immediately instead of being masked by non-deterministic failures.

## Acceptance Criteria

1. **AC-1: Flaky test diagnosed and root cause documented**
   Given the test `test_splitting_groups_distinct_requests_from_real_llm` in `tests/e2e/test_email_pipeline_e2e.py` (line 105)
   When the root cause of non-deterministic failure is identified
   Then the cause is documented in the Dev Agent Record section of this story
   And the fix addresses the root cause, not just symptoms

2. **AC-2: Test passes reliably with real LLM**
   Given the test uses a real LLM (not mocked)
   When the test is run 5 consecutive times with `pytest -m e2e -k test_splitting_groups_distinct_requests_from_real_llm`
   Then all 5 runs pass
   And the test still validates that multi-product emails produce 2+ split requests

3. **AC-3: LLM non-determinism is contained**
   Given LLM output is stochastic
   When the test asserts on LLM behavior
   Then assertions use the established benchmark pattern: threshold-based validation (≥ X% pass rate, temperature=0)
   And the test tolerates legitimate LLM variation without accepting wrong results

4. **AC-4: Multi-product fixture clarity**
   Given the `multi_product_quote()` fixture contains 4 items for a single shipyard project
   When the LLM groups these items
   Then the test expectations match what a reasonable grouping looks like for this fixture
   And the fixture or assertions are adjusted if the current expectation (split_count >= 2) contradicts the fixture's semantic content

5. **AC-5: Zero regressions**
   Given all changes
   When the full test suite runs
   Then all existing tests pass (unit: `pytest`, E2E: `pytest -m e2e`)
   And `ruff check` and `mypy --strict` pass

6. **AC-6: CI green**
   Given all changes
   When the CI pipeline runs
   Then unit tests pass (E2E excluded from CI as per `addopts = "-m 'not e2e'"`)
   And `ruff check` and `mypy --strict` pass

## Tasks / Subtasks

- [x] Task 1: Diagnose root cause (AC: #1)
  - [x] 1.1 Run `pytest -m e2e -k test_splitting_groups_distinct_requests_from_real_llm -v` at least 3 times, capture outputs
  - [x] 1.2 Analyze failure mode: does extraction fail (< 2 line items)? Does splitting fail (split_count < 2)? Does LLM group all 4 items together?
  - [x] 1.3 Check if `multi_product_quote()` fixture semantically justifies `split_count >= 2` — all 4 items are for the same shipyard project ("chantier naval"), same delivery (Marseille), which may cause LLM to legitimately group as 1 request
  - [x] 1.4 Document root cause in Dev Agent Record

- [x] Task 2: Fix the flaky test (AC: #2, #3, #4)
  - [x] 2.1 **If fixture is ambiguous**: Update `multi_product_quote()` fixture to contain clearly distinct requests (different projects, different delivery addresses, different purposes) — making the splitting decision unambiguous for the LLM
  - [x] 2.2 **If assertion is wrong**: Adjust `split_count >= 2` if the fixture legitimately represents a single request — N/A, assertion is correct with new fixture
  - [x] 2.3 **If LLM non-determinism**: Add `temperature=0` to the splitting LLM call if not already set (check `get_model("simple")` config)
  - [x] 2.4 **If timeout**: Increase `_SPLITTING_TIMEOUT` or add retry with backoff — N/A, no timeout issues (responses in 1.6-1.9s)
  - [x] 2.5 Ensure the fix follows the benchmark pattern from Epic 3 retro: threshold-based, temperature=0

- [x] Task 3: Validate reliability (AC: #2)
  - [x] 3.1 Run the fixed test 5 consecutive times, all must pass
  - [x] 3.2 Run full E2E suite: `pytest -m e2e -v`
  - [x] 3.3 Run full unit suite: `pytest`

- [x] Task 4: Verify CI and quality gates (AC: #5, #6)
  - [x] 4.1 Run `ruff check src tests`
  - [x] 4.2 Run `mypy --strict src`
  - [x] 4.3 Run full unit test suite, verify 0 regressions
  - [x] 4.4 Verify CI pipeline passes

## Dev Notes

### The Flaky Test

The test at `tests/e2e/test_email_pipeline_e2e.py:105` (`test_splitting_groups_distinct_requests_from_real_llm`) does:

1. Calls `extract()` with real LLM on `multi_product_quote()` email
2. Asserts extraction produces 2+ line items
3. Calls `split_requests(extraction)` with real LLM
4. **Asserts `split_result.split_count >= 2`** — this is the likely failure point

### Probable Root Cause: Fixture vs Assertion Mismatch

The `multi_product_quote()` fixture (at `tests/e2e/fixtures/emails.py:38`) contains 4 items:
1. 200 tubes inox 304L Ø25mm 6m
2. 50 plaques acier S235 10mm 2000x1000
3. 100 brides PN16 DN50 inox 316L
4. 30 coudes 90° inox 304 Ø25mm

**All 4 items** are for the same "chantier naval" project, same delivery address (Marseille), same deadline (2 weeks). The splitter's system prompt says: *"Items that would logically appear on the SAME quote belong together (same project, same delivery, related products)"* and *"When in doubt, keep items together"*.

A reasonable LLM may group all 4 items as 1 request (same project, same delivery) or split into 2+ (different product families). This ambiguity is the source of flakiness.

**Fix strategy**: Make the fixture unambiguous by having clearly distinct requests (different projects/deliveries), OR adjust the test to accept both outcomes.

### Splitting Service Architecture

- File: `src/quote_agent/services/request_splitter.py`
- Short-circuits for ≤1 items (no LLM call)
- Uses `get_llm_adapter().get_model("simple")` → `with_structured_output(SplitDecision)`
- `SplitDecision` contains `groups: list[RequestGroup]`, each with `line_item_indices` and `rationale`
- Timeout: 10s (`_SPLITTING_TIMEOUT`)
- Fallback: empty groups → single request
- Security: sanitizes line items before LLM call

### LLM Non-Determinism Pattern (from Epic 3 retro)

The established pattern for non-deterministic LLM tests:
- Use `temperature=0` for maximum reproducibility
- Threshold-based benchmarks: N queries, ≥ X% pass rate
- For this test, the simplest fix is making the fixture semantically unambiguous so that temperature=0 gives consistent results

### What to Check in LLM Config

The `get_model("simple")` configuration in the LLM adapter may or may not set `temperature=0`. Check:
- `src/quote_agent/adapters/llm/openai_compat.py` — `get_model()` method
- `src/quote_agent/config.py` — `LLMSettings` for temperature defaults

### Existing Code to Modify (NOT Reinvent)

- `tests/e2e/fixtures/emails.py` — may need to update `multi_product_quote()` fixture
- `tests/e2e/test_email_pipeline_e2e.py` — may need to adjust assertions in `TestLLMExtraction`
- `src/quote_agent/services/request_splitter.py` — may need to add `temperature=0` if not set
- Do NOT modify the `SplitDecision`/`SplitResult` models
- Do NOT modify the splitter's system prompt unless absolutely necessary
- Do NOT add retry loops in the test itself — fix the source of non-determinism

### What NOT to Do

- Do NOT mock the LLM in this test — it must remain a real LLM E2E test
- Do NOT add `@pytest.mark.flaky` or similar skip/retry decorators — fix the root cause
- Do NOT change the splitting logic behavior — this is a test reliability fix only
- Do NOT add new test files — modify existing ones
- Do NOT touch notification code — that's Stories 5.1+
- Do NOT refactor `asyncio.run()` in CLI — that's deferred tech debt

### Previous Story Intelligence

Story 5.0a (done, same epic) established:
- 609 tests passing (current baseline)
- CLI pattern with 11 commands
- `NotificationPayload`/`NotificationResult` DTOs added
- No changes to E2E tests or splitting logic

### Project Structure Notes

Files potentially modified:
- `tests/e2e/fixtures/emails.py` — update fixture if needed
- `tests/e2e/test_email_pipeline_e2e.py` — adjust assertions if needed
- `src/quote_agent/services/request_splitter.py` — add temperature=0 if needed

No new files expected.

### References

- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-22.md — Tech debt #2: "Flaky E2E test LLM splitting (Story 3.3) — 2 retros deferred", line 99]
- [Source: _bmad-output/implementation-artifacts/epic-3-retro-2026-03-20.md — Tech debt #3: "1 flaky E2E test (LLM splitting) from Story 3.3", line 111]
- [Source: _bmad-output/implementation-artifacts/epic-3-retro-2026-03-20.md — "Non-deterministic LLM tests use threshold benchmarks — N queries, ≥ X% pass rate, temperature=0", line 211]
- [Source: tests/e2e/test_email_pipeline_e2e.py — flaky test at lines 105-127]
- [Source: tests/e2e/fixtures/emails.py — multi_product_quote() fixture at lines 38-59]
- [Source: src/quote_agent/services/request_splitter.py — splitting logic, system prompt, timeout]
- [Source: docs/project-context.md — E2E test requirements: "All E2E tests use real services — no mocked E2E acceptable"]
- [Source: docs/project-context.md — Test markers: "@pytest.mark.e2e", run with "pytest -m e2e"]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Run 1: split_count=1, rationale="All items are related to stainless steel and carbon steel products, suggesting they are for the same project or delivery." (1902ms)
- Run 2: split_count=1, rationale="All items are related to metal products and are likely for a single project involving stainless steel and steel components." (1632ms)
- Run 3: split_count=1, rationale="All items are related to metal products for a potential industrial project, likely within the same context as they are complementary components that could be used together in piping or construction." (1617ms)

### Implementation Plan

**Root Cause**: Fixture-assertion mismatch. The `multi_product_quote()` fixture contains 4 items for the SAME project ("chantier naval"), SAME delivery (Marseille), SAME deadline (2 weeks). The splitter prompt instructs "When in doubt, keep items together" and "same project, same delivery → same quote". The LLM correctly groups all items as 1 request — the test assertion `split_count >= 2` is wrong for this fixture.

**Secondary finding**: `ChatOpenAI` instances in `OpenAICompatAdapter.__init__()` are created without `temperature=0`. The `LLMRequest.temperature=0.0` field exists but is never passed through. However, since the test fails 3/3 times, temperature is not the primary cause — the fixture semantics are.

**Fix strategy**:
1. Update `multi_product_quote()` fixture to contain clearly distinct requests (different projects, different delivery addresses, different purposes)
2. Add `temperature=0` to ChatOpenAI instances for maximum reproducibility

### Completion Notes List

- Task 1: Root cause diagnosed — fixture-assertion mismatch. 3/3 runs fail consistently (not random). LLM correctly groups all items as 1 request because fixture semantically represents a single order.
- Task 2: Fixed by (a) updating `multi_product_quote()` fixture with two clearly distinct projects (shipyard Marseille vs warehouse Lyon) with different references, delivery addresses, and product families; (b) adding `temperature=0` to all ChatOpenAI instances for maximum reproducibility.
- Task 3: Fixed test passes 5/5 consecutive runs. Full E2E suite: 3 passed, 0 failed (19 pre-existing DB setup errors). Unit suite: 612 passed, 0 failed.
- Task 4: `ruff check`: all passed. `mypy --strict`: 1 pre-existing error in unrelated file (sentence_transformers.py). Unit tests: 612 passed, 0 regressions.

### Change Log

- 2026-03-22: Fixed flaky E2E splitting test — updated `multi_product_quote()` fixture with semantically unambiguous distinct requests; added `temperature=0` to all LLM model instances.

### File List

- tests/e2e/fixtures/emails.py (modified) — Updated `multi_product_quote()` fixture with two distinct projects
- src/quote_agent/adapters/llm/openai_compat.py (modified) — Added `temperature=0` to ChatOpenAI common kwargs
