# Story 4.5: Détection Export-Controlled & Entités Sanctionnées

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to detect and flag requests involving export-controlled products or sanctioned entities,
So that the company avoids legal liability from processing prohibited transactions.

## Acceptance Criteria

1. **AC-1: Export-Controlled Product Detection** — Given a request involves a product that may be export-controlled (dual-use goods, military-grade materials, controlled chemicals, nuclear-related items), when the compliance check node runs, then the request is flagged with a clear warning indicating the specific concern (export control category) and escalated — never auto-processed.

2. **AC-2: Sanctioned Entity Detection** — Given a request from a client whose name (or alias) matches a sanctions list entry, when the compliance check runs, then the request is blocked from automatic processing and flagged for human review with the matched entity and list source.

3. **AC-3: Mandatory Pipeline Integration** — Given detection is active, when any request is processed through the pipeline, then the compliance check runs as a mandatory step (not optional, not skippable) and the result is recorded in the reasoning trace.

4. **AC-4: Compliance Result DTO** — The check produces a `ComplianceCheckResult` with: `is_compliant` (bool), `flags` (list of `ComplianceFlag`), `check_duration_ms` (int). Each `ComplianceFlag` contains: `flag_type` (Literal["export_control", "sanctioned_entity"]), `severity` (Literal["warning", "block"]), `detail` (str), `matched_term` (str).

5. **AC-5: LLM-Based Detection** — The compliance check uses LLM structured output to analyze product descriptions and client names against known categories of controlled goods and sanctioned entities. The LLM receives the request content (in UNTRUSTED delimiters) and a system prompt describing what to look for.

6. **AC-6: Configurable Keyword Lists** — `ComplianceSettings` provides configurable keyword lists (`export_control_keywords`, `sanctioned_entity_keywords`) as seed terms for the LLM. These are supplementary hints — the LLM also uses its own knowledge of export control regulations (EAR, EU Dual-Use Regulation, Wassenaar Arrangement) and sanctions programs (OFAC SDN, EU sanctions, UN sanctions).

7. **AC-7: Fail-Safe Behavior** — On LLM timeout or error, the compliance check returns `is_compliant=False` with a flag explaining the error. Never approve on error — always escalate.

8. **AC-8: CLI Command** — A `uv run quote-agent compliance "description" --client "client name"` command runs the compliance check in isolation and displays the result (compliant/flagged, flags with details). Also, the `review` pipeline is extended to include the compliance check after self-review.

9. **AC-9: Audit Trail** — All compliance check results (pass and fail) are logged with structured logging including the component `"agent.nodes.compliance_checker"`, the flags detected, and the check duration.

## Tasks / Subtasks

- [x] Task 1: Create DTOs (AC: #4)
  - [x] `ComplianceFlag` model — flag_type (Literal), severity (Literal), detail (str), matched_term (str)
  - [x] `ComplianceCheckResult` model — is_compliant (bool), flags (list[ComplianceFlag]), check_duration_ms (int)
  - [x] `LLMComplianceOutput` model — for structured LLM output: flags (list), reasoning (str)
  - [x] `ComplianceSettings` config — timeout_seconds, export_control_keywords (list[str]), sanctioned_entity_keywords (list[str])
- [x] Task 2: Implement `check_compliance()` async function (AC: #1-3, #5-7, #9)
  - [x] `_check_export_control()` — LLM structured output to detect export-controlled products in matched results and request description
  - [x] `_check_sanctioned_entity()` — LLM structured output to detect sanctioned entity names in client name and request text
  - [x] Aggregate flags into `ComplianceCheckResult`
  - [x] `is_compliant = True` only if zero flags detected
  - [x] Structured logging for all results (pass and fail)
- [x] Task 3: Add `ComplianceSettings` to config.py (AC: #6)
  - [x] Settings class with sensible defaults for keyword lists
  - [x] Add to `Settings` root class as `compliance: ComplianceSettings`
- [x] Task 4: Implement CLI `compliance` command (AC: #8)
  - [x] `src/quote_agent/cli/compliance.py` — follows review.py pattern
  - [x] Standalone mode: check compliance on description + optional client name
  - [x] Display: compliance verdict, flags with severity/detail/matched_term
  - [x] `--json` output flag
  - [x] Register in `cli/main.py`
- [x] Task 5: Extend `review` CLI pipeline (AC: #8)
  - [x] After self-review step, add compliance check step
  - [x] Display compliance result alongside self-review result
  - [x] If compliance flags exist with severity "block", override final verdict to blocked
- [x] Task 6: Write unit tests for compliance checker node (AC: #1-7, #9)
  - [x] Test export control detection: controlled product keyword → flag with type "export_control"
  - [x] Test export control detection: normal industrial product → no flag
  - [x] Test sanctioned entity detection: sanctioned name → flag with type "sanctioned_entity", severity "block"
  - [x] Test sanctioned entity detection: normal client name → no flag
  - [x] Test combined: export-controlled product + sanctioned entity → two flags
  - [x] Test combined: clean request → is_compliant=True, empty flags
  - [x] Test fail-safe: LLM timeout → is_compliant=False with error flag
  - [x] Test fail-safe: adapter error → is_compliant=False with error flag
  - [x] Test duration tracking: check_duration_ms populated
  - [x] Test logging: structured log emitted with correct component
- [x] Task 7: Write unit tests for CLI compliance command (AC: #8)
  - [x] Test formatted output (compliant case)
  - [x] Test formatted output (flagged case with export control)
  - [x] Test formatted output (blocked case with sanctioned entity)
  - [x] Test JSON output
  - [x] Test error handling
- [x] Task 8: Write unit tests for extended review pipeline (AC: #8)
  - [x] Test review pipeline includes compliance step
  - [x] Test compliance block overrides self-review approved
- [x] Task 9: Quality gates — ruff, mypy --strict, all tests passing

## Dev Notes

### Architecture & Constraints

- **New file**: `src/quote_agent/agent/nodes/compliance_checker.py`
- Do NOT create `graph.py` or `state.py` — those come in Story 4.8
- The compliance check is a **mandatory pipeline step** that runs alongside self-review — it validates the request and matched products for export control and sanctions concerns
- It does NOT create or modify quotes — it flags and blocks
- Architecture gap noted: "FR28 (export control) underspecified — Detection approach remains vague — specify during implementation." This story specifies: LLM-based detection with configurable keyword seed lists

### Node Function Signature

Follow the established pattern from self_reviewer.py:

```python
async def check_compliance(
    request: ExtractedQuoteRequest,
    llm_adapter: OpenAICompatAdapter,
    *,
    client_name: str | None = None,
) -> ComplianceCheckResult:
```

Takes the request and optionally the client name. Does NOT need DB session (unlike self-review) — this is pure LLM analysis, no database queries.

### Export Control Detection (LLM)

Use LLM structured output to detect export-controlled products:

```python
class LLMExportControlOutput(BaseModel):
    has_concerns: bool
    concerns: list[ExportControlConcern] = Field(default_factory=list)
    reasoning: str

class ExportControlConcern(BaseModel):
    category: str  # e.g., "dual-use", "military", "nuclear", "chemical"
    detail: str
    matched_term: str
```

The LLM receives:
- The request description and matched product names (in UNTRUSTED delimiters)
- Seed keywords from `ComplianceSettings.export_control_keywords`
- Task: "Analyze if any products could be export-controlled under EAR, EU Dual-Use Regulation, or Wassenaar Arrangement."

Default `export_control_keywords`:
```python
[
    "dual-use", "military", "nuclear", "uranium", "centrifuge",
    "cryptographic", "night-vision", "thermal-imaging", "drone",
    "missile", "chemical-precursor", "biological", "explosif",
    "arme", "munition", "radar", "satellite",
]
```

### Sanctioned Entity Detection (LLM)

Second LLM call to detect sanctioned entity names:

```python
class LLMSanctionOutput(BaseModel):
    has_matches: bool
    matches: list[SanctionMatch] = Field(default_factory=list)
    reasoning: str

class SanctionMatch(BaseModel):
    entity_name: str
    matched_against: str  # what in the request matched
    list_source: str  # e.g., "OFAC SDN", "EU sanctions", "UN sanctions"
```

The LLM receives:
- The client name and any entity references in the request (in UNTRUSTED delimiters)
- Seed keywords from `ComplianceSettings.sanctioned_entity_keywords`
- Task: "Analyze if the client name or entities match known sanctioned parties under OFAC, EU, or UN sanctions programs."

Default `sanctioned_entity_keywords`:
```python
[
    "DPRK", "North Korea", "Iran", "Syria", "Cuba", "Crimea",
    "Donetsk", "Luhansk", "Wagner", "Hezbollah", "Hamas",
]
```

### LLM Structured Output Pattern

Same as all other nodes:
```python
from quote_agent.config import get_settings
settings = get_settings()

model = llm_adapter.get_model("simple")
structured = model.with_structured_output(LLMExportControlOutput)
result = await asyncio.wait_for(
    structured.ainvoke(messages),  # type: ignore[arg-type]
    timeout=settings.compliance.timeout_seconds,
)
```

### Input Isolation (Security Layer 2)

All LLM calls must wrap untrusted content with delimiters:
```
<<<UNTRUSTED_QUOTE_REQUEST_START>>>
{request content}
<<<UNTRUSTED_QUOTE_REQUEST_END>>>
```

System prompts in French, following the established pattern from classifier.py and self_reviewer.py.

### Error Handling / Fallback

- On timeout or LLM error → `is_compliant=False` (fail-safe: flag on error, never approve on error)
- Catch `LLMTimeoutError`, `AdapterError`, `TimeoutError` specifically
- Record the error as a `ComplianceFlag`: flag_type="error", severity="block", detail=error message
- This is the same fail-safe philosophy as self_reviewer.py

### Flag Severity Semantics

- `"warning"` — export-controlled product detected. Request is flagged for human review but not hard-blocked. The sales rep sees the flag and decides.
- `"block"` — sanctioned entity detected OR error during check. Request is hard-blocked from automatic processing. Must be reviewed by human.

### ComplianceSettings Defaults

```python
class ComplianceSettings(BaseModel):
    """Compliance check configuration."""

    timeout_seconds: int = 15
    export_control_keywords: list[str] = Field(default_factory=lambda: [
        "dual-use", "military", "nuclear", "uranium", "centrifuge",
        "cryptographic", "night-vision", "thermal-imaging", "drone",
        "missile", "chemical-precursor", "biological", "explosif",
        "arme", "munition", "radar", "satellite",
    ])
    sanctioned_entity_keywords: list[str] = Field(default_factory=lambda: [
        "DPRK", "North Korea", "Iran", "Syria", "Cuba", "Crimea",
        "Donetsk", "Luhansk", "Wagner", "Hezbollah", "Hamas",
    ])
```

Timeout is 15s (slightly longer than self-review's 10s) because two LLM calls are made sequentially.

### CLI `compliance` Command

Standalone compliance check:
```
uv run quote-agent compliance "tubes zirconium grade nucléaire Ø25" --client "ACME Industries"
```

Output (formatted):
```
Compliance Verdict: FLAGGED
Check Duration: 1842ms

Flags:
  [export_control] WARNING
    Category: nuclear
    Detail: Zirconium tubes of nuclear grade are controlled under EU Dual-Use Regulation
    Matched: "zirconium grade nucléaire"

  [sanctioned_entity] — none detected
```

### Extending the `review` Pipeline

In `review.py`, after the self-review step, add the compliance check:

```python
# Step 5: Self-review
review_result = await self_review(reasoning, request, adapter, session)

# Step 6: Compliance check
from quote_agent.agent.nodes.compliance_checker import check_compliance
compliance_result = await check_compliance(request, adapter, client_name=client_name)
```

The `review` command gains a new `--client` option for the client name.

The `_run_review()` return type changes to include both results. Options:
1. Return a tuple `(SelfReviewResult, ComplianceCheckResult)` — simplest
2. Create a `PipelineResult` that wraps both — cleaner but more abstraction

Prefer option 1 for simplicity. Adjust `_format_review_result()` to display compliance after self-review.

### Mock Pattern for Tests

Follow the exact pattern from `test_self_reviewer.py`:

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

For tests with two sequential LLM calls (export control + sanctions), use `side_effect` to return different results for each call:

```python
mock_structured = AsyncMock()
mock_structured.ainvoke = AsyncMock(side_effect=[export_result, sanction_result])
```

Settings mock: patch `"quote_agent.config.get_settings"` (local import in the node function).

### Project Structure Notes

- New files follow existing naming and location patterns
- `src/quote_agent/agent/nodes/compliance_checker.py` — mirrors `self_reviewer.py`
- `src/quote_agent/cli/compliance.py` — mirrors `review.py`
- `tests/unit/agent/test_compliance_checker.py` — mirrors `test_self_reviewer.py`
- `tests/unit/test_cli_compliance.py` — mirrors `test_cli_review.py`
- `from __future__ import annotations` required in all new files
- Absolute imports only

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.5]
- [Source: _bmad-output/planning-artifacts/prd.md — FR28 (export control/sanctioned entities)]
- [Source: _bmad-output/planning-artifacts/architecture.md — FR24-28, Agent nodes structure, Security architecture, Audit trail, Gap: FR28 underspecified]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Escalation UX, confidence tier visual language (red/flag for low/blocked)]
- [Source: docs/project-context.md — Established patterns, LLM structured output, Input isolation, Config pattern]
- [Source: src/quote_agent/agent/nodes/self_reviewer.py — Node function pattern, fail-safe pattern, UNTRUSTED delimiters]
- [Source: src/quote_agent/agent/nodes/classifier.py — LLM structured output pattern, system prompt pattern]
- [Source: src/quote_agent/cli/review.py — CLI pipeline pattern, _run_review() extension point]
- [Source: src/quote_agent/cli/main.py — CLI command registration pattern]
- [Source: src/quote_agent/config.py — Settings pattern (SelfReviewSettings as model)]
- [Source: src/quote_agent/exceptions.py — SecurityError, AdapterError, LLMTimeoutError]

### Previous Story Intelligence (4.4)

- Mock pattern: `_make_adapter_mock(result)` creates mock adapter -> model -> structured -> ainvoke
- For two sequential LLM calls, use `side_effect` on `ainvoke` (self_reviewer uses this for coherence + integrity)
- Patch path for settings: `"quote_agent.config.get_settings"` (local import in node function)
- 478 unit tests passing before this story
- `from __future__ import annotations` required in all src/ files
- `asyncio_mode = "auto"` in pytest — no manual @pytest.mark.asyncio needed
- `fallback_complexity` / `fallback_tier` must be typed as `Literal` not `str`
- Pydantic forward reference: if a DTO from another module is used as a Pydantic field, it must be runtime-imported (not TYPE_CHECKING only)
- Input isolation delimiters: `<<<UNTRUSTED_QUOTE_REQUEST_START>>>` / `<<<UNTRUSTED_QUOTE_REQUEST_END>>>`
- Variable shadowing: avoid reusing import names as loop variables
- DB session obtained via `_get_session_factory()` from `models.base` — but NOT needed for this story (pure LLM check)
- `review.py` `_run_review()` reuses `_run_reason()` from `reason.py` — extend this to add compliance check
- Self-reviewer has 4 validation steps (catalog, quantity, coherence, integrity) — compliance is a separate node, not a 5th step in self-review
- `model_copy(update={...})` for Pydantic immutable updates with duration

### Git Intelligence

Recent commits (Stories 4.1-4.4):
- `e8a0223` feat: add self-review validation gate with CLI command (Story 4.4)
- `0d8f076` feat: add adaptive reasoning strategies with CLI command (Story 4.3)
- `b4ac30d` feat: add confidence scoring node and tier routing with CLI command (Story 4.2)
- `bbd8cc2` feat: add request complexity classifier node with CLI command (Story 4.1)
- Pattern: each story adds a node file, a CLI file, and corresponding unit tests
- Config settings added to `config.py` and `Settings` root class
- CLI commands registered in `main.py` with wrapper pattern (lazy imports)
- Commit message format: `feat: add {feature description} ({Story X.Y})`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- mypy variable shadowing: `flag` loop variable in `_format_review_result()` shadowed string loop variable from `review.anomaly_flags` — renamed to `cflag`
- Settings patch path: `quote_agent.config.get_settings` (not `quote_agent.agent.nodes.compliance_checker.get_settings`) because local import in function

### Completion Notes List

- Implemented `ComplianceFlag`, `ComplianceCheckResult`, `LLMExportControlOutput`, `LLMSanctionOutput` DTOs with Literal-constrained types
- Implemented `check_compliance()` async function with two sequential LLM calls (export control + sanctions)
- Fail-safe: both `TimeoutError`, `LLMTimeoutError`, and `AdapterError` caught per check, returning `is_compliant=False` with error flag
- Added `ComplianceSettings` to config.py with default keyword lists for export control and sanctions
- Created standalone CLI `compliance` command with `--client` and `--json` options
- Extended `review` CLI pipeline: returns tuple `(SelfReviewResult, ComplianceCheckResult)`, displays compliance after self-review, blocks on severity "block"
- Added `--client` option to `review` command
- 28 new unit tests (17 compliance checker + 9 CLI compliance + 2 review pipeline extension)
- Updated 5 existing review CLI tests to handle new tuple return type
- All 506 unit tests passing, ruff clean, mypy --strict clean

### File List

New files:
- src/quote_agent/agent/nodes/compliance_checker.py
- src/quote_agent/cli/compliance.py
- tests/unit/agent/test_compliance_checker.py
- tests/unit/test_cli_compliance.py

Modified files:
- src/quote_agent/config.py (added ComplianceSettings + compliance field on Settings)
- src/quote_agent/cli/main.py (registered compliance command, added --client to review)
- src/quote_agent/cli/review.py (extended _run_review to return tuple, added compliance display)
- tests/unit/test_cli_review.py (updated mocks for tuple return, added 2 compliance integration tests)

### Change Log

- 2026-03-21: Story 4.5 implementation complete — export control & sanctioned entity detection node, CLI command, review pipeline extension, 28 new tests (506 total)
