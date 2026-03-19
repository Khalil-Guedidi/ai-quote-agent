# Story 3.0b: Génération du project-context.md

Status: done

## Story

As a **developer (human or AI)**,
I want a centralized `project-context.md` documenting established patterns, conventions, and known pitfalls,
So that every story starts with full project context instead of rediscovering it from scratch.

## Acceptance Criteria

1. **AC-1: Comprehensive pattern documentation**
   - Given the project has completed Epics 1 and 2
   - When the `project-context.md` is generated
   - Then it contains: adapter pattern, LLM structured output pattern, pipeline integration pattern, security layer pattern, test conventions, known pitfalls (annotations + SQLAlchemy, lexicographic string comparisons, regex edge cases), naming conventions, and quality gates (mypy strict, ruff, coverage)

2. **AC-2: Sufficient context for anti-pattern prevention**
   - Given a new story is created
   - When the dev agent reads `project-context.md`
   - Then it has sufficient context to avoid previously-identified anti-patterns without relying on per-story dev notes

## Tasks / Subtasks

- [x] Task 1: Analyze existing codebase for established patterns (AC: 1, 2)
  - [x] 1.1: Document the **Adapter Pattern** — Protocol + Implementation + DTOs + Factory (`@lru_cache`), replicated in 4 adapters (LLM, ERP, Email, Notification)
  - [x] 1.2: Document the **LLM Structured Output Pattern** — `model.with_structured_output(PydanticModel)` → `await structured.ainvoke(messages)` with `asyncio.wait_for` timeout
  - [x] 1.3: Document the **Pipeline Integration Pattern** — `_persist_emails()` inline processing: `received → cleaned → extracted → split`, per-step error handling
  - [x] 1.4: Document the **Security Layer Pattern** — sanitizer (regex detection + `[SANITIZED: ...]` escaping), input_isolation (delimiter separation), log_redactor (`[REDACTED_*]` replacement), audit/logger (JSONLogFormatter with auto-redaction)
  - [x] 1.5: Document the **Async Pattern** — `asyncio.to_thread()` for wrapping sync stdlib (xmlrpc, imaplib), entire stack is async

- [x] Task 2: Document known pitfalls and anti-patterns (AC: 2)
  - [x] 2.1: **Pydantic + mocking** — `patch.object` on Pydantic model instances fails because `__setattr__`/`__delattr__` are intercepted. Use class-level patching instead.
  - [x] 2.2: **Lexicographic string comparison** — `max()` on severity strings fails (`"medium" > "high"` lexicographically). Use explicit conditional logic for severity ordering.
  - [x] 2.3: **Regex over-matching** — Price regex patterns can match unintended content like percentages. Test edge cases explicitly.
  - [x] 2.4: **Recursive logging** — `redact()` called during log formatting can trigger additional log calls. Guard with `_in_format` flag or similar.
  - [x] 2.5: **`from __future__ import annotations`** — Required in all files for deferred annotation evaluation. Without it, `Mapped[datetime]` and other SQLAlchemy annotations fail at runtime. Except: SQLAlchemy models need `datetime` imported at runtime (add `# noqa: TC003` comment).
  - [x] 2.6: **FastAPI `Depends()` and `dependency_overrides`** — `Annotated[X, Depends(...)]` breaks `dependency_overrides` in tests (returns 422). Keep standard `Depends()` with `# noqa: B008`.
  - [x] 2.7: **Health check cascade** — Adding new services to health endpoint breaks existing tests if mocks are missing. Use shared test helpers from `conftest.py`.
  - [x] 2.8: **Runtime vs dev dependencies** — Audit dependencies at each story. httpx was misclassified as dev-only but used by TeamsAdapter at runtime.
  - [x] 2.9: **Integration test fixture isolation** — `env_vars` autouse fixtures can overwrite real `DATABASE__URL`. Keep integration tests in separate `tests/integration/` with dedicated conftest.
  - [x] 2.10: **Settings cache clearing** — Must clear all `@lru_cache` singletons between tests: `get_settings.cache_clear()`, `create_async_engine_from_settings.cache_clear()`, `_get_session_factory.cache_clear()`, `get_llm_adapter.cache_clear()`, `get_email_adapter.cache_clear()`
  - [x] 2.11: **Dead code from LLM iterations** — Dev agent produces clean code but leaves traces of its own iterations (unused constants, stale classes, dead test methods). Review explicitly.

- [x] Task 3: Document conventions and quality gates (AC: 1)
  - [x] 3.1: **Naming conventions** — Python: PEP 8 strict (snake_case files/functions/vars, PascalCase classes, UPPER_SNAKE constants). DB: snake_case plural tables, `{singular}_id` FKs, `ix_/uq_/ck_/fk_/pk_` prefix conventions. Tests: `test_{behavior}_when_{condition}()` or `test_{behavior}_e2e()`.
  - [x] 3.2: **Quality gates** — mypy --strict (0 issues), ruff (select E/F/W/I/N/UP/B/A/SIM/TCH/RUF, line-length 120, target py312), pytest with pytest-asyncio `asyncio_mode = "auto"`, E2E tests excluded by default (`-m 'not e2e'`)
  - [x] 3.3: **Import conventions** — Absolute imports only (`from quote_agent.adapters.erp.protocol import ERPAdapter`). Never relative. Order: stdlib → third-party → local (Ruff enforces). Use `TYPE_CHECKING` blocks for import-only types.
  - [x] 3.4: **Project structure** — `src/quote_agent/` layout: adapters/ (4 types), agent/ (graph, state, nodes, tools), models/, services/, security/, audit/, cli/, api/. Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`.
  - [x] 3.5: **Configuration** — pydantic-settings with `__` nested delimiter. `get_settings()` cached singleton. Lazy module attribute for `from quote_agent.config import settings`.
  - [x] 3.6: **Structured logging** — JSON format with `timestamp`, `level`, `component` (dot notation matching Python path), `message`, `context` dict. Never confidential data in context.

- [x] Task 4: Write the `project-context.md` file (AC: 1, 2)
  - [x] 4.1: Create `docs/project-context.md` with all documented patterns, pitfalls, conventions, and quality gates
  - [x] 4.2: Organize for quick scanning: clear headings, bullet points, code examples where needed
  - [x] 4.3: Include a "Quick Reference" section at the top with the most critical patterns and pitfalls

- [x] Task 5: Verify completeness (AC: 1, 2)
  - [x] 5.1: Cross-reference against Epic 1 retrospective lessons learned (8 items)
  - [x] 5.2: Cross-reference against Epic 2 retrospective lessons learned (8 items)
  - [x] 5.3: Cross-reference against Epic 2 review feedback themes (dead code, string edge cases, module boundaries)
  - [x] 5.4: Cross-reference against architecture.md Implementation Patterns & Consistency Rules section
  - [x] 5.5: Verify no production code is modified — this story is purely additive (new docs file only)

## Dev Notes

### What This Story IS

This is a **documentation-only** story. The output is a single file: `docs/project-context.md`. No production code changes. No test changes. No new dependencies.

### What This Story Is NOT

- NOT a CLAUDE.md or AI-specific configuration file
- NOT an architecture document (that already exists)
- NOT a README — this is an internal developer reference
- NOT a style guide (ruff and mypy enforce style automatically)

### File to Create

```
docs/project-context.md
```

### Content Structure

The document should be organized in this order for maximum dev agent utility:

1. **Quick Reference** — 10-15 bullet points covering the most critical patterns and pitfalls
2. **Established Patterns** — Adapter, LLM structured output, pipeline integration, security layers, async
3. **Known Pitfalls** — Every anti-pattern and gotcha discovered in Epics 1-2, with the fix for each
4. **Conventions** — Naming, imports, project structure, testing, logging
5. **Quality Gates** — mypy strict, ruff config, test conventions, E2E requirements
6. **Tech Stack Summary** — Python 3.12+, uv, FastAPI, SQLAlchemy+Alembic, pydantic-settings, LangGraph, pytest

### Source Material

All content must be derived from the existing codebase and retrospectives — do NOT invent patterns:

- `src/quote_agent/adapters/llm/` — adapter pattern reference implementation
- `src/quote_agent/services/email_poller.py` — pipeline integration pattern
- `src/quote_agent/security/` — security layer pattern (sanitizer, input_isolation, log_redactor)
- `src/quote_agent/config.py` — configuration pattern
- `src/quote_agent/models/base.py` — DB session management, TimestampMixin, naming conventions
- `pyproject.toml` — quality gate configuration (ruff, mypy, pytest)
- `_bmad-output/implementation-artifacts/epic-1-retro-2026-03-18.md` — lessons 1-8
- `_bmad-output/implementation-artifacts/epic-2-retro-2026-03-19.md` — lessons 1-8, review themes
- `tests/e2e/conftest.py` — cache clearing pattern, E2E fixture setup

### Previous Story Intelligence (Story 3.0a)

**Key learnings from Story 3.0a:**
- `project_root` path calculation required 3 dirname levels (not 4) for alembic subprocess
- PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` columns require naive UTC datetimes in test fixtures (not timezone-aware)
- `requires_e2e` marker checks DB + LLM (not IMAP) since most E2E tests construct `IncomingEmail` directly
- Test naming follows `test_{behavior}_e2e()` pattern
- All `@lru_cache` singletons must be cleared between E2E tests

**Files from Story 3.0a:**
- `tests/e2e/conftest.py` — E2E fixtures and cache clearing pattern
- `tests/e2e/test_email_pipeline_e2e.py` — E2E test examples
- `tests/e2e/fixtures/emails.py` — test email factory functions

### What NOT to Do

- Do NOT modify any existing production code or test code
- Do NOT add new dependencies
- Do NOT create multiple files — single `docs/project-context.md` output
- Do NOT duplicate the architecture document — focus on practical patterns, pitfalls, and conventions that the dev agent needs during implementation
- Do NOT include project history, retrospective narratives, or delivery metrics — only actionable technical content
- Do NOT include TODOs or future plans — only document what exists NOW

### Project Structure Notes

- `docs/` directory may or may not exist — create it if needed
- `docs/E2E_TESTS.md` already exists (from Story 3.0a)
- The new file sits alongside existing docs, not in `_bmad-output/`

### References

- [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-03-18.md] — 8 lessons learned, 5 "what didn't go well" items
- [Source: _bmad-output/implementation-artifacts/epic-2-retro-2026-03-19.md] — 8 lessons learned, 5 "what didn't go well" items, established patterns section
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules] — naming, structure, format, communication patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries] — complete directory structure
- [Source: src/quote_agent/adapters/llm/] — adapter pattern (protocol.py, models.py, __init__.py with factory)
- [Source: src/quote_agent/services/email_poller.py] — pipeline pattern
- [Source: src/quote_agent/security/sanitizer.py] — security layer pattern (severity_max fix is the anti-pattern example)
- [Source: src/quote_agent/config.py] — pydantic-settings configuration
- [Source: src/quote_agent/models/base.py] — async engine, session factory, naming conventions
- [Source: pyproject.toml] — ruff/mypy/pytest configuration
- [Source: tests/e2e/conftest.py] — cache clearing, fixture patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — documentation-only story, no debug issues encountered.

### Completion Notes List

- Created `docs/project-context.md` with 6 major sections: Quick Reference, Established Patterns, Known Pitfalls, Conventions, Quality Gates, Tech Stack Summary
- Quick Reference contains 15 bullet points covering the most critical patterns and pitfalls
- Established Patterns documents 6 patterns: Adapter, LLM Structured Output, Pipeline Integration, Security Layer, Async, Configuration
- Known Pitfalls documents all 11 anti-patterns from subtasks 2.1–2.11 with fixes for each
- Conventions covers naming (Python, DB, tests), imports, project structure, structured logging
- Quality Gates documents exact mypy, ruff, and pytest configurations with enforcement rules
- Cross-referenced against Epic 1 retro (8 lessons), Epic 2 retro (8 lessons), review themes, and architecture.md
- No production or test code modified — purely additive story
- All 189 existing tests pass, no regressions

### Change Log

- 2026-03-19: Created `docs/project-context.md` — centralized developer reference for patterns, pitfalls, conventions, and quality gates derived from Epics 1-2
- 2026-03-19: [Code Review] Fixed 4 issues — clarified cache clearing list (M1), added 2 missing Epic 1 lessons: PEP 695 generics and BaseHTTPMiddleware (M2), noted embedding adapter scaffolding (L1), clarified TeamsAdapter health check timeout deviation (L2)

### File List

- `docs/project-context.md` (NEW) — centralized project context document
