# Story 4.4: Self-Review avant Soumission

Status: done

## Story

As a **sales rep (Sophie)**,
I want the agent to self-review its own output before creating the draft quote,
So that errors, hallucinations, and manipulated outputs are caught before they reach me.

## Acceptance Criteria

1. **AC-1: Catalog Validation (Anti-hallucination FR27)** — Given the agent has produced a draft quote result (a `ReasoningResult` with matched products), when the self-review node runs, then it validates that each proposed product exists in the current catalog by checking product IDs against the database.

2. **AC-2: Quantity Plausibility** — Given a draft result with product matches and requested quantities, when the self-review runs, then it validates that quantities are plausible (positive, non-zero, within reasonable industrial ranges) and flags implausible values.

3. **AC-3: Coherence with Original Request** — Given the reasoning output and the original extracted request, when the self-review runs, then it uses LLM structured output to verify that the proposed products are coherent with what was originally requested (descriptions match intent, specifications align).

4. **AC-4: Prompt Injection Defense Layer 3 (FR24-26)** — Given the self-review is the 3rd layer of prompt injection defense, when it validates output, then it checks that the output is coherent with system instructions (not influenced by email content manipulation) and any detected anomaly is flagged and logged.

5. **AC-5: Rejection and Re-routing** — Given the self-review detects a hallucinated product (not in catalog) or critical incoherence, when validation fails, then the draft is rejected with a `SelfReviewResult` indicating `approved=False`, failure reasons are documented, and the result can be used by the caller to re-route for re-processing or escalation.

6. **AC-6: Reasoning Trace** — For all reviews (pass or fail), each validation step is recorded with step name, duration, and outcome in the `SelfReviewResult`.

7. **AC-7: CLI Command** — A `uv run quote-agent review "description"` command runs the full pipeline (classify → reason → score → route → self-review) and displays the review verdict, validation steps, and any flagged issues.

## Tasks / Subtasks

- [x] Task 1: Create DTOs (AC: #1-6)
  - [x] `ValidationStep` model — step_name, passed (bool), detail, duration_ms
  - [x] `SelfReviewResult` model — approved (bool), steps (list[ValidationStep]), failure_reasons (list[str]), review_duration_ms, anomaly_flags (list[str])
  - [x] `SelfReviewSettings` config — timeout_seconds, max_quantity (plausibility upper bound), min_quantity (plausibility lower bound)
- [x] Task 2: Implement `self_review()` async function (AC: #1-6)
  - [x] `_validate_catalog_existence()` — check each product ID in `ReasoningResult.search_result.results` exists in DB via search engine or direct query
  - [x] `_validate_quantity_plausibility()` — check quantities from `ExtractedQuoteRequest.line_items` are positive and within configured bounds
  - [x] `_validate_coherence()` — LLM structured output call to verify match coherence between request and proposed products
  - [x] `_validate_output_integrity()` — LLM check that output is not influenced by prompt injection (layer 3 defense)
  - [x] Aggregate all validation steps into `SelfReviewResult`
  - [x] `approved = True` only if ALL validation steps pass
- [x] Task 3: Add `SelfReviewSettings` to config.py (AC: #1-2)
  - [x] Settings class with env prefix `SELF_REVIEW__`
  - [x] Add to `Settings` root class
- [x] Task 4: Implement CLI `review` command (AC: #7)
  - [x] `src/quote_agent/cli/review.py` — follows reason.py pattern
  - [x] Pipeline: classify → reason → score → route → self-review
  - [x] Display: review verdict (approved/rejected), validation steps with pass/fail, failure reasons, anomaly flags
  - [x] `--json` output flag
  - [x] Register in `cli/main.py`
- [x] Task 5: Write unit tests for self-review node (AC: #1-6)
  - [x] Test catalog validation: all products exist → pass
  - [x] Test catalog validation: hallucinated product (fake ID) → fail
  - [x] Test quantity plausibility: normal quantities → pass
  - [x] Test quantity plausibility: zero/negative/extreme → fail
  - [x] Test coherence validation: coherent match → pass
  - [x] Test coherence validation: incoherent (products don't match request intent) → fail
  - [x] Test output integrity: clean output → pass
  - [x] Test output integrity: injection-influenced output detected → fail + anomaly flag
  - [x] Test aggregate: one step fails → approved=False
  - [x] Test aggregate: all steps pass → approved=True
  - [x] Test timeout/error fallback: LLM error → approved=False with fallback reason
  - [x] Test validation steps recorded with durations
- [x] Task 6: Write unit tests for CLI command (AC: #7)
  - [x] Test formatted output (approved case)
  - [x] Test formatted output (rejected case with failure reasons)
  - [x] Test JSON output
  - [x] Test error handling
- [x] Task 7: Quality gates — ruff, mypy --strict, all tests passing

## Dev Notes

### Architecture & Constraints

- **New file**: `src/quote_agent/agent/nodes/self_reviewer.py`
- Do NOT create `graph.py` or `state.py` — those come in Story 4.8
- The self-review node is a **quality gate** positioned after reasoning+scoring in the pipeline, before any draft creation (Story 4.7)
- It does NOT create or modify quotes — it validates the reasoning output and returns a pass/fail verdict
- The node needs access to the database (to verify product existence) and the LLM (for coherence + integrity checks)

### Node Function Signature

Follow the established pattern from reasoning_strategy.py (which also takes search engine as dependency):

```python
async def self_review(
    reasoning_result: ReasoningResult,
    request: ExtractedQuoteRequest,
    llm_adapter: OpenAICompatAdapter,
    session: AsyncSession,
) -> SelfReviewResult:
```

Takes an `AsyncSession` (not the search engine) because catalog validation is a direct DB lookup, not a search operation. Import `AsyncSession` from `sqlalchemy.ext.asyncio`.

### Catalog Validation (Anti-Hallucination)

This is the most critical validation. The search results in `ReasoningResult.search_result.results` contain `ScoredProduct` objects with `product_id` (UUID). Validate by querying the `products` table:

```python
from quote_agent.models.product import Product

stmt = select(Product.id).where(Product.id.in_(product_ids))
result = await session.execute(stmt)
existing_ids = {row[0] for row in result.fetchall()}
```

Any product ID not found in `existing_ids` is a hallucination — fail the review.

### Quantity Plausibility

Check `request.line_items[*].quantity`:
- Must be positive (> 0) if present
- Must be below a configurable max (e.g., 1_000_000 — configurable via `SelfReviewSettings.max_quantity`)
- `None` quantity is acceptable (not all requests specify quantity)

This is a pure validation — no LLM call needed.

### Coherence Validation (LLM)

Use LLM structured output to validate that the top matched products are coherent with the original request:

```python
model = llm_adapter.get_model("simple")
structured = model.with_structured_output(CoherenceCheckResult)
result = await asyncio.wait_for(structured.ainvoke(messages), timeout=settings.self_review.timeout_seconds)
```

The LLM receives:
- The original request description (in UNTRUSTED delimiters)
- The top matched products (names, references, categories)
- Task: "Are these products coherent with what was requested? Flag any mismatches."

Output model:
```python
class CoherenceCheckResult(BaseModel):
    is_coherent: bool
    mismatches: list[str] = Field(default_factory=list)
    reasoning: str
```

### Output Integrity (Prompt Injection Layer 3)

Second LLM call to validate that the output doesn't show signs of prompt injection influence:

```python
class IntegrityCheckResult(BaseModel):
    is_clean: bool
    anomalies: list[str] = Field(default_factory=list)
    reasoning: str
```

The LLM receives the reasoning trace and matched products and checks for:
- Products that seem unrelated to industrial supply
- Unusual patterns in product names/descriptions that could indicate injection
- Output that contradicts system behavior expectations

### LLM Structured Output Pattern

Same as all other nodes:
```python
from quote_agent.config import get_settings
settings = get_settings()

model = llm_adapter.get_model("simple")
structured = model.with_structured_output(SomeOutputModel)
result = await asyncio.wait_for(structured.ainvoke(messages), timeout=settings.self_review.timeout_seconds)
```

### Input Isolation (Security Layer 2)

All LLM calls must wrap untrusted content with delimiters:
```
<<<UNTRUSTED_QUOTE_REQUEST_START>>>
{request content}
<<<UNTRUSTED_QUOTE_REQUEST_END>>>
```

### Error Handling / Fallback

- On timeout or LLM error during coherence/integrity checks → `approved=False` (fail-safe: reject on error)
- Catch `LLMTimeoutError`, `AdapterError`, `TimeoutError` specifically
- Record the error as a validation step: step_name="error", passed=False, detail=error message
- This is **different from reasoning_strategy.py** which falls back to a simpler strategy — self-review must be fail-safe (reject on error, don't approve on error)

### Mock Pattern for Tests

Follow the exact pattern from `test_confidence_scorer.py`:

```python
def _make_adapter_mock(result):
    mock_structured = AsyncMock()
    mock_structured.ainvoke = AsyncMock(return_value=result)
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured)
    mock_adapter = MagicMock()
    mock_adapter.get_model = MagicMock(return_value=mock_model)
    return mock_adapter
```

For the database session mock (catalog validation):
```python
mock_session = AsyncMock()
mock_result = MagicMock()
mock_result.fetchall = MagicMock(return_value=[(uuid1,), (uuid2,)])
mock_session.execute = AsyncMock(return_value=mock_result)
```

Settings mock: patch `"quote_agent.config.get_settings"` (local import in the node function).

### CLI Pipeline

The `review` command runs the full pipeline with self-review as the final gate:
1. Build `ExtractedQuoteRequest` from CLI args
2. Classify (reuses `classify_request`)
3. Reason (calls `apply_reasoning_strategy` — does search internally)
4. Score confidence
5. Route
6. **Self-review** (validates the reasoning output)

This extends the `reason` pipeline by appending the self-review step. Reuse `_run_reason()` from `reason.py` to avoid duplication, then call `self_review()` on the result.

### Project Structure Notes

- New files follow existing naming and location patterns
- `src/quote_agent/agent/nodes/self_reviewer.py` — mirrors `confidence_scorer.py`, `reasoning_strategy.py`
- `src/quote_agent/cli/review.py` — mirrors `reason.py`
- `tests/unit/agent/test_self_reviewer.py` — mirrors `test_confidence_scorer.py`
- `tests/unit/test_cli_review.py` — mirrors `test_cli_reason.py`
- `from __future__ import annotations` required in all new files
- Absolute imports only

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.4]
- [Source: _bmad-output/planning-artifacts/prd.md — FR24, FR25, FR26, FR27]
- [Source: _bmad-output/planning-artifacts/architecture.md — Self-reviewer node, 3-layer prompt injection defense, Agent nodes structure]
- [Source: docs/project-context.md — Established patterns, LLM structured output, Input isolation, Config pattern, Security layer pattern]
- [Source: src/quote_agent/agent/nodes/confidence_scorer.py — Node function pattern, mock pattern]
- [Source: src/quote_agent/agent/nodes/reasoning_strategy.py — Node with DB/search dependency, ReasoningResult DTO]
- [Source: src/quote_agent/agent/nodes/router.py — Pure routing function, RoutingDecision DTO]
- [Source: src/quote_agent/cli/reason.py — CLI pipeline pattern, _run_reason() reuse]
- [Source: src/quote_agent/config.py — Settings pattern (ReasoningSettings as model)]
- [Source: src/quote_agent/models/product.py — Product model for catalog validation]
- [Source: src/quote_agent/exceptions.py — AdapterError, LLMTimeoutError]

### Previous Story Intelligence (4.3)

- Mock pattern: `_make_adapter_mock(result)` creates mock adapter → model → structured → ainvoke
- Patch path for settings: `"quote_agent.config.get_settings"` (local import in node function)
- 453 unit tests passing before this story
- `from __future__ import annotations` required in all src/ files
- `asyncio_mode = "auto"` in pytest — no manual @pytest.mark.asyncio needed
- `fallback_complexity` / `fallback_tier` must be typed as `Literal` not `str`
- Pydantic forward reference: if a DTO from another module is used as a Pydantic field, it must be runtime-imported (not TYPE_CHECKING only)
- Input isolation delimiters: `<<<UNTRUSTED_QUOTE_REQUEST_START>>>` / `<<<UNTRUSTED_QUOTE_REQUEST_END>>>`
- `SearchResult` and `ExtractedQuoteRequest` must be runtime-imported when used as Pydantic fields
- Variable shadowing: avoid reusing import names as loop variables (e.g., `step` in a loop vs `ReasoningStep`)

### Git Intelligence

Recent commits (Stories 4.1-4.3):
- `0d8f076` feat: add adaptive reasoning strategies with CLI command (Story 4.3)
- `b4ac30d` feat: add confidence scoring node and tier routing with CLI command (Story 4.2)
- `bbd8cc2` feat: add request complexity classifier node with CLI command (Story 4.1)
- Pattern: each story adds a node file, a CLI file, and corresponding unit tests
- Config settings added to `config.py` and `Settings` root class
- CLI commands registered in `main.py` with wrapper pattern (lazy imports)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Implemented `self_review()` async function with 4 validation steps: catalog existence (DB lookup), quantity plausibility (pure validation), coherence (LLM structured output), output integrity (LLM prompt injection layer 3)
- DTOs: `ValidationStep`, `SelfReviewResult`, `CoherenceCheckResult`, `IntegrityCheckResult` in `self_reviewer.py`; `SelfReviewSettings` in `config.py`
- CLI `review` command reuses `_run_reason()` from `reason.py` then appends self-review step
- Fail-safe design: any error (timeout, LLM failure, DB error) results in `approved=False`
- Input isolation delimiters applied to coherence LLM call; integrity check validates reasoning trace
- 18 unit tests for self-review node covering all ACs, 6 unit tests for CLI command
- 478 total tests passing (454 before + 24 new), 0 regressions
- ruff clean, mypy --strict clean on all new files

### File List

- src/quote_agent/agent/nodes/self_reviewer.py (new)
- src/quote_agent/cli/review.py (new)
- src/quote_agent/cli/main.py (modified — added review command)
- src/quote_agent/config.py (modified — added SelfReviewSettings)
- tests/unit/agent/test_self_reviewer.py (new)
- tests/unit/test_cli_review.py (new)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified — story status tracking)

### Change Log

- 2026-03-21: Story 4.4 implemented — self-review node with 4 validation steps, CLI command, 24 unit tests, all quality gates passing
- 2026-03-21: Code review fix — added sprint-status.yaml to File List, corrected test count in Completion Notes (24 new, not 25)
