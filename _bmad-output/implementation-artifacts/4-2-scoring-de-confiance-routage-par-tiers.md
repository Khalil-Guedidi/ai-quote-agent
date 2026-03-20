# Story 4.2: Scoring de Confiance & Routage par Tiers

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to calculate a confidence score for each match and route decisions accordingly,
so that high-confidence quotes go straight to review while uncertain ones come with options or context.

## Acceptance Criteria

1. **Given** a product match with high confidence (>85%)
   **When** routing runs
   **Then** the request proceeds to draft quote creation
   **And** the confidence score and reasoning are recorded in the trace

2. **Given** a product match with medium confidence (50-85%)
   **When** routing runs
   **Then** the agent generates 2-5 alternative proposals (FR8)
   **And** each proposal includes its own confidence score and brief reasoning

3. **Given** a match with low confidence (<50%)
   **When** routing runs
   **Then** the request is escalated to the sales rep with enriched context
   **And** the context includes: what was understood, what was uncertain, and suggested next steps

4. **Given** an out-of-scope classification
   **When** routing runs
   **Then** the sales rep is notified with an explanation of why the request is out of scope (FR15)

## Tasks / Subtasks

- [x] Task 1: Create confidence scoring Pydantic DTOs (AC: #1, #2, #3)
  - [x] 1.1 Create `src/quote_agent/agent/nodes/confidence_scorer.py` with `ConfidenceResult` model: `overall_confidence` (float, 0.0-1.0), `tier` (Literal["high", "medium", "low"]), `product_scores` (list[ProductConfidence]), `reasoning` (list[str]), `scoring_duration_ms` (int)
  - [x] 1.2 Create `ProductConfidence` model: `product_id` (UUID), `reference` (str), `name` (str), `confidence` (float, 0.0-1.0), `match_quality` (str — brief reason why this score), `rank` (int)
  - [x] 1.3 Create `ScoringInput` model wrapping: `ClassificationResult` (from classifier), `SearchResult` (from search), `ExtractedQuoteRequest` (original request). Provide `from_components()` classmethod.

- [x] Task 2: Implement the confidence scorer node function (AC: #1, #2, #3)
  - [x] 2.1 Implement `async def score_confidence(classification: ClassificationResult, search_result: SearchResult, request: ExtractedQuoteRequest, llm_adapter: OpenAICompatAdapter) -> ConfidenceResult`
  - [x] 2.2 Use `model.with_structured_output(ConfidenceResult)` pattern (same as classifier)
  - [x] 2.3 Wrap with `asyncio.wait_for(..., timeout=settings.confidence_scoring.timeout_seconds)`
  - [x] 2.4 Use `llm_adapter.get_model("simple")` — scoring is a lightweight structured output task
  - [x] 2.5 Catch `LLMTimeoutError` and `AdapterError`, return fallback result with tier="low" and confidence=0.0 (safe default — triggers escalation)
  - [x] 2.6 Track `scoring_duration_ms` via `time.monotonic()`

- [x] Task 3: Design the confidence scoring prompt (AC: #1, #2, #3)
  - [x] 3.1 System prompt instructs the LLM to:
    - Evaluate how well each search result matches the original request (description, quantity, specs, reference)
    - Assign per-product confidence (0.0-1.0) based on: name/description semantic match, reference match, specification compatibility, category relevance
    - Compute overall confidence as the weighted max of product confidences (best match drives the decision)
    - Provide reasoning for each score (brief, actionable)
  - [x] 3.2 Include classification context: if "ambiguous" → stricter scoring; if "simple" → straightforward match logic
  - [x] 3.3 Apply input isolation: wrap user-originated content (request description, line items) in `<<<UNTRUSTED_QUOTE_REQUEST_START>>>` / `<<<UNTRUSTED_QUOTE_REQUEST_END>>>` delimiters
  - [x] 3.4 Prompt language: French (consistent with classifier and target market)

- [x] Task 4: Create routing Pydantic DTOs and router function (AC: #1, #2, #3, #4)
  - [x] 4.1 Create `src/quote_agent/agent/nodes/router.py` with `RoutingDecision` model: `action` (Literal["proceed_to_draft", "generate_proposals", "escalate", "notify_out_of_scope"]), `tier` (Literal["high", "medium", "low", "out_of_scope"]), `confidence` (float), `proposals` (list[ProductConfidence] — top 2-5 for medium tier), `escalation_context` (EscalationContext | None)
  - [x] 4.2 Create `EscalationContext` model: `understood` (str — what was understood from the request), `uncertain` (str — what was unclear or ambiguous), `suggested_next_steps` (list[str])
  - [x] 4.3 Implement `def route_by_confidence(confidence_result: ConfidenceResult, classification: ClassificationResult, settings: ConfidenceScoringSettings) -> RoutingDecision` — pure function, no LLM call, deterministic routing based on thresholds:
    - `classification.complexity == "out_of_scope"` → `notify_out_of_scope` (regardless of confidence)
    - `overall_confidence > high_threshold` (default 0.85) → `proceed_to_draft`
    - `overall_confidence >= low_threshold` (default 0.50) → `generate_proposals` (include top 2-5 products from `product_scores`)
    - `overall_confidence < low_threshold` → `escalate`
  - [x] 4.4 For `escalate` action: build `EscalationContext` from the classification reasons + scoring reasoning (what was understood, what was uncertain, suggested next steps)
  - [x] 4.5 For `generate_proposals`: select top 2-5 products from `confidence_result.product_scores` where `confidence > 0.0`, sorted by confidence descending

- [x] Task 5: Add ConfidenceScoringSettings to config (AC: #1, #2, #3)
  - [x] 5.1 Create `ConfidenceScoringSettings` in `config.py` with env prefix `CONFIDENCE_SCORING__`
  - [x] 5.2 Fields: `timeout_seconds: int = 10`, `high_threshold: float = 0.85`, `low_threshold: float = 0.50`, `max_proposals: int = 5`, `min_proposals: int = 2`, `fallback_tier: Literal["high", "medium", "low"] = "low"`
  - [x] 5.3 Add `confidence_scoring: ConfidenceScoringSettings = ConfidenceScoringSettings()` to `Settings` class

- [x] Task 6: Write unit tests — confidence scorer (AC: #1, #2, #3)
  - [x] 6.1 Create `tests/unit/agent/test_confidence_scorer.py`
  - [x] 6.2 Test high confidence result (>85%) returns tier="high"
  - [x] 6.3 Test medium confidence result (50-85%) returns tier="medium"
  - [x] 6.4 Test low confidence result (<50%) returns tier="low"
  - [x] 6.5 Test timeout fallback returns tier="low" with confidence=0.0
  - [x] 6.6 Test AdapterError fallback returns tier="low" with confidence=0.0
  - [x] 6.7 Test scoring_duration_ms is populated
  - [x] 6.8 Test input isolation delimiters are present in the prompt sent to LLM
  - [x] 6.9 Test that classification context influences scoring (ambiguous → scoring considers multiple alternatives)

- [x] Task 7: Write unit tests — router (AC: #1, #2, #3, #4)
  - [x] 7.1 Create `tests/unit/agent/test_router.py`
  - [x] 7.2 Test high confidence (>0.85) → action="proceed_to_draft"
  - [x] 7.3 Test medium confidence (0.50-0.85) → action="generate_proposals" with 2-5 proposals
  - [x] 7.4 Test low confidence (<0.50) → action="escalate" with EscalationContext populated
  - [x] 7.5 Test out-of-scope classification → action="notify_out_of_scope" regardless of confidence
  - [x] 7.6 Test proposals are sorted by confidence descending, limited to max_proposals
  - [x] 7.7 Test proposals minimum count: if fewer than min_proposals products available, include all
  - [x] 7.8 Test escalation context includes: understood, uncertain, suggested_next_steps
  - [x] 7.9 Test custom thresholds via settings override (e.g., high_threshold=0.90)
  - [x] 7.10 Test boundary values: exactly 0.85 → medium (not high), exactly 0.50 → medium (not low)

- [x] Task 8: Add CLI `score` command for manual testing (AC: #1, #2, #3, #4)
  - [x] 8.1 Add `score` subcommand to `src/quote_agent/cli/score.py` (follow `classify.py` pattern)
  - [x] 8.2 Accept: text description (positional), optional `--quantity`, `--reference`, `--urgency`, `--limit` (search results count, default 5)
  - [x] 8.3 Pipeline: classify request → search products → score confidence → route → display
  - [x] 8.4 Display: classification, search results summary, per-product confidence, overall confidence, tier, routing decision, escalation context if applicable
  - [x] 8.5 Support `--json` output mode
  - [x] 8.6 Use lazy imports for ML/LLM deps (same pattern as classify.py)
  - [x] 8.7 Write unit tests in `tests/unit/test_cli_score.py` (mock the pipeline, test display formatting)

- [x] Task 9: Validate CI passes
  - [x] 9.1 `ruff check` clean
  - [x] 9.2 `mypy --strict` clean (no new errors)
  - [x] 9.3 All unit tests pass (`pytest tests/unit/`)

## Dev Notes

### Context: Second Agent Node + First Router

This story creates **two new agent nodes**: `confidence_scorer.py` (LLM-powered scoring) and `router.py` (deterministic routing logic). The scorer is an LLM node (like classifier). The router is a **pure function** — no LLM call, just threshold-based branching. Both will be wired into the agent graph in Story 4.8.

**Do NOT create `graph.py` or `state.py` yet** — those come in Story 4.8 (Orchestration). These nodes are standalone async/sync functions, testable independently.

### Architecture Compliance

**File locations (from architecture.md):**
- Confidence scorer: `src/quote_agent/agent/nodes/confidence_scorer.py`
- Router: `src/quote_agent/agent/nodes/router.py`
- Unit tests: `tests/unit/agent/test_confidence_scorer.py`, `tests/unit/agent/test_router.py`
- CLI command: `src/quote_agent/cli/score.py`
- CLI tests: `tests/unit/test_cli_score.py`
- Config addition: `src/quote_agent/config.py`

**LLM call pattern (from project-context.md):**
```python
structured = model.with_structured_output(ConfidenceResult)
result = await asyncio.wait_for(
    structured.ainvoke(messages),
    timeout=settings.confidence_scoring.timeout_seconds,
)
```

**Model selection:** Use `llm_adapter.get_model("simple")` — confidence scoring is structured analysis of search results, not complex reasoning. The `simple_model` maps to `gpt-4o-mini` by default.

**Security:** Apply Layer 2 input isolation when injecting the original request text into the scoring prompt. The scorer receives content that was already sanitized by Layer 1 (`security/sanitizer.py`) during email processing. Wrap user content in `<<<UNTRUSTED_QUOTE_REQUEST_START>>>` / `<<<UNTRUSTED_QUOTE_REQUEST_END>>>` delimiters.

### Existing Code to Reuse

| Component | Location | Usage |
|-----------|----------|-------|
| LLM adapter factory | `adapters/llm/__init__.py` → `get_llm_adapter()` | Get configured LLM adapter |
| `get_model(complexity)` | `adapters/llm/openai_compat.py:51-57` | Returns ChatOpenAI for "simple"/"complex"/default |
| `with_structured_output` | LangChain pattern (used in `agent/nodes/classifier.py`) | Structured Pydantic output from LLM |
| `ClassificationResult` | `agent/nodes/classifier.py` | Input to scorer (complexity context) |
| `ExtractedQuoteRequest` | `services/extraction_models.py` | Original request data for scoring context |
| `SearchResult`, `ScoredProduct` | `search/models.py` | Search results to score against |
| Exception hierarchy | `exceptions.py` | `LLMTimeoutError`, `AdapterError` |
| Input isolation delimiters | `security/input_isolation.py` | `<<<UNTRUSTED_QUOTE_REQUEST_START>>>` pattern from classifier |
| CLI pattern | `cli/classify.py` | Lazy imports, `--json` flag, formatted output, `_run_*()` async runner |
| Config pattern | `config.py` | `ConfidenceScoringSettings` follows `ClassificationSettings` pattern |
| SearchEngine factory | `search/__init__.py` → `get_search_engine(session)` | For CLI pipeline (search before scoring) |
| DB session factory | `models/base.py` → `_get_session_factory()` | For CLI pipeline |

### Anti-Patterns to Avoid

- **Do NOT create `graph.py` or `state.py`** — those come in Story 4.8
- **Do NOT use `invoke()` from LLMAdapter** — use `get_model()` + `with_structured_output()` + `ainvoke()` directly (same as classifier)
- **Do NOT hardcode model names** — always use `get_model("simple")`
- **Do NOT hardcode thresholds** — all thresholds come from `ConfidenceScoringSettings` (high_threshold, low_threshold)
- **Do NOT make the router call the LLM** — routing is deterministic threshold-based logic, not LLM-powered
- **Do NOT add database schema changes** — scoring result is transient (stored in agent state in Story 4.8)
- **Do NOT replace `_compute_extraction_confidence()` in `email_extractor.py`** — that placeholder heuristic serves a different purpose (extraction quality). Story 4.2's confidence scoring operates on product match quality
- **Do NOT add `from __future__ import annotations` to test files** — only needed in source files
- **Do NOT forget `from __future__ import annotations`** in all new `src/` files

### Previous Story Intelligence

**From Story 4.1 (Classification de Complexité des Demandes):**
- ClassificationResult model established: `complexity`, `reasons`, `confidence`, `classification_duration_ms`
- LLM structured output pattern works reliably with mock-based tests
- `_make_adapter_mock(result)` helper in tests: creates mock adapter → mock model → mock structured → ainvoke returns result
- `_mock_settings` fixture patches `quote_agent.config.get_settings` (not module-level — local import in node function)
- 375 unit tests currently passing
- Patch path for settings: `"quote_agent.config.get_settings"` (local import in classify_request, same pattern will apply to score_confidence)
- `from __future__ import annotations` in all src/ files, not in test files
- Test naming: `test_{behavior}_when_{condition}()`
- `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed

**From Story 4.1 code review:**
- `fallback_complexity` typed as `Literal` instead of `str` — apply same pattern to `fallback_tier` in ConfidenceScoringSettings

### Git Intelligence

Recent commit pattern: `feat:` prefix for new features, story reference in parentheses.
Expected commit: `feat: add confidence scoring node and tier routing with CLI command (Story 4.2)`

### Testing Strategy

**Unit tests only** (no E2E for this story):

**Confidence scorer tests (`test_confidence_scorer.py`):**
- Mock LLM adapter entirely — `with_structured_output` returns mock that `ainvoke` returns pre-built `ConfidenceResult`
- Mock `get_settings` to provide `ConfidenceScoringSettings` values
- Provide synthetic `ClassificationResult`, `SearchResult`, `ExtractedQuoteRequest` as inputs
- Test scenarios: high/medium/low scoring, timeout fallback, error fallback, duration tracking, input isolation

**Router tests (`test_router.py`):**
- No mocking needed — `route_by_confidence` is a pure function
- Provide synthetic `ConfidenceResult` and `ClassificationResult` inputs
- Test all routing paths: high → proceed, medium → proposals, low → escalate, out_of_scope → notify
- Test boundary values (exactly 0.85, exactly 0.50)
- Test custom thresholds
- Test proposal selection logic (sort, min/max count)
- Test escalation context population

**CLI tests (`test_cli_score.py`):**
- Mock the entire pipeline (classify + search + score + route)
- Test display formatting, JSON output, error handling

### Project Structure Notes

- `agent/nodes/confidence_scorer.py` and `agent/nodes/router.py` follow architecture directory structure exactly
- `tests/unit/agent/` directory already exists (created in Story 4.1) — add `test_confidence_scorer.py` and `test_router.py`
- CLI follows existing `cli/` organization — `classify.py` as closest reference

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.2, lines 1070-1095]
- [Source: _bmad-output/planning-artifacts/prd.md — FR8 (multi-proposals), FR13 (confidence scoring), FR14 (tier routing), FR15 (out-of-scope notification)]
- [Source: _bmad-output/planning-artifacts/architecture.md — agent/nodes/confidence_scorer.py, agent/nodes/router.py, Data Flow diagram]
- [Source: docs/project-context.md — LLM Structured Output Pattern, Security Layer Pattern, Adapter Pattern]
- [Source: src/quote_agent/agent/nodes/classifier.py — ClassificationResult model, LLM call pattern, input isolation]
- [Source: src/quote_agent/search/models.py — SearchResult, ScoredProduct models]
- [Source: src/quote_agent/services/extraction_models.py — ExtractedQuoteRequest, QuoteLineItem]
- [Source: src/quote_agent/config.py — ClassificationSettings pattern, Settings root class]
- [Source: src/quote_agent/cli/classify.py — CLI command pattern reference]
- [Source: src/quote_agent/adapters/llm/openai_compat.py — get_model() method]
- [Source: tests/unit/agent/test_classifier.py — Mock patterns, test organization]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Fixed Pydantic forward reference error: `ProductConfidence` must be runtime-imported in `router.py` (not TYPE_CHECKING only) because Pydantic needs it for model field resolution even with `from __future__ import annotations`.

### Completion Notes List

- Task 5: Added `ConfidenceScoringSettings` to config.py with env prefix pattern, `Literal` typed `fallback_tier`
- Tasks 1-3: Implemented `confidence_scorer.py` with `ConfidenceResult`, `ProductConfidence`, `ScoringInput` DTOs, LLM structured output scoring, French prompt with input isolation, timeout/error fallback to tier="low"
- Task 4: Implemented `router.py` with `RoutingDecision`, `EscalationContext` DTOs, pure deterministic `route_by_confidence()` function with threshold-based routing
- Task 6: 15 unit tests for confidence scorer — high/medium/low tier, timeout/error fallback, duration tracking, input isolation delimiters, classification context influence, ScoringInput.from_components
- Task 7: 15 unit tests for router — all 4 routing paths, boundary values (0.85/0.50), custom thresholds, proposal sorting/limits, escalation context
- Task 8: CLI `score` command with full pipeline (classify→search→score→route), formatted and JSON output, 9 unit tests
- Task 9: ruff clean, mypy clean (pre-existing error in sentence_transformers.py unchanged), 414 unit tests passing (39 new)

### Change Log

- 2026-03-20: Story 4.2 implementation complete — confidence scoring node, tier router, CLI command, 39 new tests

### File List

**New files:**
- src/quote_agent/agent/nodes/confidence_scorer.py
- src/quote_agent/agent/nodes/router.py
- src/quote_agent/cli/score.py
- tests/unit/agent/test_confidence_scorer.py
- tests/unit/agent/test_router.py
- tests/unit/test_cli_score.py

**Modified files:**
- src/quote_agent/config.py (added ConfidenceScoringSettings)
- src/quote_agent/cli/main.py (added score command registration)
- _bmad-output/implementation-artifacts/sprint-status.yaml (status → review)
