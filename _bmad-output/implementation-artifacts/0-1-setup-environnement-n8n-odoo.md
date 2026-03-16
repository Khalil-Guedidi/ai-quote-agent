# Story 0.1: Setup Environnement n8n + Odoo Community

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want a local Docker environment with n8n and Odoo Community running and connected,
So that I have the infrastructure to build and test the prototype workflows.

## Acceptance Criteria

1. **AC-0.1.1**: Docker Compose file with n8n and Odoo Community services running
   - Given: A developer clones the repo
   - When: They run `docker compose up -d`
   - Then: Both n8n and Odoo Community containers start without errors
   - And: Both services are healthy within 60 seconds

2. **AC-0.1.2**: Odoo Community accessible and initialized with demo data
   - Given: Docker services are running
   - When: The developer opens `http://localhost:8069` in a browser
   - Then: Odoo 18 Community is accessible and initialized
   - And: Demo data is loaded (products, contacts, sale module enabled)

3. **AC-0.1.3**: n8n accessible and able to connect to Odoo API
   - Given: Both services are running on the same Docker network
   - When: The developer opens `http://localhost:5678`
   - Then: n8n is accessible with a configured Odoo credential
   - And: A test workflow can list Odoo products via HTTP Request node (JSON-RPC)

4. **AC-0.1.4**: Basic health verification of both services
   - Given: All containers are running
   - When: The developer runs a verification script or checks
   - Then: n8n health endpoint returns OK, Odoo web login page loads, and a basic JSON-RPC call to Odoo returns product data

## Tasks / Subtasks

- [x] Task 1: Create Docker Compose configuration (AC: #1, #2, #3)
  - [x] 1.1: Create `docker-compose.yml` with services: `n8n`, `odoo`, `postgres-odoo` (Odoo's dedicated PostgreSQL)
  - [x] 1.2: Configure n8n service (`docker.n8n.io/n8nio/n8n:latest`, port 5678, persistent volume)
  - [x] 1.3: Configure Odoo service (`odoo:18.0`, port 8069, linked to its postgres)
  - [x] 1.4: Configure PostgreSQL for Odoo (`postgres:16`, with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` for Odoo)
  - [x] 1.5: Create shared Docker network for inter-service communication
  - [x] 1.6: Add `.env.example` with all required environment variables
  - [x] 1.7: Add Docker healthchecks for all services

- [x] Task 2: Odoo initialization with demo data (AC: #2)
  - [x] 2.1: Configure Odoo to auto-initialize database with demo data on first boot
  - [x] 2.2: Verify Sale module is installed and accessible
  - [x] 2.3: Verify demo product catalog and contacts are loaded

- [x] Task 3: n8n ↔ Odoo connection setup (AC: #3)
  - [x] 3.1: Create a test n8n workflow (exported as JSON) that connects to Odoo via HTTP Request node using JSON-RPC
  - [x] 3.2: Test workflow lists products from Odoo (`product.product` model, `search_read` method)
  - [x] 3.3: Document the connection method and credentials

- [x] Task 4: Health verification (AC: #4)
  - [x] 4.1: Create `scripts/verify-setup.sh` that checks: containers running, n8n accessible, Odoo accessible, Odoo JSON-RPC responds
  - [x] 4.2: Document the full setup process in a `prototype/README.md`

## Dev Notes

### Critical: Odoo Version Choice — Use Odoo 18, NOT Odoo 19

The n8n built-in Odoo node uses deprecated XML-RPC/JSON-RPC endpoints that are scheduled for removal in Odoo 20. Odoo 19 throws deprecation warnings and has known compatibility issues with n8n (see [GitHub issue #21545](https://github.com/n8n-io/n8n/issues/21545)). **Use Odoo 18.0** for this prototype to avoid unnecessary friction. The goal is to validate product matching, not debug API compatibility issues.

If you need Odoo 19 features later, use n8n's **HTTP Request node** with direct JSON-RPC calls instead of the built-in Odoo node.

### n8n ↔ Odoo Connection: Prefer HTTP Request Node

Even with Odoo 18, the built-in n8n Odoo node has reported issues with request serialization. For reliability:
- Use n8n's **HTTP Request node** with JSON-RPC payloads to call Odoo
- Odoo JSON-RPC endpoint: `http://odoo:8069/jsonrpc`
- Authentication: call `/web/session/authenticate` first, then use session cookie
- Operations: use `call_kw` method with model, method, args, kwargs

Example JSON-RPC payload for listing products:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "service": "object",
    "method": "execute_kw",
    "args": ["odoo_db", 2, "admin", "product.product", "search_read", [[]], {"fields": ["name", "default_code", "list_price"], "limit": 10}]
  }
}
```

### Docker Compose Architecture

```
┌─────────────────────────────────────────┐
│           Docker Network: proto-net      │
│                                          │
│  ┌──────────┐  ┌───────┐  ┌──────────┐ │
│  │   n8n    │  │ Odoo  │  │ Postgres │ │
│  │ :5678   │──│ :8069 │──│  :5432   │ │
│  └──────────┘  └───────┘  └──────────┘ │
└─────────────────────────────────────────┘
```

- **n8n** talks to **Odoo** via `http://odoo:8069` (Docker DNS)
- **Odoo** talks to **Postgres** via `postgres-odoo:5432`
- n8n uses its own internal SQLite for workflow storage (sufficient for prototype)

### Technology Versions

| Component | Image | Version | Notes |
|-----------|-------|---------|-------|
| n8n | `docker.n8n.io/n8nio/n8n` | latest (2.11.x) | Pin to stable tag in production |
| Odoo | `odoo` | `18.0` | Community Edition. NOT 19 — see note above |
| PostgreSQL | `postgres` | `16` | For Odoo data storage |

### File Structure

Place all prototype files under a `prototype/` directory at project root:
```
ai-quote-agent/
├── prototype/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── .env                    # (gitignored)
│   ├── scripts/
│   │   └── verify-setup.sh
│   ├── n8n-workflows/          # exported workflow JSONs
│   │   └── test-odoo-connection.json
│   └── README.md
├── .gitignore                  # add prototype/.env
└── ...
```

Keep prototype separate from the future Python/LangGraph codebase (Epic 1+). This prototype is throwaway — it validates architecture, not production code.

### Environment Variables

```env
# Odoo
ODOO_DB=odoo_db
ODOO_USER=admin
ODOO_PASSWORD=admin
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo_secret
POSTGRES_DB=postgres

# n8n
N8N_PORT=5678
N8N_BASIC_AUTH_ACTIVE=false
```

### Testing Standards

This is a prototype — no unit tests required. Validation is manual + verification script:
- `scripts/verify-setup.sh` performs smoke tests (curl health endpoints, basic API call)
- Manual verification: open Odoo UI, open n8n UI, run test workflow

### Gotchas to Avoid

1. **Do NOT use Odoo 19** — n8n compatibility issues (see above)
2. **Do NOT use n8n's built-in Odoo node** — use HTTP Request node for reliability
3. **Do NOT create a production-grade setup** — this is a throwaway prototype
4. **Do NOT configure Odoo extensively** — demo data is sufficient for now
5. **Odoo first boot is slow** — it initializes the database and installs modules; this can take 2-3 minutes. Docker healthcheck must account for this with retries/interval
6. **n8n needs persistent volume** — without it, workflows are lost on container restart

### Project Structure Notes

- This story creates the `prototype/` directory — it does NOT touch the future `src/` structure defined in the architecture document
- The `prototype/` directory will be used by stories 0.2 through 0.6 and may be archived or deleted after Epic 0 retrospective
- No conflict with the architecture's project structure — prototype is isolated

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 0, Story 0.1]
- [Source: _bmad-output/planning-artifacts/architecture.md - Infrastructure & Deployment, Data Architecture]
- [Source: _bmad-output/planning-artifacts/prd.md - Prototype Phase, Integration Constraints]
- [n8n Docker docs](https://docs.n8n.io/hosting/installation/docker/)
- [Odoo Docker Hub](https://hub.docker.com/_/odoo/)
- [n8n Odoo node deprecated RPC issue](https://github.com/n8n-io/n8n/issues/21545)
- [n8n Odoo integration docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.odoo/)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Initial Odoo entrypoint script bypassed official entrypoint, causing PostgreSQL socket connection error. Fixed by using `command` instead of custom `entrypoint`.
- Bash `((PASS++))` with `set -e` fails when PASS=0 (evaluates to falsy). Fixed with `PASS=$((PASS + 1))`.
- Bash `UID` is a readonly variable. Renamed to `ODOO_UID`.

### Completion Notes List

- **Task 1**: Created `prototype/docker-compose.yml` with 3 services (n8n, odoo:18.0, postgres:16), shared `proto-net` network, persistent volumes, and healthchecks for all services. Added `.env.example` and root `.gitignore`.
- **Task 2**: Odoo configured with `--init=sale --without-demo=` command to auto-initialize with demo data and sale module on first boot. Verified: products loaded, login page accessible.
- **Task 3**: Created `n8n-workflows/test-odoo-connection.json` with 3-node workflow: ManualTrigger → Authenticate (HTTP Request, JSON-RPC) → List Products (HTTP Request, search_read). Connection details documented in README.
- **Task 4**: Created `scripts/verify-setup.sh` performing 7 checks (3 container status, n8n health, Odoo login, JSON-RPC auth, product query). All 7 checks pass. Full setup documented in `prototype/README.md`.

### Implementation Plan

Used Odoo's official Docker entrypoint with `command` override for DB init flags. n8n connects to Odoo via HTTP Request node with JSON-RPC (as recommended in Dev Notes). Verification script uses curl + python3 for JSON parsing.

### File List

- prototype/docker-compose.yml (new)
- prototype/.env.example (new)
- prototype/.env (new, gitignored)
- prototype/scripts/verify-setup.sh (new)
- prototype/n8n-workflows/test-odoo-connection.json (new)
- prototype/README.md (new)
- .gitignore (new)

### Change Log

- 2026-03-16: Implemented Story 0.1 — Docker environment with n8n, Odoo 18 Community, PostgreSQL 16. All services healthy, JSON-RPC connectivity verified, 7/7 smoke tests pass.
- 2026-03-16: Code review fixes — Replaced Code node with HTTP Request nodes in n8n test workflow (AC-0.1.3 compliance). Fixed hardcoded passwords in verify-setup.sh to use env vars. Added .env auto-loading to verify script. Unstaged .idea/ files from git.
