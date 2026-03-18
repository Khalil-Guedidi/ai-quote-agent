# Story 1.1: Scaffolding Projet & Système de Configuration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator**,
I want the project initialized with the correct tech stack (Python 3.12+, uv, LangGraph) and a centralized type-safe configuration system (pydantic-settings),
So that all system parameters can be configured via environment variables and .env files with validation.

**This is the first production story. It transitions from the `prototype/` proof-of-concept to the real Python/LangGraph codebase in `src/quote_agent/`. Everything built here becomes the foundation for all subsequent stories.**

## Acceptance Criteria

1. **AC-1.1.1**: Project dependencies install cleanly
   - Given a fresh clone of the repository
   - When I run `uv sync`
   - Then all core dependencies are installed: langgraph, langchain-core, langchain-community, fastapi, uvicorn, sqlalchemy[asyncio], alembic, psycopg[binary], pgvector, python-dotenv, pydantic, pydantic-settings
   - And dev dependencies are available: pytest, pytest-asyncio, pytest-cov, ruff, mypy
   - And `uv run python -c "import quote_agent"` succeeds (package is importable)

2. **AC-1.1.2**: Configuration system loads from .env
   - Given a `.env.example` file exists with all required variables documented
   - When I copy it to `.env` and fill in required values
   - Then the configuration system loads and validates all settings with clear error messages for missing/invalid values
   - And the settings object is available via `from quote_agent.config import settings`

3. **AC-1.1.3**: Type-safe configuration access
   - Given the configuration system is loaded
   - When code accesses settings
   - Then it uses `settings.database_url`, `settings.llm_api_key`, etc. (never `os.getenv()`)
   - And all settings are typed (str, int, bool, etc.) with Pydantic validation
   - And nested config groups exist for: database, llm, erp, email, notification, app

4. **AC-1.1.4**: Invalid configuration fails fast
   - Given a `.env` with a missing required value (e.g., DATABASE_URL)
   - When the application starts
   - Then it fails immediately with a clear `ValidationError` listing all missing/invalid fields
   - And the error message tells the operator exactly what to fix

5. **AC-1.1.5**: Project structure matches architecture
   - Given the project is initialized
   - Then the `src/quote_agent/` directory structure exists with `__init__.py` files for all planned packages
   - And the package layout matches the architecture document's directory tree
   - And stub `__init__.py` files exist for: agent/, adapters/, memory/, search/, models/, services/, audit/, security/, api/, cli/

6. **AC-1.1.6**: Code quality tooling works
   - Given the project is initialized
   - When I run `uv run ruff check src/` and `uv run mypy src/`
   - Then both commands succeed with zero errors on the initial codebase
   - And `uv run pytest` discovers and runs tests (at minimum a smoke test)

## Tasks / Subtasks

- [x] Task 1: Initialize uv project and dependencies (AC: #1)
  - [x] 1.1: Run `uv init` at project root (alongside existing `prototype/`). Create `pyproject.toml` with project metadata: name=`ai-quote-agent`, python>=3.12, package name=`quote_agent`, src layout
  - [x] 1.2: Add core dependencies: `uv add langgraph langchain-core langchain-community psycopg[binary] pgvector "sqlalchemy[asyncio]" alembic fastapi uvicorn python-dotenv pydantic pydantic-settings` — NOTE: `sqlalchemy[asyncio]` extra is **required** (greenlet no longer installs by default since SQLAlchemy 2.1)
  - [x] 1.3: Add dev dependencies: `uv add --dev pytest pytest-asyncio pytest-cov ruff mypy`
  - [x] 1.4: Configure tool settings in `pyproject.toml`:
    - `[tool.ruff]` — target-version = "py312", line-length = 120, select all recommended rules
    - `[tool.mypy]` — strict = true, python_version = "3.12"
    - `[tool.pytest.ini_options]` — testpaths = ["tests"], asyncio_mode = "auto"
  - [x] 1.5: Verify `uv sync` succeeds and `uv run python -c "import quote_agent"` works

- [x] Task 2: Create project directory structure (AC: #5)
  - [x] 2.1: Create `src/quote_agent/` with `__init__.py` (version string)
  - [x] 2.2: Create all sub-packages with `__init__.py`:
    ```
    src/quote_agent/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── exceptions.py
    ├── agent/
    │   ├── __init__.py
    │   ├── nodes/__init__.py
    │   └── tools/__init__.py
    ├── adapters/
    │   ├── __init__.py
    │   ├── erp/__init__.py
    │   ├── llm/__init__.py
    │   ├── email/__init__.py
    │   ├── notification/__init__.py
    │   └── embedding/__init__.py
    ├── memory/__init__.py
    ├── search/__init__.py
    ├── models/__init__.py
    ├── services/__init__.py
    ├── audit/__init__.py
    ├── security/__init__.py
    ├── api/__init__.py
    └── cli/__init__.py
    ```
  - [x] 2.3: Each `__init__.py` should be empty (or contain `"""Package docstring."""` one-liner) — NO placeholder code, NO stub classes. Stub classes come in their respective stories.

- [x] Task 3: Implement configuration system (AC: #2, #3, #4)
  - [x] 3.1: Create `src/quote_agent/config.py` using pydantic-settings `BaseSettings`
  - [x] 3.2: Define settings groups as nested models:
    ```python
    class DatabaseSettings(BaseModel):
        url: str  # DATABASE_URL — PostgreSQL connection string
        echo: bool = False  # SQL echo for debugging

    class LLMSettings(BaseModel):
        api_key: SecretStr  # LLM_API_KEY
        base_url: str = "https://api.openai.com/v1"  # LLM_BASE_URL
        default_model: str = "gpt-4o"  # LLM_DEFAULT_MODEL
        simple_model: str = "gpt-4o-mini"  # LLM_SIMPLE_MODEL
        complex_model: str = "gpt-4o"  # LLM_COMPLEX_MODEL
        timeout: int = 60  # LLM_TIMEOUT seconds
        max_retries: int = 3  # LLM_MAX_RETRIES

    class ERPSettings(BaseModel):
        url: str  # ERP_URL — Odoo base URL
        database: str  # ERP_DATABASE
        username: str  # ERP_USERNAME
        api_key: SecretStr  # ERP_API_KEY

    class EmailSettings(BaseModel):
        imap_server: str  # EMAIL_IMAP_SERVER
        imap_port: int = 993  # EMAIL_IMAP_PORT
        username: str  # EMAIL_USERNAME
        password: SecretStr  # EMAIL_PASSWORD
        folder: str = "INBOX"  # EMAIL_FOLDER
        poll_interval: int = 60  # EMAIL_POLL_INTERVAL seconds

    class NotificationSettings(BaseModel):
        channel: str = "teams"  # NOTIFICATION_CHANNEL
        teams_webhook_url: str = ""  # NOTIFICATION_TEAMS_WEBHOOK_URL

    class AppSettings(BaseModel):
        name: str = "ai-quote-agent"
        version: str = "0.1.0"
        debug: bool = False  # APP_DEBUG
        log_level: str = "INFO"  # APP_LOG_LEVEL
        api_host: str = "0.0.0.0"  # APP_API_HOST
        api_port: int = 8000  # APP_API_PORT
    ```
  - [x] 3.3: Create root `Settings` class with `model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")` — environment variables use double underscore for nesting (e.g., `DATABASE__URL`, `LLM__API_KEY`)
  - [x] 3.4: Expose singleton: `settings = Settings()` at module level — importable as `from quote_agent.config import settings`
  - [x] 3.5: Use `SecretStr` for all sensitive values (api_key, password) — prevents accidental logging
  - [x] 3.6: Add custom validators where needed (e.g., `database.url` must start with `postgresql://` or `postgresql+asyncpg://`)

- [x] Task 4: Create .env.example (AC: #2)
  - [x] 4.1: Create `.env.example` at project root with ALL configuration variables, grouped by section, with comments explaining each
  - [x] 4.2: Include sensible defaults for non-sensitive values, placeholder hints for secrets (e.g., `LLM__API_KEY=sk-your-key-here`)
  - [x] 4.3: Document the env_nested_delimiter convention (`__`) in the file header

- [x] Task 5: Create exception hierarchy (AC: #5)
  - [x] 5.1: Create `src/quote_agent/exceptions.py` with the base exception hierarchy from the architecture:
    ```python
    class QuoteAgentError(Exception): ...
    class AdapterError(QuoteAgentError): ...
    class ERPConnectionError(AdapterError): ...
    class LLMTimeoutError(AdapterError): ...
    class EmailConnectionError(AdapterError): ...
    class NotificationError(AdapterError): ...
    class ValidationError(QuoteAgentError): ...
    class SecurityError(QuoteAgentError): ...
    class ConfigurationError(QuoteAgentError): ...
    ```

- [x] Task 6: Create minimal main.py (AC: #5)
  - [x] 6.1: Create `src/quote_agent/main.py` with a minimal FastAPI app creation function (`create_app() -> FastAPI`) — just enough to verify the project runs
  - [x] 6.2: Import and validate config on startup (fail fast if config is invalid)
  - [x] 6.3: Do NOT implement routes yet — just a bare FastAPI app. Routes come in Story 1.3.

- [x] Task 7: Write tests (AC: #6)
  - [x] 7.1: Create `tests/conftest.py` with shared fixtures
  - [x] 7.2: Create `tests/unit/test_config.py`:
    - `test_settings_load_from_env` — settings load from environment variables
    - `test_settings_fail_on_missing_required` — missing DATABASE__URL raises ValidationError
    - `test_settings_secret_str_not_exposed` — SecretStr values don't appear in repr/str
    - `test_settings_nested_delimiter` — double underscore nesting works (e.g., `DATABASE__URL`)
    - `test_settings_default_values` — defaults are applied for optional settings
  - [x] 7.3: Create `tests/unit/test_exceptions.py`:
    - `test_exception_hierarchy` — verify inheritance chain
  - [x] 7.4: Verify `uv run pytest` passes, `uv run ruff check src/ tests/`, `uv run mypy src/` all green

- [x] Task 8: Update .gitignore (AC: #5)
  - [x] 8.1: Update project root `.gitignore` to include Python-specific patterns: `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `dist/`, `*.egg-info/`, `.env` (but NOT `.env.example`)
  - [x] 8.2: Keep existing entries (prototype, .venv, etc.)

## Dev Notes

### Architecture Compliance

- **Package manager**: uv (NOT pip, NOT poetry). Use `uv add`, `uv sync`, `uv run`.
- **Source layout**: `src/quote_agent/` — standard src layout, NOT flat layout.
- **Python version**: 3.12+ required. Set in `pyproject.toml` `requires-python = ">=3.12"`.
- **Config approach**: pydantic-settings with `env_nested_delimiter="__"` — all config via env vars, loaded into typed Python objects. **Never use `os.getenv()` anywhere in the codebase.**
- **Naming conventions**: PEP 8 strictly enforced. Files: `snake_case.py`. Classes: `PascalCase`. Functions: `snake_case()`. Constants: `UPPER_SNAKE_CASE`.
- **Imports**: Absolute only — `from quote_agent.config import settings`. Never relative imports.
- **Type safety**: All functions must have typed parameters and return types. `mypy --strict` must pass.

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| `import os; os.getenv("API_KEY")` | `from quote_agent.config import settings; settings.llm.api_key` |
| `from ..config import settings` | `from quote_agent.config import settings` |
| `except Exception: pass` | Type the exception, log and re-raise |
| Add placeholder/stub code in `__init__.py` | Keep `__init__.py` empty — stubs come in their respective stories |
| Use pip or poetry | Use uv exclusively |
| Create `requirements.txt` for production | Dependencies live in `pyproject.toml` only |

### Relationship to Existing Prototype

The `prototype/` directory contains the n8n/Python proof-of-concept (Epic 0). It stays as-is — do NOT modify it. The new `src/quote_agent/` is the production codebase. They coexist at the project root:

```
ai-quote-agent/
├── prototype/           # Epic 0 — n8n PoC (read-only reference)
├── src/quote_agent/     # Epic 1+ — production code (NEW)
├── tests/               # production tests (NEW)
├── pyproject.toml       # production config (NEW)
└── .env.example         # production env template (NEW)
```

### Previous Story Intelligence (Epic 0 Learnings)

- **Odoo JSON-RPC pattern works well** — reuse the `execute_kw` pattern from `prototype/scripts/e2e-quote-pipeline.py` when building the Odoo adapter (Story 1.5)
- **Hybrid search validated**: 96.2% Hit@5 on dirty catalog (Story 0.4) — production search engine should follow the same vector+keyword strategy
- **LLM extraction reliable**: GPT-4o extraction on French industrial emails passed 5/5 scenarios (Story 0.5)
- **GO decision confirmed** in Story 0.6 — proceed to production build
- **Key prototype env vars** to mirror in production: `OPENAI_API_KEY`, `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD`, `QDRANT_URL` (Qdrant will be replaced by pgvector in production)

### Git Intelligence

Recent commits follow pattern: `feat: add <description> (Story X.Y)`. Production stories should follow: `feat: add <description> (Story 1.1)`.

Files at project root: `.gitignore` already exists — extend it, don't replace it.

### Project Structure Notes

- The architecture specifies a detailed directory tree in `architecture.md` lines 499-698. Follow it exactly for `src/quote_agent/`.
- `web-ui/` is NOT created in this story — it comes later (Epic 7).
- `alembic/` is NOT created in this story — it comes in Story 1.2.
- `Dockerfile` and `docker-compose.yml` are NOT created in this story — they come in Story 1.7.
- `.github/workflows/ci.yml` is NOT created in this story — it comes in Story 1.8.

### Testing Standards

- Tests live in `tests/` (not co-located), mirroring `src/` structure
- Naming: `test_{module}.py`, functions `test_{behavior}_when_{condition}()`
- Use pytest fixtures, not setUp/tearDown
- `pytest-asyncio` with `asyncio_mode = "auto"` for async tests
- Minimum: one unit test per public function in config.py and exceptions.py

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter-Template-Evaluation] — initialization commands, project structure
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns-&-Consistency-Rules] — naming, structure, format patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure-&-Boundaries] — complete directory tree
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1] — acceptance criteria, user story
- [Source: _bmad-output/planning-artifacts/prd.md#Configuration-&-Administration] — FR45-FR49
- [Source: _bmad-output/planning-artifacts/architecture.md#Core-Architectural-Decisions] — pydantic-settings, uv, Python 3.12+

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- uv 0.10.11 installed from astral.sh
- `uv init --lib --name quote-agent --package --python ">=3.12"` used for src layout
- ruff auto-fix applied for import sorting and unused imports
- mypy strict mode: removed unnecessary `type: ignore[call-arg]` comment
- Lazy singleton pattern via `__getattr__` for `settings` to avoid import-time failures without .env

### Completion Notes List

- Task 1: Project initialized with uv, all core + dev dependencies installed, tool configs in pyproject.toml. `uv sync` and `import quote_agent` both succeed.
- Task 2: Full directory structure created matching architecture spec — 14 sub-packages with minimal `__init__.py` docstrings.
- Task 3: pydantic-settings config system with 6 nested groups (DatabaseSettings, LLMSettings, ERPSettings, EmailSettings, NotificationSettings, AppSettings). SecretStr for sensitive values, field_validator on database URL. Lazy singleton via `get_settings()` with LRU cache + `__getattr__`.
- Task 4: `.env.example` created with all variables grouped by section, `__` nesting convention documented in header.
- Task 5: Exception hierarchy with 8 exception classes following architecture spec.
- Task 6: Minimal `main.py` with `create_app()` factory — validates config on startup, no routes.
- Task 7: 13 tests across 2 test files — all pass. ruff + mypy both green.
- Task 8: `.gitignore` extended with `.env`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`.

### Change Log

- 2026-03-18: Story 1.1 implemented — project scaffolding, configuration system, exception hierarchy, tests, tooling

### File List

- pyproject.toml (new)
- uv.lock (new)
- .python-version (new)
- .env.example (new)
- README.md (new, from uv init)
- .gitignore (modified)
- src/quote_agent/__init__.py (modified)
- src/quote_agent/py.typed (new, from uv init)
- src/quote_agent/config.py (new)
- src/quote_agent/exceptions.py (new)
- src/quote_agent/main.py (new)
- src/quote_agent/agent/__init__.py (new)
- src/quote_agent/agent/nodes/__init__.py (new)
- src/quote_agent/agent/tools/__init__.py (new)
- src/quote_agent/adapters/__init__.py (new)
- src/quote_agent/adapters/erp/__init__.py (new)
- src/quote_agent/adapters/llm/__init__.py (new)
- src/quote_agent/adapters/email/__init__.py (new)
- src/quote_agent/adapters/notification/__init__.py (new)
- src/quote_agent/adapters/embedding/__init__.py (new)
- src/quote_agent/memory/__init__.py (new)
- src/quote_agent/search/__init__.py (new)
- src/quote_agent/models/__init__.py (new)
- src/quote_agent/services/__init__.py (new)
- src/quote_agent/audit/__init__.py (new)
- src/quote_agent/security/__init__.py (new)
- src/quote_agent/api/__init__.py (new)
- src/quote_agent/cli/__init__.py (new)
- tests/__init__.py (new)
- tests/conftest.py (new)
- tests/unit/__init__.py (new)
- tests/unit/test_config.py (new)
- tests/unit/test_exceptions.py (new)
