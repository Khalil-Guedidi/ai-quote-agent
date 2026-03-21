# Story 4.3: Stratégies de Raisonnement Adaptatives

Status: done

## Story

As a **sales rep (Sophie)**,
I want the agent to apply different reasoning strategies based on request complexity,
So that simple requests are processed efficiently while complex ones get deeper analysis.

## Acceptance Criteria

1. **AC-1: Simple → Direct Match Strategy** — Given a "simple" classified request, when the reasoning strategy runs, then it applies a direct match strategy (search → top result → confidence check) and uses the lighter LLM model (`get_model("simple")`).

2. **AC-2: Ambiguous → Exploration Strategy** — Given an "ambiguous" classified request, when the reasoning strategy runs, then it applies an exploration strategy (broader search → multiple candidates → comparative scoring) and uses the more capable LLM model (`get_model("complex")`).

3. **AC-3: Complex → Deep Analysis Strategy** — Given a "complex" classified request, when the reasoning strategy runs, then it applies a deep analysis strategy (search + context enrichment + multi-step reasoning) and the reasoning trace documents each step taken.

4. **AC-4: Out-of-scope Passthrough** — Given an "out_of_scope" classified request, when the reasoning strategy runs, then it skips reasoning entirely and returns an empty result flagged for notification (no LLM call, no search).

5. **AC-5: Reasoning Trace** — For all strategies, each reasoning step is recorded as a `ReasoningStep` in the output, including step name, duration, and outcome.

6. **AC-6: CLI Command** — A `uv run quote-agent reason "description"` command runs the full pipeline (classify → search → reason → score → route) and displays the strategy used, reasoning steps, and final result.

## Tasks / Subtasks

- [x] Task 1: Create DTOs (AC: #1-5)
  - [x]`ReasoningStep` model — step_name, description, duration_ms, outcome
  - [x]`ReasoningResult` model — strategy (Literal["direct_match", "exploration", "deep_analysis", "out_of_scope_skip"]), steps (list[ReasoningStep]), enriched_request (ExtractedQuoteRequest | None), search_result (SearchResult), reasoning_duration_ms
  - [x]`ReasoningSettings` config — timeout_seconds, simple_search_limit, ambiguous_search_limit, complex_search_limit, fallback_strategy
- [x] Task 2: Implement `apply_reasoning_strategy()` async function (AC: #1-5)
  - [x]Route to strategy function based on `classification.complexity`
  - [x]Simple: `_direct_match_strategy()` — single search with default limit, return top result
  - [x]Ambiguous: `_exploration_strategy()` — broader search (higher limit), LLM-powered comparative analysis of candidates
  - [x]Complex: `_deep_analysis_strategy()` — broad search + LLM context enrichment (reformulate vague descriptions, resolve implicit references) + multi-step reasoning
  - [x]Out-of-scope: return immediately with empty search result and skip flag
  - [x]Input isolation delimiters on all LLM calls
- [x] Task 3: Add `ReasoningSettings` to config.py (AC: #1-3)
  - [x]Settings class with env prefix `REASONING__`
  - [x]Add to `Settings` root class
- [x] Task 4: Implement CLI `reason` command (AC: #6)
  - [x]`src/quote_agent/cli/reason.py` — follows score.py pattern
  - [x]Pipeline: classify → reason (which does search internally) → score → route
  - [x]Display: strategy name, reasoning steps with durations, then confidence + routing result
  - [x]`--json` output flag
  - [x]Register in `cli/main.py`
- [x] Task 5: Write unit tests for reasoning node (AC: #1-5)
  - [x]Test each strategy independently: simple, ambiguous, complex, out-of-scope
  - [x]Test timeout/error fallback behavior
  - [x]Test reasoning trace completeness (every step captured)
  - [x]Test input isolation delimiters in prompts
  - [x]Test model selection (simple strategies use simple model, complex use complex model)
- [x] Task 6: Write unit tests for CLI command (AC: #6)
  - [x]Test formatted output and JSON output
  - [x]Test error handling
- [x] Task 7: Quality gates — ruff, mypy --strict, all tests passing

## Dev Notes

### Architecture & Constraints

- **New file**: `src/quote_agent/agent/nodes/reasoning_strategy.py`
- Do NOT create `graph.py` or `state.py` — those come in Story 4.8
- The reasoning node **owns the search call** — it decides search parameters (limit, strategy) based on complexity, then returns the SearchResult alongside enriched context
- For simple strategy: search is straightforward (limit=5 or configurable), no LLM enrichment
- For ambiguous: search with higher limit (e.g., 10), then LLM compares candidates and identifies best matches
- For complex: search with high limit, then LLM enriches the request (reformulates vague parts, extracts implicit requirements), potentially re-searches with refined query
- Use `adapter.get_model("simple")` for simple strategy, `adapter.get_model("complex")` for ambiguous and complex strategies (FR16)

### Node Function Signature

Follow the established pattern from classifier.py and confidence_scorer.py:

```python
async def apply_reasoning_strategy(
    classification: ClassificationResult,
    request: ExtractedQuoteRequest,
    llm_adapter: OpenAICompatAdapter,
    search_engine: HybridSearchEngine,
) -> ReasoningResult:
```

The function takes the search engine as a dependency (unlike classifier/scorer which are LLM-only). This is because the reasoning strategy controls HOW search is performed.

### LLM Structured Output Pattern

```python
from quote_agent.config import get_settings
settings = get_settings()

model = llm_adapter.get_model("simple")  # or "complex"
structured = model.with_structured_output(SomeOutputModel)
result = await asyncio.wait_for(structured.ainvoke(messages), timeout=settings.reasoning.timeout_seconds)
```

### Input Isolation (Security Layer 2)

All LLM calls must wrap untrusted content with delimiters:
```
<<<UNTRUSTED_QUOTE_REQUEST_START>>>
{request content}
<<<UNTRUSTED_QUOTE_REQUEST_END>>>
```

### Strategy Details

**Direct Match (simple):**
1. Build `SearchRequest(query=description, limit=simple_search_limit)` from first line item
2. Execute hybrid search
3. Record step: "search" with duration and result count
4. Return results — no LLM enrichment needed

**Exploration (ambiguous):**
1. Build `SearchRequest` with higher limit (`ambiguous_search_limit`)
2. Execute hybrid search
3. Record step: "broad_search"
4. LLM comparative analysis: present top candidates, ask LLM to evaluate which ones best match the vague request, explain reasoning
5. Record step: "comparative_analysis" with LLM reasoning
6. Return results with comparative analysis in reasoning trace

**Deep Analysis (complex):**
1. LLM context enrichment: reformulate vague descriptions, resolve implicit references ("like last time" → needs client context in future, for now flag it), extract specifications
2. Record step: "context_enrichment"
3. Build `SearchRequest` with high limit (`complex_search_limit`)
4. Execute hybrid search using enriched/reformulated query
5. Record step: "enriched_search"
6. LLM multi-step reasoning: evaluate matches against complex requirements, check specifications alignment
7. Record step: "deep_evaluation"
8. Return results with full reasoning chain

### Error Handling / Fallback

- On timeout or LLM error → fall back to direct_match strategy (just do the search without LLM enrichment)
- Catch `LLMTimeoutError`, `AdapterError`, `TimeoutError` specifically
- Record the fallback as a reasoning step: "fallback" with error reason
- Fallback strategy configurable via `ReasoningSettings.fallback_strategy`

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

For the search engine mock:
```python
mock_engine = AsyncMock()
mock_engine.search_hybrid = AsyncMock(return_value=mock_search_result)
```

Settings mock: patch `"quote_agent.config.get_settings"` (local import in the node function).

### CLI Pipeline

The `reason` command runs the full pipeline with reasoning as the centerpiece:
1. Build `ExtractedQuoteRequest` from CLI args
2. Classify (reuses `classify_request`)
3. **Reason** (calls `apply_reasoning_strategy` — does search internally, returns `ReasoningResult`)
4. Score confidence on the reasoning result's search results
5. Route based on confidence

This extends the `score` pipeline by inserting the reasoning step between classify and score.

### Project Structure Notes

- New files follow existing naming and location patterns
- `src/quote_agent/agent/nodes/reasoning_strategy.py` — mirrors `classifier.py`, `confidence_scorer.py`
- `src/quote_agent/cli/reason.py` — mirrors `score.py`
- `tests/unit/agent/test_reasoning_strategy.py` — mirrors `test_confidence_scorer.py`
- `tests/unit/test_cli_reason.py` — mirrors `test_cli_score.py`
- `from __future__ import annotations` required in all new files
- Absolute imports only

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.3]
- [Source: _bmad-output/planning-artifacts/prd.md — FR12, FR16]
- [Source: _bmad-output/planning-artifacts/architecture.md — Agent nodes structure, LLM adapter pattern, Data flow]
- [Source: docs/project-context.md — Established patterns, LLM structured output, Input isolation, Config pattern]
- [Source: src/quote_agent/agent/nodes/classifier.py — Node function pattern]
- [Source: src/quote_agent/agent/nodes/confidence_scorer.py — Scoring pattern, mock pattern]
- [Source: src/quote_agent/agent/nodes/router.py — Pure routing function]
- [Source: src/quote_agent/cli/score.py — CLI pipeline pattern]
- [Source: src/quote_agent/config.py — Settings pattern (ClassificationSettings, ConfidenceScoringSettings)]

### Previous Story Intelligence (4.2)

- Mock pattern: `_make_adapter_mock(result)` creates mock adapter → model → structured → ainvoke
- Patch path for settings: `"quote_agent.config.get_settings"` (local import in node function)
- 414 unit tests passing before this story
- `from __future__ import annotations` required in all src/ files
- `asyncio_mode = "auto"` in pytest — no manual @pytest.mark.asyncio needed
- `fallback_complexity` / `fallback_tier` must be typed as `Literal` not `str`
- Pydantic forward reference: if a DTO from another module is used as a Pydantic field, it must be runtime-imported (not TYPE_CHECKING only)
- Input isolation delimiters: `<<<UNTRUSTED_QUOTE_REQUEST_START>>>` / `<<<UNTRUSTED_QUOTE_REQUEST_END>>>`

### Git Intelligence

Recent commits (Stories 4.1, 4.2):
- `b4ac30d` feat: add confidence scoring node and tier routing with CLI command (Story 4.2)
- `bbd8cc2` feat: add request complexity classifier node with CLI command (Story 4.1)
- Pattern: each story adds a node file, a CLI file, and corresponding unit tests
- Config settings added to `config.py` and `Settings` root class

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Pydantic forward reference: `SearchResult` and `ExtractedQuoteRequest` must be runtime-imported (not TYPE_CHECKING only) because they are used as Pydantic fields in `ReasoningResult`
- Variable shadowing: `step` variable in CLI `_format_result` escalation loop shadowed `ReasoningStep` import; renamed to `next_step`
- `SearchResult` local import alias needed in `apply_reasoning_strategy` to avoid conflict with runtime import at module level

### Completion Notes List

- Implemented 4 reasoning strategies: direct_match (simple), exploration (ambiguous), deep_analysis (complex), out_of_scope_skip
- Simple strategy: search only, no LLM call, uses `get_model("simple")` not called
- Ambiguous strategy: broad search + LLM comparative analysis, uses `get_model("complex")`
- Complex strategy: LLM context enrichment + enriched search + LLM deep evaluation, uses `get_model("complex")`
- Out-of-scope: immediate return with empty result, no search or LLM call
- Fallback: on TimeoutError/LLMTimeoutError/AdapterError, falls back to direct_match strategy
- All LLM calls use input isolation delimiters (<<<UNTRUSTED_QUOTE_REQUEST_START/END>>>)
- ReasoningSettings added to config.py with `REASONING__` env prefix
- CLI `reason` command: classify → reason → score → route pipeline with --json flag
- 39 new tests (28 reasoning node + 11 CLI), all passing
- Full test suite: 453 tests, 0 failures
- ruff clean, mypy --strict zero issues

### File List

- `src/quote_agent/agent/nodes/reasoning_strategy.py` (new) — reasoning node with DTOs and 4 strategy functions
- `src/quote_agent/cli/reason.py` (new) — CLI reason command
- `src/quote_agent/cli/main.py` (modified) — registered reason command
- `src/quote_agent/config.py` (modified) — added ReasoningSettings class and reasoning field to Settings
- `tests/unit/agent/test_reasoning_strategy.py` (new) — 28 unit tests for reasoning node
- `tests/unit/test_cli_reason.py` (new) — 11 unit tests for CLI reason command

### Change Log

- 2026-03-21: Story 4.3 implementation complete — adaptive reasoning strategies with CLI command
- 2026-03-21: Code review fixes — (H1) `--json` suppresses intermediate prints, (M1) removed dead `fallback_strategy` config, (M2) added deep analysis input isolation test
