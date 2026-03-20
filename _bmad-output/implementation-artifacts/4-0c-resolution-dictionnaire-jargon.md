# Story 4.0c: Résolution Dictionnaire Jargon (Story 3.6)

Status: done

## Story

As a **Project Lead (Khalil)**,
I want the jargon dictionary regression from Story 3.6 evaluated and resolved,
so that the "zero-preprocessing" product vision is restored and we don't carry a synonym table into Epic 4.

## Acceptance Criteria

1. **Given** the jargon benchmark (25 queries from `tests/e2e/fixtures/jargon_benchmark.json`)
   **When** run with `expansion_enabled=False` (no dictionary, pure semantic search)
   **Then** the pass rate is measured and compared to the expansion-enabled result

2. **Given** the benchmark results
   **When** analyzed
   **Then** a decision is made:
   - If BGE-M3 alone meets ≥ 80% pass rate → remove the dictionary entirely
   - If not → investigate embedding strategy improvements (text building, model tuning) rather than growing the dictionary

3. **Given** the decision is made
   **When** implemented
   **Then** the `JargonSettings.expansion_enabled` default reflects the decision
   **And** the rationale is documented in `docs/project-context.md`

## Tasks / Subtasks

- [x] Task 1: Run benchmark with expansion enabled (baseline) (AC: #1)
  - [x] 1.1 Execute `TestJargonBenchmarkE2E` in `tests/e2e/test_search_jargon_e2e.py` with `JARGON__EXPANSION_ENABLED=true`
  - [x] 1.2 Record pass rate, per-category breakdown (abbreviation, jargon, cross_language, exact_reference)
  - [x] 1.3 Record which specific queries pass/fail with scores

- [x] Task 2: Run benchmark with expansion disabled (AC: #1)
  - [x] 2.1 Execute same benchmark with `JARGON__EXPANSION_ENABLED=false`
  - [x] 2.2 Record pass rate and per-category breakdown
  - [x] 2.3 Record which queries pass/fail — identify which queries **only** pass with dictionary

- [x] Task 3: Analyze results and decide (AC: #2)
  - [x] 3.1 Compare pass rates: expansion-enabled vs expansion-disabled
  - [x] 3.2 Identify queries where semantic-only fails — assess if failure is due to abbreviation gaps or embedding model limitation
  - [x] 3.3 If semantic-only ≥ 80% → decision = **remove dictionary**
  - [ ] ~~3.4 If semantic-only < 80% → investigate embedding text-building improvements~~ (N/A — 96% pass rate)

- [x] Task 4: Implement the decision (AC: #2, #3)
  - [x] **IF REMOVE (≥ 80% pass rate):**
    - [x] 4a.1 Delete `src/quote_agent/search/jargon.py`
    - [x] 4a.2 Remove `JargonSettings` class from `src/quote_agent/config.py`
    - [x] 4a.3 Remove jargon expansion calls from `src/quote_agent/search/engine.py` (`_apply_jargon_expansion` method and all 3 call sites in `search_hybrid`, `search_semantic`, `search_keyword`)
    - [x] 4a.4 Remove `jargon_expanded` and `expanded_query` fields from `src/quote_agent/search/models.py` `SearchResult`
    - [x] 4a.5 Remove jargon display logic from `src/quote_agent/cli/search.py` (lines 23-24)
    - [x] 4a.6 Delete `tests/unit/test_search_jargon.py`
    - [x] 4a.7 Delete `tests/e2e/test_search_jargon_e2e.py`
    - [x] 4a.8 Delete `tests/e2e/fixtures/jargon_benchmark.json`
    - [x] 4a.9 Remove jargon-related tests from `tests/unit/test_cli_search.py` (expanded query display test, ~lines 92-99)
    - [x] 4a.10 Update `docs/project-context.md` — remove jargon from search module listing, add rationale under a "Decisions" section
  - ~~**IF KEEP (< 80% pass rate):**~~ (N/A — 96% pass rate, decision is REMOVE)
    - ~~4b.1 Set `JargonSettings.expansion_enabled` default to `True` (already is)~~
    - ~~4b.2 Document why dictionary is temporarily retained and what embedding strategy improvements are needed~~
    - ~~4b.3 Create a follow-up story for embedding text-building improvements~~

- [x] Task 5: Validate CI passes (AC: #1, #2, #3)
  - [x] 5.1 Run full unit test suite — all tests pass (353 passed, down from 377 — 24 jargon tests removed)
  - [x] 5.2 Run `ruff check` and `mypy --strict` — no new errors (1 pre-existing mypy warning in sentence_transformers.py, unrelated)
  - [x] 5.3 Verify no import errors or broken references after jargon removal

- [x] Task 6: Document rationale (AC: #3)
  - [x] 6.1 Update `docs/project-context.md` with benchmark results and decision rationale
  - [x] 6.2 Include pass rate numbers and category breakdown in the documentation

## Dev Notes

### Context: Why This Story Exists

Story 3.6 introduced a jargon dictionary (10 abbreviation→expansion mappings) for query expansion. The Epic 3 retrospective flagged this as a **product regression**: the project's core vision is "zero-preprocessing" — BGE-M3's multilingual semantic understanding should handle industrial jargon natively, without maintaining synonym tables. Khalil cited the ArcelorMittal pipeline as a cautionary parallel where synonym maintenance became unsustainable.

This story is a **blocker for all Epic 4 stories** (4.1–4.8). The zero-preprocessing vision must be validated before building the reasoning layer.

### Architecture Compliance

- **Search module location:** `src/quote_agent/search/` — all modifications stay within this module
- **Configuration:** `src/quote_agent/config.py` — JargonSettings uses `JARGON__` env prefix via pydantic-settings
- **CLI:** `src/quote_agent/cli/search.py` — displays jargon metadata in search results
- **Test structure:** `tests/unit/test_search_*.py` mirrors `src/` structure; `tests/e2e/` for real-service tests

### Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `src/quote_agent/search/jargon.py` | Remove (if ≥80%) or Keep | Core expansion logic |
| `src/quote_agent/config.py` | Remove JargonSettings (if ≥80%) or Update default | Lines ~91-108 |
| `src/quote_agent/search/engine.py` | Remove `_apply_jargon_expansion` + 3 call sites (if ≥80%) | Lines ~74-81, plus calls in search_hybrid/semantic/keyword |
| `src/quote_agent/search/models.py` | Remove `jargon_expanded`/`expanded_query` fields (if ≥80%) | Lines ~44-45 |
| `src/quote_agent/cli/search.py` | Remove jargon display (if ≥80%) | Lines ~23-24 |
| `tests/unit/test_search_jargon.py` | Remove (if ≥80%) | 11+ unit tests |
| `tests/e2e/test_search_jargon_e2e.py` | Remove (if ≥80%) | 4 E2E + benchmark tests |
| `tests/e2e/fixtures/jargon_benchmark.json` | Remove (if ≥80%) | 25 benchmark queries |
| `tests/unit/test_cli_search.py` | Remove jargon display test (if ≥80%) | Lines ~92-99 |
| `docs/project-context.md` | Update with decision rationale | Always |

### Testing Strategy

1. **Benchmark execution** requires real PostgreSQL + pgvector + BGE-M3 embeddings (E2E environment)
2. **Unit tests** can validate code removal cleanly (no broken imports, no stale references)
3. **CI validation** via `ruff check` + `mypy --strict` + `pytest tests/unit/` (no ML deps needed)
4. Run the CLI search command (`uv run agent search "tubes inox 304L Ø25"`) to visually confirm behavior post-change

### Anti-Patterns to Avoid

- **Do NOT grow the dictionary** — adding more abbreviations is the opposite of the project vision
- **Do NOT half-remove** — if the decision is remove, remove completely (code, tests, config, fixtures, docs)
- **Do NOT break the SearchResult contract** — other code may reference `jargon_expanded` field; grep for all usages before removing
- **Do NOT skip the benchmark** — the decision must be data-driven, not assumed

### Previous Story Intelligence

**From Story 4.0b (CLI Flux Testable Search):**
- CLI search command created at `src/quote_agent/cli/search.py`
- Lazy imports pattern for ML deps (important for CI compatibility)
- Pre-existing timezone bug fixed in `search/cache.py`
- 377 total tests pass currently
- Test pattern: `test_{behavior}_when_{condition}()` naming convention

**From Story 4.0a (Fix CI/CD):**
- ML deps isolated to `[dependency-groups] ml` — use `uv sync --locked --no-group ml` for CI
- 19 files modified, ruff/mypy errors cleaned up
- PostgreSQL + pgvector service container in GitHub Actions CI

### Git Intelligence

Recent commits show consistent pattern:
- Commit prefix: `feat:`, `fix:`, `retro:`, `content:`
- Story reference in parentheses: `(Story X.Y)`
- Expected commit for this story: `feat: resolve jargon dictionary — benchmark validates BGE-M3 semantic search (Story 4.0c)` or similar

### Project Structure Notes

- Jargon module is cleanly isolated in `search/jargon.py` with well-defined integration points in `engine.py`
- No database schema changes needed — jargon is config-only, no migrations
- The `search/` module listing in `docs/project-context.md` (lines ~154-167) includes `jargon.py` — must be updated if removed

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.0c]
- [Source: _bmad-output/implementation-artifacts/epic-3-retro-2026-03-20.md — Technical Debt #1, lines 64-70]
- [Source: _bmad-output/implementation-artifacts/4-0b-cli-flux-testable-search.md — Dev Notes]
- [Source: docs/project-context.md — Search Module Pattern, lines 154-167]
- [Source: src/quote_agent/config.py — JargonSettings, lines 91-108]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- ✅ Task 1: Benchmark with expansion enabled — 24/25 = 96.0% (abbreviation 83%, jargon 100%, cross_language 100%, exact_reference 100%). Only failure: "boulons HM M10x50" — no matching product in fixture.
- ✅ Task 2: Benchmark with expansion disabled — 24/25 = 96.0% (identical breakdown). Delta = 0%. No query benefits from dictionary expansion.
- ✅ Task 3: Decision = **REMOVE dictionary**. 96% >> 80% threshold. The single failure ("boulons HM M10x50") fails in both modes — it's a fixture gap, not a semantic search limitation. BGE-M3 handles all abbreviations (inox, DN, PN, Ø, lg, TB, RD) natively.
- ✅ Task 4: Complete jargon removal — deleted jargon.py, JargonSettings, all 3 engine call sites, SearchResult fields, CLI display, 24 tests (unit + E2E + benchmark fixture).
- ✅ Task 5: 353 unit tests pass, ruff clean, no import errors. mypy has 1 pre-existing unrelated warning.
- ✅ Task 6: docs/project-context.md updated with Decisions section documenting benchmark results and rationale.

### Change Log

- 2026-03-20: Story 4.0c — Jargon dictionary removed after benchmark validated BGE-M3 semantic search (96% pass rate, 0% delta with/without dictionary)

### File List

**Deleted:**
- `src/quote_agent/search/jargon.py`
- `tests/unit/test_search_jargon.py`
- `tests/e2e/test_search_jargon_e2e.py`
- `tests/e2e/fixtures/jargon_benchmark.json`

**Modified:**
- `src/quote_agent/config.py` — removed JargonSettings class and jargon field from Settings
- `src/quote_agent/search/engine.py` — removed _apply_jargon_expansion method, jargon import, all 3 call sites, jargon_expanded/expanded_query from SearchResult construction
- `src/quote_agent/search/models.py` — removed jargon_expanded and expanded_query fields from SearchResult
- `src/quote_agent/cli/search.py` — removed jargon expanded query display
- `tests/unit/test_cli_search.py` — removed jargon expanded query test and jargon params from _make_search_result
- `docs/project-context.md` — removed jargon from search module listing and settings table, added Decisions section with benchmark rationale
