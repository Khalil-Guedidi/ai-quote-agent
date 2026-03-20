# Story 4.1: Classification de Complexité des Demandes

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to classify each quote request by complexity (simple / ambiguous / complex / out-of-scope),
so that it applies the right reasoning strategy and I know upfront how much attention each request needs.

## Acceptance Criteria

1. **Given** an extracted quote request with clear product reference and quantity
   **When** the classification node runs
   **Then** it classifies the request as "simple"
   **And** classification completes within 5 seconds (NFR-P4)

2. **Given** a request with vague description ("like last time but longer")
   **When** classification runs
   **Then** it classifies as "ambiguous" with reasons documented in reasoning trace

3. **Given** a request involving multiple custom products with special conditions
   **When** classification runs
   **Then** it classifies as "complex"

4. **Given** a request for a service or product outside the company's catalog
   **When** classification runs
   **Then** it classifies as "out-of-scope" with an explanation of why

## Tasks / Subtasks

- [x] Task 1: Create classification Pydantic DTOs (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `src/quote_agent/agent/nodes/classifier.py` with `ClassificationResult` model: `complexity` (Literal["simple", "ambiguous", "complex", "out_of_scope"]), `reasons` (list[str]), `confidence` (float), `classification_duration_ms` (int)
  - [x] 1.2 Create `ClassificationInput` model wrapping relevant fields from `ExtractedQuoteRequest` + `QuoteLineItem` (description, quantity, unit, specifications, reference, urgency, notes)

- [x] Task 2: Implement the classifier node function (AC: #1, #2, #3, #4)
  - [x] 2.1 Implement `async def classify_request(request: ExtractedQuoteRequest, llm_adapter: OpenAICompatAdapter) -> ClassificationResult`
  - [x] 2.2 Use `model.with_structured_output(ClassificationResult)` pattern (same as `email_extractor.py`)
  - [x] 2.3 Wrap with `asyncio.wait_for(..., timeout=10.0)` for timeout protection
  - [x] 2.4 Use `llm_adapter.get_model("simple")` — classification is a lightweight task, use the `simple_model` (gpt-4o-mini by default)
  - [x] 2.5 Catch `LLMTimeoutError` and `AdapterError`, return a fallback classification of "complex" (safe default — triggers deeper analysis) with error reason logged

- [x] Task 3: Design the classification prompt (AC: #1, #2, #3, #4)
  - [x] 3.1 System prompt defines the 4 complexity tiers with clear decision criteria:
    - **simple**: Clear product reference OR well-specified description + quantity present + no special conditions
    - **ambiguous**: Vague description, missing key fields (quantity, specs), relative references ("like last time"), unclear product
    - **complex**: Multiple products with interdependencies, special conditions (custom specs, certifications, delivery constraints), large quantities requiring stock check
    - **out_of_scope**: Request for services (not products), products clearly outside industrial supply domain, non-quote-related emails
  - [x] 3.2 Prompt must instruct the LLM to explain WHY — `reasons` field must contain specific justifications
  - [x] 3.3 Use input isolation pattern: user content wrapped in `<<<UNTRUSTED_QUOTE_REQUEST_START>>>` / `<<<UNTRUSTED_QUOTE_REQUEST_END>>>` delimiters (Layer 2 defense, consistent with `security/input_isolation.py`)
  - [x] 3.4 Prompt language: French (target market, product catalog is in French)

- [x] Task 4: Add ClassificationSettings to config (AC: #1)
  - [x] 4.1 Create `ClassificationSettings` in `config.py` with env prefix `CLASSIFICATION__`
  - [x] 4.2 Fields: `timeout_seconds: int = 10`, `fallback_complexity: str = "complex"`
  - [x] 4.3 Add `classification: ClassificationSettings = ClassificationSettings()` to `Settings` class

- [x] Task 5: Write unit tests (AC: #1, #2, #3, #4)
  - [x] 5.1 Create `tests/unit/agent/test_classifier.py`
  - [x] 5.2 Test each complexity tier with mocked LLM (mock `with_structured_output` + `ainvoke`)
  - [x] 5.3 Test timeout fallback returns "complex"
  - [x] 5.4 Test `AdapterError` fallback returns "complex"
  - [x] 5.5 Test classification_duration_ms is populated
  - [x] 5.6 Test that input isolation delimiters are present in the prompt sent to LLM
  - [x] 5.7 Ensure `tests/unit/agent/` directory exists (create `conftest.py` if needed)

- [x] Task 6: Add CLI `classify` command for manual testing (AC: #1, #2, #3, #4)
  - [x] 6.1 Add `classify` subcommand to `src/quote_agent/cli/` (follow `search.py` pattern)
  - [x] 6.2 Accept a text description (positional arg) + optional `--quantity`, `--reference`, `--urgency` flags
  - [x] 6.3 Display: complexity, confidence, reasons, duration
  - [x] 6.4 Support `--json` output mode (same pattern as `search.py`)
  - [x] 6.5 Use lazy imports for ML/LLM deps (same pattern as `search.py`)
  - [x] 6.6 Write unit tests in `tests/unit/test_cli_classify.py`

- [x] Task 7: Validate CI passes
  - [x] 7.1 `ruff check` clean
  - [x] 7.2 `mypy --strict` clean (no new errors)
  - [x] 7.3 All unit tests pass (`pytest tests/unit/`)

## Dev Notes

### Context: First Agent Node

This is the **first LangGraph agent node** being built. The `agent/` directory currently has only empty `__init__.py` files in `agent/`, `agent/nodes/`, and `agent/tools/`. This story creates the first real node (`classifier.py`) that will later be wired into the full agent graph in Story 4.8.

**Do NOT create `graph.py` or `state.py` yet** — those come in Story 4.8 (Orchestration). This story only creates the classifier as a standalone async function that can be called independently and tested independently.

### Architecture Compliance

**File locations (from architecture.md):**
- Classifier node: `src/quote_agent/agent/nodes/classifier.py`
- Unit tests: `tests/unit/agent/test_classifier.py`
- CLI command: `src/quote_agent/cli/classify.py`
- Config addition: `src/quote_agent/config.py`

**LLM call pattern (from project-context.md):**
```python
structured = model.with_structured_output(ClassificationResult)
result = await asyncio.wait_for(
    structured.ainvoke(messages),
    timeout=settings.classification.timeout_seconds,
)
```

**Model selection:** Use `llm_adapter.get_model("simple")` — classification is a lightweight structured output task. The `simple_model` maps to `gpt-4o-mini` by default (see `LLMSettings.simple_model` in `config.py:33`). This aligns with FR16 (route requests to different LLM models based on complexity).

**Security:** Apply Layer 2 input isolation when injecting the quote request text into the LLM prompt. The classifier receives text that was already sanitized by Layer 1 (`security/sanitizer.py`) during email processing (Epic 2). But still wrap in delimiters for defense-in-depth.

### Existing Code to Reuse

| Component | Location | Usage |
|-----------|----------|-------|
| LLM adapter factory | `adapters/llm/__init__.py` → `get_llm_adapter()` | Get configured LLM adapter |
| `get_model(complexity)` | `adapters/llm/openai_compat.py:51-57` | Returns ChatOpenAI for "simple"/"complex"/default |
| `with_structured_output` | LangChain pattern (used in `services/email_extractor.py`) | Structured Pydantic output from LLM |
| `ExtractedQuoteRequest` | `services/extraction_models.py` | Input data for classification |
| `QuoteLineItem` | `services/extraction_models.py` | Line item details for classification signals |
| Exception hierarchy | `exceptions.py` | `LLMTimeoutError`, `AdapterError` |
| Input isolation | `security/input_isolation.py` | Delimiter pattern for untrusted content |
| CLI pattern | `cli/search.py` | Lazy imports, `--json` flag, formatted output |
| Config pattern | `config.py` | `ClassificationSettings` follows `SearchSettings` pattern |

### Anti-Patterns to Avoid

- **Do NOT create `graph.py` or `state.py`** — those come in Story 4.8
- **Do NOT use `invoke()` from LLMAdapter** — use `get_model()` + `with_structured_output()` + `ainvoke()` directly on the ChatOpenAI instance (same as extractor pattern)
- **Do NOT hardcode model names** — always use `get_model("simple")` which reads from config
- **Do NOT create a new adapter or Protocol** — the classifier is an agent node, not an adapter
- **Do NOT add database schema changes** — classification result is transient (stored in agent state later, not its own table)
- **Do NOT add `from __future__ import annotations` to test files** — only needed in source files with complex type annotations
- **Do NOT forget `from __future__ import annotations`** in all new `src/` files — required for deferred annotations

### Previous Story Intelligence

**From Story 4.0c (Résolution Dictionnaire Jargon):**
- Jargon dictionary fully removed — BGE-M3 handles all industrial jargon natively
- 353 unit tests currently pass
- `SearchResult` no longer has `jargon_expanded`/`expanded_query` fields
- Clean search module with no jargon dependencies

**From Story 4.0b (CLI Flux Testable Search):**
- CLI pattern established in `cli/search.py` — follow exact same pattern for `cli/classify.py`
- Lazy imports via `def _get_*():` functions for ML/LLM dependencies
- `--json` flag for machine-readable output
- Test pattern for CLI in `tests/unit/test_cli_search.py`

**From Story 4.0a (Fix CI/CD):**
- ML deps isolated to `[dependency-groups] ml` — `uv sync --locked --no-group ml` for CI
- LLM deps available in CI (langchain, langchain-openai are in main deps, not ml group)
- PostgreSQL + pgvector service container in GitHub Actions

### Git Intelligence

Recent commit pattern: `feat:` prefix for new features, story reference in parentheses.
Expected commit: `feat: add request complexity classifier node with CLI command (Story 4.1)`

### Testing Strategy

**Unit tests only** (no E2E for this story):
- Mock the LLM adapter entirely — `with_structured_output` returns mock that `ainvoke` returns a pre-built `ClassificationResult`
- Follow `test_{behavior}_when_{condition}()` naming
- Use `pytest-asyncio` with `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed)
- Create `tests/unit/agent/` directory if it doesn't exist (may need `__init__.py`)
- CLI tests mock the classifier function entirely (test display formatting, not LLM logic)

**Test scenarios:**
1. Simple request: clear reference + quantity → "simple"
2. Ambiguous request: vague description, no quantity → "ambiguous"
3. Complex request: multiple items, special conditions → "complex"
4. Out-of-scope: service request → "out_of_scope"
5. LLM timeout → fallback to "complex"
6. LLM error → fallback to "complex"
7. Duration tracking populates `classification_duration_ms`
8. Input isolation delimiters in prompt

### Project Structure Notes

- Alignment with architecture: `agent/nodes/classifier.py` exactly matches architecture directory structure
- New `tests/unit/agent/` directory mirrors source structure — add `__init__.py`
- CLI follows existing `cli/` organization — `search.py` as reference implementation

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.1, lines 1045-1068]
- [Source: _bmad-output/planning-artifacts/prd.md — FR11 (classification), FR16 (model routing)]
- [Source: _bmad-output/planning-artifacts/architecture.md — agent/nodes/classifier.py, Data Flow diagram]
- [Source: docs/project-context.md — LLM Structured Output Pattern, Security Layer Pattern]
- [Source: src/quote_agent/adapters/llm/openai_compat.py — get_model() method, lines 51-57]
- [Source: src/quote_agent/services/email_extractor.py — with_structured_output pattern]
- [Source: src/quote_agent/config.py — LLMSettings.simple_model, lines 27-44]
- [Source: src/quote_agent/cli/search.py — CLI pattern reference]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Fixed mock patch path: `quote_agent.config.get_settings` instead of module-level (local import in classify_request)
- Removed unused `type: ignore` comments flagged by mypy strict
- Reformatted prompt string to comply with ruff E501 (120 char line limit)

### Completion Notes List

- ✅ Created `ClassificationResult` and `ClassificationInput` Pydantic DTOs in `agent/nodes/classifier.py`
- ✅ Implemented `classify_request()` async function with structured LLM output, timeout protection, and fallback to "complex"
- ✅ French classification prompt with 4 tiers (simple/ambiguous/complex/out_of_scope) and input isolation delimiters
- ✅ Added `ClassificationSettings` to `config.py` (timeout_seconds, fallback_complexity)
- ✅ 13 unit tests for classifier (4 tiers, timeout/error fallback, duration tracking, input isolation, ClassificationInput)
- ✅ CLI `classify` command with `--quantity`, `--reference`, `--urgency`, `--json` flags
- ✅ 9 unit tests for CLI classify (formatted output, JSON output, options passthrough, error handling)
- ✅ All 375 unit tests pass (353 existing + 22 new), ruff clean, mypy --strict clean

### Change Log

- 2026-03-20: Story 4.1 implementation complete — complexity classifier node, CLI command, and 22 unit tests
- 2026-03-20: Code review — M1 fixed: `fallback_complexity` typed as `Literal` instead of `str` to fail at config load, not during error recovery

### File List

- `src/quote_agent/agent/nodes/classifier.py` (new) — ClassificationResult, ClassificationInput, classify_request()
- `src/quote_agent/cli/classify.py` (new) — CLI classify command
- `src/quote_agent/cli/main.py` (modified) — registered classify command
- `src/quote_agent/config.py` (modified) — added ClassificationSettings
- `tests/unit/agent/__init__.py` (new) — test package init
- `tests/unit/agent/test_classifier.py` (new) — 13 classifier unit tests
- `tests/unit/test_cli_classify.py` (new) — 9 CLI classify unit tests
