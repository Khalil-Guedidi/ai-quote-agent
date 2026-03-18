# Story 1.7: Deploiement Docker & Outils CLI

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator (Laurent)**,
I want to deploy the entire system via Docker Compose and manage it through CLI commands,
So that I can operate the system on client infrastructure with minimal effort.

## Acceptance Criteria

1. **AC-1.7.1**: Docker Compose starts the full stack
   - Given a server with Docker installed
   - When I run `docker compose up -d`
   - Then two services start: `app` container (FastAPI) and `postgres` container (PostgreSQL + pgvector)
   - And the app container uses a multi-stage Docker build (uv dependency install → Python app)
   - And the PostgreSQL container has pgvector extension available (already the case with `pgvector/pgvector:pg16`)
   - And the app container waits for PostgreSQL to be healthy before starting (`depends_on` with `condition: service_healthy`)

2. **AC-1.7.2**: Dockerfile uses multi-stage build with uv
   - Given the Dockerfile exists
   - When Docker builds the image
   - Then it uses a multi-stage build: builder stage installs dependencies with `uv sync --locked --no-editable`, final stage copies only `.venv` (no uv, no build tools)
   - And `UV_COMPILE_BYTECODE=1` is set for production bytecode compilation
   - And `UV_LINK_MODE=copy` is set to avoid symlink issues with cache mounts
   - And the final image runs as a non-root user

3. **AC-1.7.3**: Docker HEALTHCHECK calls /health
   - Given the Dockerfile exists
   - When Docker builds the image
   - Then the HEALTHCHECK instruction calls `curl http://localhost:8000/health` (or equivalent) and reports container health
   - And `docker ps` shows the container health status

4. **AC-1.7.4**: CLI `agent status` shows per-service health
   - Given the system is running
   - When I run `agent status` (CLI via Typer)
   - Then I see per-service health status (database, llm, erp, email, notification)
   - And the output is formatted for human readability (colored status indicators)

5. **AC-1.7.5**: CLI `agent logs` shows structured log output
   - Given the system is running
   - When I run `agent logs` (CLI)
   - Then I see structured JSON log output from the application
   - And the command supports a `--follow` flag for tailing logs
   - And the command supports a `--lines N` flag to limit output

6. **AC-1.7.6**: CLI entry point is registered
   - Given the package is installed
   - When I run `agent --help`
   - Then I see available commands: `status`, `logs`
   - And the CLI is registered as a `[project.scripts]` entry point in `pyproject.toml`

7. **AC-1.7.7**: Tests pass
   - Given the test suite exists
   - When I run `uv run pytest tests/unit/test_cli.py`
   - Then all CLI tests pass (status command, logs command, help output)
   - And `uv run ruff check src/ tests/` and `uv run mypy src/` both succeed

## Tasks / Subtasks

- [x] Task 1: Create Dockerfile with multi-stage build (AC: 1, 2, 3)
  - [x] 1.1: Create `Dockerfile` at project root with multi-stage build:
    - **Builder stage**: `python:3.12-slim` base, copy uv from `ghcr.io/astral-sh/uv:0.10.9`, install dependencies with `uv sync --locked --no-install-project --no-editable`, then copy source and `uv sync --locked --no-editable`
    - **Final stage**: `python:3.12-slim` base, copy only `.venv` from builder, create non-root `appuser`, set `HEALTHCHECK`, set entrypoint to run uvicorn via `.venv/bin/python`
  - [x] 1.2: Set environment variables: `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy`
  - [x] 1.3: Add `HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` (no curl dependency needed — use Python stdlib)
  - [x] 1.4: Final image runs as non-root user (`appuser`)

- [x] Task 2: Update docker-compose.yml with app service (AC: 1)
  - [x] 2.1: Add `app` service to existing `docker-compose.yml`:
    - Build from `Dockerfile` in project root
    - Expose port 8000
    - `depends_on: postgres: condition: service_healthy`
    - Mount `.env` file (or use `env_file: .env`)
    - Set `DATABASE__URL` to point to `postgres` service hostname
  - [x] 2.2: Keep existing `postgres` service unchanged (already has healthcheck)
  - [x] 2.3: Add app service healthcheck mirroring the Dockerfile HEALTHCHECK

- [x] Task 3: Add Typer dependency (AC: 4, 5, 6)
  - [x] 3.1: Run `uv add typer` to add Typer as a project dependency
  - [x] 3.2: Add `[project.scripts]` entry in `pyproject.toml`: `agent = "quote_agent.cli.main:app"`

- [x] Task 4: Create CLI entry point and `status` command (AC: 4, 6)
  - [x] 4.1: Create `src/quote_agent/cli/main.py` with Typer app:
    - `app = typer.Typer(name="agent", help="AI Quote Agent CLI")`
    - Register sub-commands from `status` and `logs` modules
  - [x] 4.2: Create `src/quote_agent/cli/status.py`:
    - `agent status` command
    - Makes HTTP GET request to `http://localhost:{port}/health` using `httpx` (already a dev dependency — but need as runtime for CLI; use `urllib.request` from stdlib instead to avoid adding httpx as non-dev dependency)
    - Parses JSON response, displays per-service health with colored output (Typer's `typer.style()` / Rich integration)
    - Accepts `--host` and `--port` options (default `localhost:8000`)
    - Handles connection errors gracefully (app not running → clear error message)

- [x] Task 5: Create CLI `logs` command (AC: 5)
  - [x] 5.1: Create `src/quote_agent/cli/logs.py`:
    - `agent logs` command
    - Reads Docker container logs via `docker logs quote-agent-app` subprocess call
    - Supports `--follow` / `-f` flag (maps to `docker logs --follow`)
    - Supports `--lines N` / `-n N` flag (maps to `docker logs --tail N`, default 100)
    - Handles missing container gracefully

- [x] Task 6: Write tests (AC: 7)
  - [x] 6.1: Create `tests/unit/test_cli.py` with:
    - `test_cli_help_shows_commands` — invoke `agent --help` via Typer's `CliRunner`, verify `status` and `logs` appear
    - `test_status_command_healthy` — mock HTTP response with healthy services, verify formatted output
    - `test_status_command_degraded` — mock HTTP response with unhealthy service, verify degraded display
    - `test_status_command_connection_error` — mock connection failure, verify error message
    - `test_logs_command_default` — mock subprocess call, verify `docker logs --tail 100` invoked
    - `test_logs_command_follow` — mock subprocess, verify `--follow` flag passed
  - [x] 6.2: Verify `uv run ruff check src/ tests/` and `uv run mypy src/` both pass

## Dev Notes

### Architecture Compliance

- **CLI framework**: Typer — recommended in architecture.md ("Typer recommended — decide in first CLI story"). [Source: architecture.md#CLI-framework-not-chosen]
- **CLI layer boundaries**: CLI calls services or API via HTTP to self — never calls adapters directly. [Source: architecture.md#Layered-Architecture]
- **No `print()`**: Use Typer's `typer.echo()` or Rich console for output. [Source: architecture.md#Code-Quality-Mandates]
- **Docker Compose**: Two services only — app container + PostgreSQL container. [Source: architecture.md#Infrastructure-Decisions]
- **Multi-stage build**: Frontend build → Python app (NOTE: no frontend exists yet — Story 7.4+ will add React/Vite. For now, the multi-stage build is Python-only: builder installs deps, final stage copies .venv). [Source: architecture.md#Infrastructure-Decisions]
- **HEALTHCHECK**: `/health` endpoint for Docker HEALTHCHECK, CLI `agent status`, and web UI dashboard. [Source: architecture.md#Communication-Decisions]
- **Stateless design**: App container is stateless — all state in PostgreSQL. Multiple instances can run behind a load balancer. [Source: architecture.md#Infrastructure-Decisions]

### Docker Build Key Facts

- **Base image**: `python:3.12-slim` — matches project's `requires-python = ">=3.12"`
- **uv in Docker**: Copy uv binary from official image `ghcr.io/astral-sh/uv:0.10.9` (pin version for reproducible builds)
- **Multi-stage pattern**:
  1. Builder stage: install deps with `uv sync --locked --no-install-project --no-editable` (deps layer), then copy source and `uv sync --locked --no-editable` (app layer)
  2. Final stage: copy `.venv` only — no uv, no build tools, no source code (installed as non-editable package in .venv)
- **Environment variables**: `UV_COMPILE_BYTECODE=1` (bytecode compilation for faster startup), `UV_LINK_MODE=copy` (required with cache mounts)
- **Cache mounts**: Use `--mount=type=cache,target=/root/.cache/uv` for faster rebuilds
- **Non-root user**: Create `appuser` in final stage, `chown` the `.venv`, run as `appuser`
- **HEALTHCHECK without curl**: Use `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` — avoids adding curl to slim image
- **No frontend yet**: Architecture mentions "Multi-stage: build frontend → install Python → run" but no frontend exists (Epic 7). Skip frontend stage for now — add it in Epic 7's stories

### Typer CLI Key Facts

- **Latest version**: Typer 0.24.1 (Feb 2026) — built on Click, type-hint driven
- **Rich integration**: Typer has built-in Rich support for colored output. Use `typer.echo()` or `rich.print()` for formatted status display
- **Entry point**: Register via `[project.scripts]` in `pyproject.toml`: `agent = "quote_agent.cli.main:app"`
- **Testing**: Use `typer.testing.CliRunner` — same pattern as Click's test runner
- **No async needed in CLI**: CLI commands are synchronous — they make HTTP calls to the running FastAPI server or execute subprocess commands

### Docker Compose Integration

The existing `docker-compose.yml` has only the `postgres` service. This story adds the `app` service:

```yaml
services:
  app:
    build: .
    container_name: quote-agent-app
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      DATABASE__URL: postgresql+asyncpg://quote_agent:quote_agent_secret@postgres:5432/quote_agent
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3

  postgres:
    # ... existing config unchanged
```

**Key**: The `DATABASE__URL` environment variable in compose overrides the `.env` value to use `postgres` as hostname (Docker network DNS). The scheme must be `postgresql+asyncpg://` to match the asyncpg driver used by SQLAlchemy.

### CLI `status` Command Design

The `status` command calls `GET http://localhost:{port}/health` and formats the response:

```
Agent Status
─────────────
Overall: healthy ✓

Services:
  database      healthy ✓
  llm           healthy ✓
  erp           unhealthy ✗  Connection refused
  email         healthy ✓
  notification  healthy ✓
```

Use `urllib.request` from stdlib (not httpx) to avoid promoting httpx from dev to runtime dependency. Alternatively, httpx could be moved to runtime deps since it's already used by the notification adapter (TeamsAdapter uses `httpx.AsyncClient`).

**Decision**: Check if httpx is already a runtime dependency. Looking at `pyproject.toml` — it's in `[dependency-groups] dev` only. BUT the notification adapter (`teams.py`) imports httpx at runtime. This means httpx should actually be a runtime dependency. Move `httpx` from dev to main dependencies, then use it in CLI too.

### Existing Code to Build On

| File | What Exists | What to Do |
|------|-------------|------------|
| `docker-compose.yml` | PostgreSQL service only | Add `app` service |
| `src/quote_agent/cli/__init__.py` | Empty package placeholder (`"""Package cli."""`) | Keep as-is |
| `src/quote_agent/cli/` | Empty directory with `__init__.py` | Add `main.py`, `status.py`, `logs.py` |
| `src/quote_agent/config.py` | `AppSettings` with `api_host`, `api_port` | Use for CLI default host/port |
| `src/quote_agent/api/health.py` | `/health` endpoint returning per-service status | CLI `status` calls this |
| `pyproject.toml` | Project config, no `[project.scripts]` | Add `agent` script entry |
| `.env.example` | All env vars documented | Already complete — no changes needed |

### Testing Pattern

Test CLI commands using Typer's `CliRunner`:

```python
from typer.testing import CliRunner
from quote_agent.cli.main import app

runner = CliRunner()

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "logs" in result.output

def test_status_healthy(monkeypatch):
    # Mock urllib.request.urlopen or httpx.get to return healthy response
    mock_response = {
        "data": {
            "status": "healthy",
            "services": {
                "database": {"status": "healthy", "error": None},
                "llm": {"status": "healthy", "error": None},
                # ...
            }
        },
        "meta": {"timestamp": "2026-03-18T10:00:00Z"}
    }
    # ... mock and assert formatted output
```

For `logs` command, mock `subprocess.run` / `subprocess.Popen`:

```python
from unittest.mock import patch

def test_logs_default(monkeypatch):
    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["logs"])
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "docker" in args
        assert "--tail" in args
        assert "100" in args
```

### File Locations

```
ai-quote-agent/
├── Dockerfile                              # NEW — Multi-stage build with uv
├── docker-compose.yml                      # MODIFY — add app service
├── pyproject.toml                          # MODIFY — add typer dep + [project.scripts]
├── src/quote_agent/
│   └── cli/
│       ├── __init__.py                     # EXISTS — keep as-is
│       ├── main.py                         # NEW — CLI entry point (Typer app)
│       ├── status.py                       # NEW — agent status command
│       └── logs.py                         # NEW — agent logs command
└── tests/
    └── unit/
        └── test_cli.py                     # NEW — CLI command tests
```

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Use `print()` in CLI commands | Use `typer.echo()` or Rich console |
| Make CLI commands async | Keep CLI synchronous — HTTP calls to running server |
| Add curl to Docker image | Use Python stdlib `urllib.request` for HEALTHCHECK |
| Run as root in Docker | Create `appuser`, run as non-root |
| Copy uv into final stage | Multi-stage: uv only in builder stage |
| Include dev dependencies in Docker image | `uv sync --locked --no-editable` installs only production deps (no `--dev` flag) |
| Hardcode localhost:8000 in CLI | Accept `--host` and `--port` options with defaults from config or hardcoded defaults |
| Use `docker compose logs` in the `logs` command | Use `docker logs <container>` — the CLI should work independently of compose |
| Include a frontend build stage | No frontend exists yet (Epic 7) — Python-only multi-stage for now |
| Use `latest` tag for uv image | Pin to specific version `ghcr.io/astral-sh/uv:0.10.9` for reproducibility |

### Previous Story Intelligence (Story 1.6)

- **httpx is used at runtime** by `TeamsAdapter` in `adapters/notification/teams.py` but is listed as a dev dependency in `pyproject.toml`. This story should move `httpx` to main dependencies since it's genuinely needed at runtime (notification adapter + CLI status command).
- **All 60 tests pass** after Story 1.6 — baseline is clean.
- **Health endpoint checks 5 services**: database, llm, erp, email, notification. CLI `status` command should display all 5.
- **Adapter factory pattern**: `get_*_adapter()` functions use `@lru_cache` — these are FastAPI dependencies injected into health endpoint. CLI doesn't use these directly — it calls the HTTP endpoint.
- **conftest.py `create_test_app()`**: Already handles clearing adapter caches. CLI tests don't need this since they don't test the FastAPI app directly.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Most recent commits:
- `057aafc` feat: add LinkedIn dirty data problem post (Story T.3)
- `c6c8ea1` feat: add Teams notification adapter with webhook health check (Story 1.6)
- `4a6b980` feat: add ERP and email adapter configuration with health checks (Story 1.5)

### Dependencies to Add

- **`typer`** (runtime): CLI framework. `uv add typer`
- **Move `httpx`** from dev to runtime: Already used by notification adapter at runtime. `uv add httpx` then remove from dev group.

### Scope Boundaries

- **IN scope**: Dockerfile (multi-stage, uv, non-root, HEALTHCHECK), docker-compose.yml app service, Typer CLI entry point, `agent status` command, `agent logs` command, `[project.scripts]` registration, CLI tests, httpx dependency fix
- **OUT of scope**: Frontend build stage in Dockerfile (no frontend yet — Epic 7), `agent deploy` command (not needed for MVP — `docker compose up` is the deploy command), `agent config` command (deferred), `agent notify` command (Epic 5), CI/CD pipeline (Story 1.8), Docker image registry push (Story 1.8), production Docker optimizations (security scanning, image signing), Kubernetes/Swarm orchestration

### References

- [Source: architecture.md#Infrastructure-Decisions] — Docker Compose: app + PostgreSQL, multi-stage build
- [Source: architecture.md#Communication-Decisions] — /health for Docker HEALTHCHECK + CLI + web UI
- [Source: architecture.md#Layered-Architecture] — CLI layer calls services/config/api via HTTP
- [Source: architecture.md#Complete-Project-Directory-Structure] — cli/ directory with main.py, deploy.py, status.py, logs.py
- [Source: architecture.md#CLI-framework-not-chosen] — Typer recommended
- [Source: architecture.md#Code-Quality-Mandates] — no print(), no bare except, typed everything
- [Source: epics.md#Story-1.7] — acceptance criteria, user story
- [Source: prd.md#FR45] — IT operator can deploy on client infrastructure
- [Source: prd.md#Journey-5] — Laurent deployment & monitoring journey
- [Source: docs.astral.sh/uv/guides/integration/docker/] — uv Docker multi-stage build guide
- [Source: _bmad-output/implementation-artifacts/1-6-configuration-canal-de-notification.md] — previous story learnings, httpx runtime usage

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No blocking issues encountered during implementation.

### Completion Notes List

- Task 1: Created multi-stage Dockerfile with uv 0.10.9, UV_COMPILE_BYTECODE=1, UV_LINK_MODE=copy, non-root appuser, Python stdlib HEALTHCHECK (no curl). Added .dockerignore.
- Task 2: Added `app` service to docker-compose.yml with build context, port 8000, env_file, DATABASE__URL override for Docker network, depends_on postgres with service_healthy condition, and healthcheck.
- Task 3: Added `typer>=0.24.1` as runtime dep. Moved `httpx` from dev to runtime (used by TeamsAdapter). Added `[project.scripts] agent = "quote_agent.cli.main:app"`.
- Task 4: Created CLI entry point (main.py) with Typer app registering status and logs commands. Created status.py using urllib.request to call /health endpoint with colored output via typer.style(). Supports --host and --port options.
- Task 5: Created logs.py wrapping `docker logs` subprocess with --follow/-f and --lines/-n flags. Handles missing docker gracefully.
- Task 6: Created 7 CLI tests (help, status healthy/degraded/connection error, logs default/follow/custom lines). All pass. ruff check and mypy both clean.

### Change Log

- 2026-03-18: Story 1.7 implementation complete — Docker deployment + CLI tools

### File List

- Dockerfile (NEW)
- .dockerignore (NEW)
- docker-compose.yml (MODIFIED)
- pyproject.toml (MODIFIED)
- uv.lock (MODIFIED)
- src/quote_agent/cli/main.py (NEW)
- src/quote_agent/cli/status.py (NEW)
- src/quote_agent/cli/logs.py (NEW)
- tests/unit/test_cli.py (NEW)
