# Story 4.0b: CLI Flux Testable Search

Status: done

## Story

As a **Project Lead (Khalil)**,
I want a CLI command that executes a product search and displays formatted results,
So that I can manually test the search engine, judge result quality, and catch product regressions.

## Acceptance Criteria

1. **Given** products are ingested and embedded in PostgreSQL **When** I run `uv run agent search "tubes inox 304L Ø25"` **Then** the top results are displayed with: product name, reference, category, score, match source (semantic/keyword/hybrid/exact_ref), is_proposable flag **And** if jargon expansion occurred, the expanded query is shown **And** the search duration is displayed.

2. **Given** the CLI is extensible **When** Epic 4 is developed **Then** additional commands can be added (`classify`, `process`) to expose the full agent reasoning pipeline.

## Tasks / Subtasks

- [x] Task 1: Create `search` CLI command file (AC: #1)
  - [x] 1.1 Create `src/quote_agent/cli/search.py` with a `search` Typer command
  - [x] 1.2 Accept positional `query` argument (str)
  - [x] 1.3 Add options: `--limit` (int, default 10), `--method` (hybrid/semantic/keyword, default hybrid), `--no-filter` (disable proposability filter), `--include-stale` (include stale products), `--json` (machine-readable JSON output)
  - [x] 1.4 Run the async search inside `asyncio.run()` (Typer is sync, SearchEngine is async)

- [x] Task 2: Wire SearchEngine from CLI context (AC: #1)
  - [x] 2.1 Inside the command, create an async helper that: gets `_get_session_factory()` from `quote_agent.models.base`, opens a session, calls `get_search_engine(session)`, runs the search, and closes cleanly
  - [x] 2.2 Use lazy imports for search/embedding modules — the `search` command file must not import `sentence_transformers` or `quote_agent.adapters.embedding` at module level (CI runs without ML deps)
  - [x] 2.3 Handle missing ML deps gracefully: if `sentence-transformers` is not installed, print an error message and exit with code 1

- [x] Task 3: Format and display results (AC: #1)
  - [x] 3.1 Display header: query, method, result count, duration
  - [x] 3.2 If jargon expansion occurred, display: `Expanded query: <expanded_query>`
  - [x] 3.3 If from cache, display `(cached)` indicator
  - [x] 3.4 Display each result as a formatted row: rank, reference, name (truncated if long), category, score (4 decimal places), match_source, is_proposable (green check / red cross)
  - [x] 3.5 Use Typer color output: green for proposable, red for not proposable, yellow for match_source
  - [x] 3.6 If `--json` flag is set, output `SearchResult.model_dump_json(indent=2)` instead of formatted table

- [x] Task 4: Register command in CLI main (AC: #2)
  - [x] 4.1 Add `app.command()(search)` in `src/quote_agent/cli/main.py`
  - [x] 4.2 Import must be lazy or conditional to avoid importing ML deps when running `agent status` or `agent logs`

- [x] Task 5: Unit tests (AC: #1)
  - [x] 5.1 Test formatted output for a mock SearchResult (no DB, no embedding adapter)
  - [x] 5.2 Test `--json` output mode produces valid JSON matching SearchResult schema
  - [x] 5.3 Test `--method` option dispatches to correct SearchEngine method
  - [x] 5.4 Test `--no-filter` sets `apply_proposability_filter=False` on SearchRequest
  - [x] 5.5 Test graceful error when DB is unreachable

- [x] Task 6: Validate in CI and locally (AC: #1, #2)
  - [x] 6.1 All existing 363+ unit tests still pass
  - [x] 6.2 New unit tests pass without ML deps (no sentence-transformers needed for mocked tests)
  - [x] 6.3 mypy --strict passes
  - [x] 6.4 ruff check + ruff format pass

## Dev Notes

### Architecture Compliance

- **CLI framework:** Typer (already a dependency, `typer>=0.24.1`)
- **CLI entry point:** `agent = "quote_agent.cli.main:app"` in pyproject.toml — the actual CLI command name is `agent`, NOT `quote-agent`. Run as: `uv run agent search "tubes inox 304L Ø25"`
- **CLI design (from UX spec):** verb-based commands, color-coded output (green/yellow/red), machine-readable JSON option
- **File location:** New file at `src/quote_agent/cli/search.py`, following the existing pattern of `cli/status.py` and `cli/logs.py`

### Critical: Lazy Imports for ML Dependencies

Story 4.0a established that `sentence-transformers` is in the `[dependency-groups] ml` optional group. CI runs `uv sync --locked --no-group ml`. The `search` command requires the embedding adapter (which loads sentence-transformers), so:

- `cli/search.py` must NOT import `quote_agent.adapters.embedding` or `quote_agent.search` at module level
- All imports of search/embedding modules must happen inside the async helper function
- `cli/main.py` must import `search` command lazily (same pattern — do NOT add a top-level `from quote_agent.cli.search import search`)
- Pattern: use `app.command()` with a wrapper function that does the lazy import inside

### Session Management Pattern

The CLI command needs an `AsyncSession` but Typer commands are synchronous. Use this pattern:

```python
import asyncio

async def _run_search(query: str, ...) -> SearchResult:
    from quote_agent.models.base import _get_session_factory
    from quote_agent.search import get_search_engine

    factory = _get_session_factory()
    async with factory() as session:
        engine = get_search_engine(session)
        result = await engine.search_hybrid(request)
    return result

# In the Typer command:
result = asyncio.run(_run_search(query, ...))
```

### SearchEngine API

`SearchEngine` is constructed via `get_search_engine(session)` which creates it with the cached embedding adapter. Three methods available:
- `search_hybrid(request)` — default, RRF fusion of semantic + keyword
- `search_semantic_only(request)` — vector search only
- `search_keyword_only(request)` — tsvector full-text only

`SearchRequest` fields: `query` (str), `limit` (int=10), `include_stale` (bool=False), `apply_proposability_filter` (bool=True)

`SearchResult` fields: `results` (list[ScoredProduct]), `total_found` (int), `query` (str), `method` (str), `duration_seconds` (float), `from_cache` (bool), `jargon_expanded` (bool), `expanded_query` (str|None)

`ScoredProduct` fields: `product_id` (UUID), `reference` (str), `name` (str), `category` (str), `description` (str|None), `unit_price` (float), `score` (float), `rank` (int), `match_source` (Literal), `is_proposable` (bool)

### Output Format Example

```
Search: "tubes inox 304L Ø25"
Method: hybrid | Results: 10 / 47 | Duration: 0.1832s
Expanded query: tubes acier inoxydable stainless steel 304L diamètre diameter 25

  #  Reference       Name                           Category     Score    Source     Prop
  1  TB-INOX-304L-25 Tube inox 304L Ø25x2 6m        Tubes        0.0323  hybrid     ✓
  2  TB-INOX-304L-30 Tube inox 304L Ø30x2 6m        Tubes        0.0298  hybrid     ✓
  3  TB-INOX-316L-25 Tube inox 316L Ø25x2 6m        Tubes        0.0276  hybrid     ✗
  ...
```

### Existing Code Patterns to Follow

- **Config pattern:** `get_settings()` returns cached singleton, access via `settings.search`, `settings.jargon`, etc.
- **Type safety:** `from __future__ import annotations` in every file, mypy --strict
- **Imports:** Absolute imports only (`from quote_agent.xxx import yyy`)
- **Test naming:** `test_{behavior}_when_{condition}()`
- **Test pattern for CLI:** Use `typer.testing.CliRunner` to invoke commands and assert output
- **Pydantic:** Use `model_copy(update=...)` not direct attribute mutation, `model_dump_json()` for serialization

### What NOT to Do

- Do NOT import search/embedding modules at module level in CLI files
- Do NOT use `rich` or any new dependency for formatting — use Typer's built-in `typer.style()` and `typer.echo()` (consistent with existing `status.py`)
- Do NOT add a new API endpoint — this is CLI only
- Do NOT add Redis or any new infrastructure
- Do NOT mock the database in E2E tests
- Do NOT change the existing SearchEngine, SearchRequest, or SearchResult models
- Do NOT add `--verbose` or logging configuration flags — keep it simple for MVP

### Previous Story Intelligence (4.0a)

- CI pipeline now works: `uv sync --locked --no-group ml` for lint/test, full install for Docker
- 363+ unit tests pass without ML deps
- Embedding adapter already uses lazy imports (`from quote_agent.adapters.embedding.sentence_transformers import SentenceTransformerAdapter` inside function)
- PostgreSQL service container available in CI for integration tests
- Commit convention: `feat: add CLI search command for manual testing (Story 4.0b)`

### Git Intelligence

Recent commits follow pattern: `feat:`, `fix:`, `content:`, `retro:`, `docs:`
This story should use: `feat: add CLI search command for manual testing (Story 4.0b)`

### Project Structure Notes

- New file: `src/quote_agent/cli/search.py` — follows existing `cli/status.py`, `cli/logs.py` pattern
- Modified file: `src/quote_agent/cli/main.py` — register new command
- New test file: `tests/unit/test_cli_search.py`
- No other files should need modification

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4, Story 4.0b — Acceptance criteria, blocks all 4.1+]
- [Source: _bmad-output/planning-artifacts/architecture.md — CLI entry point, project structure]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — CLI design: verb-based, color-coded, JSON option]
- [Source: docs/project-context.md — Quality gates, known pitfalls, conventions]
- [Source: src/quote_agent/cli/main.py — Existing Typer app with status/logs commands]
- [Source: src/quote_agent/cli/status.py — Reference for CLI output formatting pattern]
- [Source: src/quote_agent/search/engine.py — SearchEngine API, 3 search methods]
- [Source: src/quote_agent/search/models.py — SearchRequest, ScoredProduct, SearchResult schemas]
- [Source: src/quote_agent/search/__init__.py — get_search_engine() factory]
- [Source: src/quote_agent/models/base.py — _get_session_factory(), async session management]
- [Source: _bmad-output/implementation-artifacts/4-0a-fix-ci-cd-pipeline-github-actions.md — ML dep isolation, lazy imports]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Ruff found 2 issues (E501 line too long, F401 unused import) — fixed immediately
- Live testing revealed pre-existing timezone bug in `search/cache.py`: `datetime.now(UTC)` produces tz-aware datetimes but `search_cache.expires_at` is `TIMESTAMP WITHOUT TIME ZONE` — fixed by stripping tzinfo
- ImportError for `sentence-transformers` was not caught because it occurs inside `get_search_engine()` (not at import time) — moved entire function body inside try/except
- DB connection error message improved with user-friendly guidance

### Completion Notes List

- Created `src/quote_agent/cli/search.py` with `search` Typer command: positional `query`, `--limit`, `--method`, `--no-filter`, `--include-stale`, `--json` options
- Async helper `_run_search()` uses lazy imports for search/embedding modules (ImportError handling for missing ML deps)
- Method dispatch: hybrid (default) → `search_hybrid()`, semantic → `search_semantic_only()`, keyword → `search_keyword_only()`
- Formatted output: header (query, method, count, duration), jargon expansion display, cache indicator, colored table with rank/ref/name/category/score/source/proposability
- JSON output via `model_dump_json(indent=2)` for machine-readable mode
- Registered in `main.py` via `@app.command()` wrapper with lazy import of `search.py` (no top-level ML import)
- 14 unit tests covering: formatted output (5), JSON output (2), method dispatch (4), no-filter flag (2), error handling (1)
- 377 total unit tests pass (was 363, +14 new), no regressions
- mypy --strict, ruff check, ruff format all pass

### Change Log

- 2026-03-20: Implemented CLI search command (Story 4.0b) — all 6 tasks complete
- 2026-03-20: Fixed pre-existing timezone bug in search cache, improved CLI error messages
- 2026-03-20: Code review fixes — ANSI column alignment in search output, documented undeclared file changes (ci.yml, test_search_proposability.py)

### File List

- `src/quote_agent/cli/search.py` (new) — CLI search command with formatted/JSON output
- `src/quote_agent/cli/main.py` (modified) — registered search command with lazy import wrapper
- `src/quote_agent/search/cache.py` (modified) — fixed timezone mismatch (tz-aware → naive UTC)
- `tests/unit/test_cli_search.py` (new) — 14 unit tests for CLI search
- `tests/unit/test_search_cache.py` (modified) — aligned mock datetimes with naive UTC fix
- `tests/unit/test_search_proposability.py` (modified) — fixed env_var_mapping test to use env_vars/clear_settings_cache fixtures
- `.github/workflows/ci.yml` (modified) — removed continue-on-error: true from test step
