# Story 1.2: Base de Données PostgreSQL & Migrations

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator**,
I want a PostgreSQL+pgvector database with Alembic migration management,
So that the system has a versioned, reliable data store ready for application tables.

**This is the database foundation story. It sets up the async SQLAlchemy engine, session management, Alembic migration infrastructure, and the initial migration that enables pgvector. Everything built here is consumed by every subsequent story that touches the database.**

## Acceptance Criteria

1. **AC-1.2.1**: Alembic migrations run successfully
   - Given a PostgreSQL instance is configured in `.env` (via `DATABASE__URL`)
   - When I run `alembic upgrade head`
   - Then the database is initialized with pgvector extension enabled (`CREATE EXTENSION IF NOT EXISTS vector`)
   - And the initial migration creates the `alembic_version` schema tracking table
   - And the migration completes without errors

2. **AC-1.2.2**: Async SQLAlchemy session management works
   - Given the database connection is configured via `DATABASE__URL` in `.env`
   - When the application creates an async session
   - Then SQLAlchemy connects successfully using `AsyncSession` with `asyncpg` driver
   - And connection parameters come from `settings.database.url` (pydantic-settings)
   - And the session factory is available via `from quote_agent.models.base import get_async_session`

3. **AC-1.2.3**: Database URL auto-conversion for async driver
   - Given `DATABASE__URL=postgresql://user:pass@host/db` in `.env`
   - When the async engine is created
   - Then the URL is automatically converted to `postgresql+asyncpg://user:pass@host/db`
   - And users never need to manually specify `+asyncpg` in the env var

4. **AC-1.2.4**: pgvector extension is available
   - Given Alembic migrations have been applied
   - When a model defines a `Vector` column
   - Then it can store and query vector embeddings using pgvector operators
   - And HNSW index creation is supported

5. **AC-1.2.5**: SQLAlchemy Base model with common mixins
   - Given the base model module exists
   - Then a `Base` declarative base is available with a `TimestampMixin` providing `created_at` and `updated_at` columns
   - And all future models inherit from this `Base`
   - And the naming convention for constraints/indexes follows the architecture patterns

6. **AC-1.2.6**: Tests pass against real PostgreSQL
   - Given a test PostgreSQL instance is available
   - When I run `uv run pytest tests/unit/test_database.py`
   - Then all database tests pass (engine creation, session lifecycle, pgvector availability)
   - And `uv run ruff check src/ tests/` and `uv run mypy src/` both succeed

## Tasks / Subtasks

- [x] Task 1: Create SQLAlchemy Base and engine module (AC: #2, #3, #5)
  - [x] 1.1: Create `src/quote_agent/models/base.py` with:
    - `Base` = `DeclarativeBase` with `metadata` using naming convention (see Dev Notes)
    - `TimestampMixin` mapped mixin with `created_at: Mapped[datetime]` (server_default=`func.now()`) and `updated_at: Mapped[datetime]` (server_default=`func.now()`, onupdate=`func.now()`)
    - `async_engine` factory function that creates `AsyncEngine` from `settings.database.url`
    - `AsyncSessionLocal` = `async_sessionmaker` bound to engine
    - `get_async_session()` async generator yielding `AsyncSession` (for FastAPI dependency injection)
  - [x] 1.2: In the engine factory, auto-convert `postgresql://` to `postgresql+asyncpg://` so operators only need to set `DATABASE__URL=postgresql://...` in `.env`
  - [x] 1.3: Pass `echo=settings.database.echo` to the engine for SQL debugging when needed

- [x] Task 2: Initialize Alembic with async template (AC: #1)
  - [x] 2.1: Run `alembic init -t async alembic` at project root to generate async-aware scaffold
  - [x] 2.2: Edit `alembic.ini`:
    - Set `script_location = alembic`
    - Remove hardcoded `sqlalchemy.url` (will be set dynamically in `env.py`)
  - [x] 2.3: Edit `alembic/env.py`:
    - Import `Settings` from `quote_agent.config` and set `sqlalchemy.url` dynamically from `settings.database.url` (converted to asyncpg)
    - Set `target_metadata = Base.metadata` (import from `quote_agent.models.base`)
    - Import all model modules so autogenerate discovers them (initially just base)
    - The async template already uses `async_engine_from_config` + `connection.run_sync()` — verify this is in place

- [x] Task 3: Create initial migration — pgvector extension (AC: #1, #4)
  - [x] 3.1: Generate migration: `alembic revision --autogenerate -m "enable pgvector extension"`
  - [x] 3.2: Edit the generated migration to add `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` in `upgrade()` and `op.execute("DROP EXTENSION IF EXISTS vector")` in `downgrade()`
  - [x] 3.3: Verify migration runs: `alembic upgrade head` against a local PostgreSQL instance

- [x] Task 4: Write tests (AC: #6)
  - [x] 4.1: Create `tests/unit/test_database.py` with:
    - `test_async_engine_creation` — engine is created from settings with asyncpg driver
    - `test_url_conversion_postgresql_to_asyncpg` — `postgresql://` is auto-converted to `postgresql+asyncpg://`
    - `test_url_passthrough_asyncpg` — `postgresql+asyncpg://` is left unchanged
    - `test_timestamp_mixin_fields` — TimestampMixin has `created_at` and `updated_at` mapped columns
    - `test_naming_convention` — Base.metadata.naming_convention matches architecture spec
    - `test_session_lifecycle` — async session opens and closes cleanly (requires real PostgreSQL)
    - `test_pgvector_extension_available` — can execute `SELECT 'vector'::regtype` (requires real PostgreSQL after migration)
  - [x] 4.2: Add a `conftest.py` fixture for test database setup (use env var `DATABASE__URL` or a test-specific override)
  - [x] 4.3: Verify `uv run ruff check src/ tests/`, `uv run mypy src/` all pass

- [x] Task 5: Update `.env.example` (AC: #1)
  - [x] 5.1: Add a comment section for database migration commands:
    ```
    # Database migrations (run after setting DATABASE__URL):
    #   alembic upgrade head    — apply all migrations
    #   alembic revision --autogenerate -m "description"  — create new migration
    #   alembic downgrade -1    — rollback last migration
    ```

## Dev Notes

### Architecture Compliance

- **Database**: PostgreSQL + pgvector — single DB for relational + vector data. [Source: architecture.md#Data-Architecture]
- **ORM**: SQLAlchemy 2.0.48 with async support (`sqlalchemy[asyncio]`). Use `DeclarativeBase` (SQLAlchemy 2.x style), NOT legacy `declarative_base()`.
- **Migrations**: Alembic 1.18.4 with async template. Use `alembic init -t async alembic`.
- **Driver**: `psycopg[binary]>=3.3.3` is installed but for async we need `asyncpg`. The architecture uses `postgresql+asyncpg://` for async sessions. **Verify** if `asyncpg` needs to be added as a dependency or if the existing `sqlalchemy[asyncio]` extra covers the async engine with psycopg3. If not, `uv add asyncpg`.
- **pgvector**: `pgvector>=0.4.2` already installed. Use `from pgvector.sqlalchemy import Vector` for vector column types. HNSW index type for 50K product refs.
- **Config**: All DB config comes from `settings.database.url` and `settings.database.echo` (defined in `DatabaseSettings` in `src/quote_agent/config.py`). **Never hardcode** connection strings.

### Database Naming Convention

The SQLAlchemy `MetaData` naming convention MUST be set on `Base.metadata` to match the architecture spec:

```python
convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

This ensures Alembic auto-generates predictable constraint names. [Source: architecture.md#Naming-Patterns — `ix_{table}_{columns}`, `uq_{table}_{columns}`, `ck_{table}_{condition}`]

### Async Engine Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

def _ensure_async_url(url: str) -> str:
    """Convert postgresql:// to postgresql+asyncpg:// if needed."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

engine = create_async_engine(_ensure_async_url(settings.database.url), echo=settings.database.echo)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Alembic env.py Key Points

- Alembic's async template uses `run_async_migrations()` wrapping `connection.run_sync(do_run_migrations)`. Migration functions themselves remain **synchronous** — only the engine connection is async.
- Set `sqlalchemy.url` dynamically from config, NOT from `alembic.ini`. This keeps the single source of truth in `.env`.
- Import `Base.metadata` as `target_metadata` for autogenerate support.
- Import all model modules at the top of `env.py` so Alembic discovers table definitions (for now, only `quote_agent.models.base`).

### pgvector Setup

- The initial migration enables the extension: `CREATE EXTENSION IF NOT EXISTS vector`
- This requires the PostgreSQL instance to have pgvector installed (via `apt install postgresql-16-pgvector` or Docker image `pgvector/pgvector:pg16`)
- Vector columns are NOT created in this story — they come in Story 3.2 when the products table is created
- For testing, use a PostgreSQL instance with pgvector available (Docker recommended: `pgvector/pgvector:pg16`)

### File Locations

```
ai-quote-agent/
├── alembic.ini                          # NEW — Alembic config (project root)
├── alembic/                             # NEW — Alembic migration directory
│   ├── env.py                           # EDIT — async engine, dynamic URL from settings
│   ├── script.py.mako                   # GENERATED — migration template
│   └── versions/                        # GENERATED — migration files
│       └── xxxx_enable_pgvector.py      # NEW — initial migration
├── src/quote_agent/
│   └── models/
│       ├── __init__.py                  # EXISTS (empty) — leave as-is for now
│       └── base.py                      # NEW — Base, TimestampMixin, engine, session
└── tests/
    └── unit/
        └── test_database.py             # NEW — database infrastructure tests
```

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Use `declarative_base()` (legacy) | Use `class Base(DeclarativeBase)` (SQLAlchemy 2.x) |
| Hardcode DB URL in `alembic.ini` | Set dynamically in `env.py` from `quote_agent.config` |
| Use sync engine for production code | Use `create_async_engine` + `AsyncSession` everywhere |
| Create any table models in this story | Only `Base`, `TimestampMixin`, engine, session — tables come in later stories |
| Use `from ..models.base import Base` | Use `from quote_agent.models.base import Base` (absolute imports) |
| Skip the `_ensure_async_url` conversion | Operators should not need to know about `+asyncpg` — auto-convert |
| Put the `CREATE EXTENSION` in Python code | Put it in the Alembic migration — schema changes belong in migrations |

### Previous Story Intelligence (Story 1.1)

- **Lazy singleton pattern**: `settings` uses `__getattr__` + `lru_cache` — safe to import at module level, loads on first access
- **Config validator**: `DatabaseSettings.url` has `field_validator` requiring `postgresql://` or `postgresql+asyncpg://` prefix — the async URL conversion in `base.py` is compatible with both accepted prefixes
- **Existing packages**: `src/quote_agent/models/__init__.py` already exists (empty) — add `base.py` alongside it
- **Tests pattern**: Tests use `monkeypatch.setenv()` for env vars, no `.env` file needed in tests. See `tests/unit/test_config.py` for the established pattern.
- **Ruff + mypy**: Both configured in `pyproject.toml`. `mypy --strict` enforced — all functions need type annotations.
- **Dev dependencies**: `pytest-asyncio` with `asyncio_mode = "auto"` already configured — async test functions work out of the box.

### Git Intelligence

- Commit pattern: `feat: add <description> (Story 1.2)`
- Latest commit: `7f9383a feat: add project scaffolding & type-safe configuration system (Story 1.1)` — this story directly builds on that foundation

### Testing Standards

- Tests in `tests/unit/test_database.py` (mirroring `src/quote_agent/models/base.py`)
- Naming: `test_{behavior}_when_{condition}()`
- Use `pytest-asyncio` for async tests — `async def test_...` functions work automatically
- For tests requiring a real PostgreSQL: mark with `@pytest.mark.skipif` if `DATABASE__URL` is not set, or use a test fixture that provides a temporary database
- Minimum: one unit test per public function (`create_async_engine_from_settings`, `get_async_session`, `_ensure_async_url`, `TimestampMixin` fields, naming convention)

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Data-Architecture] — PostgreSQL + pgvector, HNSW, Alembic
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming-Patterns] — database table/column/index/constraint naming
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure-&-Boundaries] — alembic/, models/ file locations
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns-&-Consistency-Rules] — enforcement guidelines, anti-patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2] — acceptance criteria, user story
- [Source: _bmad-output/implementation-artifacts/1-1-scaffolding-projet-systeme-de-configuration.md] — previous story learnings, file list, config patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- asyncpg not in dependencies — added via `uv add asyncpg` (asyncpg==0.31.0)
- TimestampMixin is not a mapped class by itself — cannot use `sqlalchemy.inspect()` on it; tested via attribute/descriptor checks instead
- Task 3.3 (alembic upgrade head): verified successfully against real PostgreSQL+pgvector (docker: pgvector/pgvector:pg16)
- Integration tests initially failed because autouse `env_vars` fixture overwrote real DATABASE__URL with fake credentials — moved integration tests to `tests/integration/` with dedicated conftest
- Pre-existing `test_settings_fail_on_missing_required` was fragile (assumed no `.env` file) — fixed by using `_env_file=None` parameter

### Completion Notes List

- ✅ Task 1: Created `src/quote_agent/models/base.py` with Base (DeclarativeBase), TimestampMixin, `_ensure_async_url`, `create_async_engine_from_settings`, `_get_session_factory`, `get_async_session`. All using SQLAlchemy 2.x patterns.
- ✅ Task 2: Initialized Alembic with async template. Configured `alembic.ini` (removed hardcoded URL) and `alembic/env.py` (dynamic URL from settings, Base.metadata for autogenerate).
- ✅ Task 3: Created initial migration `c740a66c4ad2_enable_pgvector_extension.py` with `CREATE EXTENSION IF NOT EXISTS vector` in upgrade and `DROP EXTENSION IF EXISTS vector` in downgrade.
- ✅ Task 4: Created `tests/unit/test_database.py` (6 unit tests) + `tests/integration/test_database_integration.py` (2 integration tests against real PostgreSQL+pgvector). All 21 tests pass. ruff + mypy clean.
- ✅ Task 5: Added migration command reference comments to `.env.example`.
- ✅ Bonus: Added `docker-compose.yml` (pgvector/pgvector:pg16), configured `.env`, ran `alembic upgrade head` successfully, all integration tests green.

### Change Log

- 2026-03-18: Story 1.2 implementation complete — database foundation with async SQLAlchemy, Alembic migrations, and pgvector extension
- 2026-03-18: Code review fixes — cached engine/session factory singletons (H1), integration conftest uses env var directly (M1), removed unused sa import from migration (L1)

### File List

- `src/quote_agent/models/base.py` — NEW: Base, TimestampMixin, async engine/session management
- `alembic.ini` — NEW: Alembic configuration (dynamic URL from settings)
- `alembic/env.py` — EDIT: async engine, dynamic URL, Base.metadata for autogenerate
- `alembic/script.py.mako` — GENERATED: migration template
- `alembic/README` — GENERATED: Alembic README
- `alembic/versions/c740a66c4ad2_enable_pgvector_extension.py` — NEW: initial migration enabling pgvector
- `tests/unit/test_database.py` — NEW: database unit tests (6 tests)
- `tests/integration/__init__.py` — NEW: integration tests package
- `tests/integration/conftest.py` — NEW: integration test fixtures (real DB detection)
- `tests/integration/test_database_integration.py` — NEW: integration tests (session lifecycle, pgvector)
- `tests/unit/test_config.py` — FIX: made test_settings_fail_on_missing_required robust with `_env_file=None`
- `.env.example` — EDIT: added migration commands reference
- `.env` — NEW: configured with real PostgreSQL credentials for local dev
- `docker-compose.yml` — NEW: PostgreSQL+pgvector service for local development
- `pyproject.toml` — EDIT: added asyncpg dependency
- `uv.lock` — EDIT: updated lock file with asyncpg
