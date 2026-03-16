---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-15'
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-ai-quote-agent-2026-03-15.md'
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - '_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-15.md'
workflowType: 'architecture'
project_name: 'ai-quote-agent'
user_name: 'Khalil'
date: '2026-03-15'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

52 FRs across 10 domains, forming a complete autonomous agent pipeline:

| Domain | FRs | Architectural Implication |
|--------|-----|--------------------------|
| Email Processing & Extraction | FR1-4 | Inbound pipeline: IMAP ingestion → cleaning → structured extraction. Must handle multi-request emails |
| Product Search & Matching | FR5-10 | Hybrid search engine (vector + keyword) on raw catalogs. Caching layer. Zero-preprocessing ingestion from ERP API/export |
| Adaptive Reasoning & Decision | FR11-16 | LangGraph agent with complexity classification, confidence scoring, routing logic, multi-model support |
| Memory & Learning | FR17-23 | 3-layer memory system (industry RAG, company context, client few-shot). Feedback loop from corrections. Pattern detection for recurring requests |
| Quality Assurance & Safety | FR24-28 | Self-review node in agent graph. Prompt injection defense (input/instruction separation). Anti-hallucination validation. Export control detection |
| ERP Integration | FR29-32 | Adapter pattern: universal quote format → ERP-specific translation. Draft-only write, read-only catalog/client data. Odoo Community for MVP |
| Notification & Communication | FR33-36 | Adapter pattern: Teams Adaptive Cards (MVP), extensible to Slack/email/webhook. Batched notifications, confidence-tier-specific templates |
| Observability & Audit | FR37-41 | Structured logging with reasoning traces. Immutable audit trail. Alerting system. Monitoring dashboard (web UI + CLI) |
| Configuration & Administration | FR42-49 | Config-driven behavior: proposability filters, confidence thresholds, client rules, LLM provider, model routing. File/env-based for MVP |
| Testing & Quality | FR50-52 | Scenario replay, prompt/config versioning with rollback, cohabitation mode (parallel processing without sending) |

**Non-Functional Requirements:**

29 NFRs driving key architectural decisions:

| Category | Key Constraints | Architecture Impact |
|----------|----------------|-------------------|
| Performance | E2E < 2 min, search < 3s, cache < 1s, notification < 30s | Async processing pipeline, vector index optimization, result caching, non-blocking notification dispatch |
| Security | Data at rest/transit encryption, prompt injection defense, least privilege, immutable audit logs, no confidential data in logs | Input isolation layer, secrets management, scoped ERP credentials, log sanitization, append-only audit store |
| Scalability | 300 quotes/day/instance, 50K product refs, 3x peak handling | Horizontal scaling via instances, efficient vector indexing, queue-based processing for peak absorption |
| Reliability | 99.5% uptime, graceful degradation (queue on LLM failure), ERP failure buffering, zero data loss | Message queue for email intake, retry with backoff on integrations, circuit breakers, persistent email tracking |
| Integration | Versioned adapter interfaces, LLM hot-swap, standard IMAP, health checks on all integrations | Clean adapter contracts, provider abstraction layer, health check endpoints, automated failure alerting |

**Scale & Complexity:**

- Primary domain: Backend Python / AI Agent (LangGraph) with multi-system integration
- Complexity level: High
- Estimated architectural components: ~12-15 (email ingestion, request parser, complexity classifier, product search engine, vector store, memory system, confidence scorer, decision router, self-review, ERP adapter, notification adapter, LLM abstraction, audit logger, config manager, monitoring/CLI)

### Technical Constraints & Dependencies

| Constraint | Source | Impact |
|-----------|--------|--------|
| Python / LangGraph stack | PRD explicit choice | Agent framework, all backend logic in Python |
| Self-hosted deployment | Data privacy requirement | No cloud dependencies, all infra client-controlled |
| LLM-agnostic | Client chooses provider | Abstraction layer mandatory, no provider-specific features in core |
| Odoo Community (MVP) | First ERP target | ERP adapter designed for Odoo first, but interface must be generic |
| Solo developer + BMAD | Resource constraint | Monolith modulaire preferred over microservices, minimize operational complexity |
| Single-tenant MVP | Deployment model | Simpler data isolation, but keep tenant-aware design for future SaaS |
| Draft-only ERP writes | Security / least privilege | Agent never sends quotes directly, always creates drafts |
| French language first | Target market | Email processing, notification tone, product catalog in French |

### Cross-Cutting Concerns Identified

| Concern | Components Affected | Architecture Strategy Needed |
|---------|-------------------|----------------------------|
| **Observability & Audit Trail** | All components | Structured logging framework, reasoning trace capture, immutable audit store — must be baked into every component, not bolted on |
| **Adapter Pattern** | ERP, LLM, Notifications, Email | Consistent interface contracts across all integration points. Versioned, independently deployable adapters |
| **Security & Input Isolation** | Email processing, LLM calls, logging | Untrusted input (email) strictly separated from agent instructions at every stage. Log sanitization to prevent data leaks |
| **Configuration Management** | All components | Centralized config system: business rules, thresholds, provider settings, model routing. File-based MVP, UI-based post-MVP |
| **Graceful Degradation** | All integrations | Circuit breakers, retry strategies, queue-based buffering. Every external dependency has a failure mode and recovery path |
| **Confidence Scoring & Routing** | Classifier, search, memory, decision engine | Confidence propagates through the entire pipeline. Routing decisions (auto/multi-proposal/escalate) depend on aggregated confidence |
| **Feedback Loop** | ERP integration, memory, search | Corrections captured passively from ERP edits, fed back into client memory and search ranking |

## Starter Template Evaluation

### Primary Technology Domain

Backend Python / AI Agent (LangGraph) with lightweight React diagnostic frontend. Two distinct technology surfaces in a monolith modulaire.

### Starter Options Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| `langgraph new --template new-langgraph-project-python` | Official LangGraph starter template | Designed for LangGraph Cloud deployment — structure too cloud-oriented, not suited for self-hosted |
| `langgraph new --template retrieval-agent` | LangGraph RAG template | Closer to our use case (RAG), but still cloud-oriented and too limited for our scope |
| **Custom project structure following LangGraph conventions** | Tailored structure adopting LangGraph patterns (graph.py, state.py, nodes/) within a broader application architecture | **Selected** — project has too many specificities (multi-adapter, CLI, web UI, audit) to fit a standard template |

### Selected Approach: Custom Project Structure

**Rationale:**
- LangGraph templates are designed for LangGraph Cloud — we are self-hosted
- Project has unique components (CLI, diagnostic web UI, multi-adapter, audit trail) that don't fit any template
- LangGraph's recommended structure (graph.py, state.py, nodes/, tools/) is adopted for the agent core, integrated into a broader architecture
- Solo dev + BMAD needs a clear, predictable structure — not a template we'd deform

**Initialization Commands:**

```bash
# Create project with uv
uv init ai-quote-agent
cd ai-quote-agent

# Add core dependencies
uv add langgraph langchain-core langchain-community
uv add psycopg[binary] pgvector sqlalchemy alembic
uv add fastapi uvicorn
uv add python-dotenv pydantic pydantic-settings

# Add dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy

# Frontend (separate)
npm create vite@latest web-ui -- --template react-ts
cd web-ui && npm install tailwindcss @tailwindcss/vite shadcn@latest
```

**Proposed Project Structure:**

```
ai-quote-agent/
├── pyproject.toml              # uv project config
├── uv.lock                     # lockfile
├── .env.example                # environment template
├── alembic/                    # database migrations
│   └── versions/
├── src/
│   └── quote_agent/
│       ├── __init__.py
│       ├── main.py             # application entry point
│       ├── config.py           # centralized configuration (pydantic-settings)
│       │
│       ├── agent/              # LangGraph agent core
│       │   ├── graph.py        # agent graph definition
│       │   ├── state.py        # agent state schema
│       │   ├── nodes/          # graph nodes (classifier, searcher, reviewer, etc.)
│       │   └── tools/          # agent tools
│       │
│       ├── adapters/           # integration adapters (adapter pattern)
│       │   ├── erp/            # ERP adapters (Odoo, future SAP/Dynamics)
│       │   ├── llm/            # LLM provider abstraction
│       │   ├── email/          # IMAP ingestion
│       │   └── notification/   # Teams, email, webhook adapters
│       │
│       ├── memory/             # 3-layer memory system
│       │   ├── industry.py     # RAG industry knowledge
│       │   ├── company.py      # company context
│       │   └── client.py       # client-level memory
│       │
│       ├── search/             # hybrid product search engine
│       │   ├── engine.py       # search orchestration
│       │   ├── vector.py       # pgvector operations
│       │   └── indexer.py      # catalog ingestion
│       │
│       ├── models/             # SQLAlchemy models / DB schema
│       ├── services/           # business logic services
│       ├── audit/              # structured logging & audit trail
│       ├── security/           # input isolation, sanitization
│       │
│       ├── api/                # FastAPI endpoints (web UI backend + health checks)
│       └── cli/                # CLI commands (agent deploy, status, logs, config)
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── web-ui/                     # React diagnostic frontend
    ├── src/
    │   ├── components/
    │   │   └── ui/             # shadcn/ui components
    │   └── pages/
    ├── package.json
    └── tailwind.config.ts
```

### Architectural Decisions Provided by This Setup

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language & Runtime | Python 3.12+ | LangGraph requirement, ecosystem maturity |
| Package Manager | uv | Speed (10-100x faster), modern, manages Python versions |
| Agent Framework | LangGraph | Explicit PRD choice, graph-based agent architecture |
| Database | PostgreSQL + pgvector | Single DB for relational + vector, RLS for future multi-tenant, self-hosted simplicity |
| API Framework | FastAPI | Async-native, auto-docs, health check endpoints |
| ORM & Migrations | SQLAlchemy + Alembic | Industry standard, migration versioning |
| Task Processing | PostgreSQL job table + asyncio | No Redis dependency, sufficient for 300 quotes/day, transactionally safe |
| Frontend | Vite + React + TypeScript + Tailwind + shadcn/ui | UX spec explicit choice, diagnostic web UI only |
| Testing | pytest (backend) + Vitest (frontend) | Industry standards for Python and React respectively |
| Linting & Formatting | Ruff | Fast all-in-one Python linting/formatting, replaces flake8 + black + isort |
| Config Management | pydantic-settings | Type-safe configuration, .env support, validation |

**Note:** Project initialization using these commands should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Data architecture: PostgreSQL + pgvector with HNSW indexing
- Embedding strategy: Local multilingual model by default (hybrid option C)
- Security architecture: 3-layer defense-in-depth for prompt injection
- Agent-adapter communication: Direct calls via Python Protocol classes

**Important Decisions (Shape Architecture):**
- Cache strategy: PostgreSQL-based with TTL invalidation
- API design: REST + optional WebSocket for log streaming
- Frontend state: React Query (server state only)
- Containerization: Docker Compose (app + PostgreSQL)
- CI/CD: GitHub Actions with portable pipeline

**Deferred Decisions (Post-MVP):**
- Full authentication system for web UI (basic token auth for MVP)
- Secret manager integration (env vars for MVP)
- Multi-tenant data isolation strategy (single-tenant MVP)
- SaaS deployment architecture

### Data Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | PostgreSQL + pgvector | Single DB for relational + vector data. RLS for future multi-tenant. Minimizes infrastructure for self-hosted deployment |
| Vector Index | HNSW | Best fit for 50K product refs with infrequent catalog updates. Faster reads, acceptable memory usage at this scale |
| Embedding Model | Local multilingual by default (BGE-M3 or multilingual-e5-large), configurable to use provider API | Stability (no re-indexing on provider change), offline capability, fine-tuning potential for industrial vocabulary. Multilingual support required from day one |
| Search Strategy | Hybrid: pgvector (semantic) + PostgreSQL tsvector (keyword/exact ref) | Combines semantic understanding with exact reference matching — both needed for industrial catalogs |
| Cache | PostgreSQL table with TTL-based invalidation | No additional infrastructure (no Redis), persistent across restarts, sufficient performance for 300 quotes/day |
| Migrations | Alembic | Standard SQLAlchemy migration tool, version-controlled schema changes |
| ORM | SQLAlchemy | Industry standard, async support, mature ecosystem |

### Authentication & Security

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Web UI Auth (MVP) | Static token in .env (HTTP Basic) | Minimal security layer for internal network deployment. No auth complexity for MVP |
| Credential Storage (MVP) | Environment variables / .env | Docker standard, familiar to IT ops, no plaintext in code. Sufficient for self-hosted single-tenant |
| Prompt Injection Defense | 3-layer defense-in-depth | (1) Structural separation: email content in dedicated `user_input` field with explicit delimiters, never in system prompt. (2) Sanitization layer: pattern detection, escaping. (3) Self-review node: validates output coherence with system instructions |
| ERP Access | Draft-only write, read-only catalog/client data | Principle of least privilege — agent never sends quotes directly |
| Log Sanitization | Confidential data (pricing, client info) stripped before logging | No sensitive data in logs or traces beyond client's LLM provider |
| Audit Trail | Append-only PostgreSQL table | Immutable by design — no UPDATE/DELETE on audit records |

### API & Communication Patterns

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Web UI API | REST (FastAPI) | Simple, auto-documented, sufficient for diagnostic dashboard |
| Real-time | WebSocket endpoint for log streaming only | LogViewer terminal mode needs live feed. Dashboard polls every 30s — no WebSocket needed |
| Agent ↔ Adapters | Direct calls via Python Protocol classes | Monolith modulaire — no serialization overhead, clean interfaces, easily testable via mocks |
| Error Format | Structured errors (code, message, context, timestamp) | Consistent across all components. Adapter errors transformed into agent state (retry/queue/escalate). API errors in standard HTTP format with actionable messages |
| Health Checks | `/health` endpoint returning per-service status | Single endpoint for Docker HEALTHCHECK, CLI `agent status`, and web UI dashboard |

### Frontend Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State Management | React Query (TanStack Query) only | Web UI only displays server data — no complex client state needed. React Query handles fetch, cache, and auto-refetch |
| Build & Serve | Vite build → static files served by FastAPI | Single process, single port. Simplified deployment for IT ops. Multi-stage Docker build |
| Component Library | shadcn/ui (copy-paste, no package dependency) | Full control, no version conflicts, AI-agent friendly code generation |
| Pages | 4 pages: Dashboard, Logs, Connections, Performance | As defined in UX spec. Minimal page count for diagnostic tool |

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Containerization | Docker Compose: app container + PostgreSQL container | Two services only. App container = multi-stage build (frontend build → Python app). Laurent runs `docker compose up` |
| CI/CD | GitHub Actions | Portable pipeline (lint → test → build → push). Commands are CI-agnostic — trivial to migrate to GitLab CI if needed |
| Pipeline Steps | Ruff lint → pytest + Vitest → Docker build → push image | Standard quality gates. No auto-deploy (self-hosted = manual deployment by IT ops) |
| Health Monitoring | `/health` endpoint + Docker HEALTHCHECK + alerting via notification adapter | Laurent sees service status via CLI, web UI, and Docker. Alerts via Teams/email on failure |
| Scaling | Horizontal: add instances behind load balancer | Stateless app design (state in PostgreSQL). Each instance connects to same DB. Sufficient for post-MVP growth |

### Decision Impact Analysis

**Implementation Sequence:**
1. PostgreSQL + pgvector setup (Alembic migrations, schema)
2. Configuration system (pydantic-settings, .env)
3. LLM adapter abstraction + embedding model integration
4. Product catalog ingestion + HNSW index
5. Agent core (LangGraph graph, nodes, state)
6. ERP adapter (Odoo)
7. Email adapter (IMAP)
8. Notification adapter (Teams)
9. API layer (FastAPI, health checks)
10. Web UI (React, diagnostic dashboard)
11. CLI commands
12. Docker Compose + CI/CD pipeline

**Cross-Component Dependencies:**
- pgvector index depends on embedding model choice → embedding adapter must be built before search engine
- Agent graph depends on all adapters being interfaced (not necessarily implemented) → define Protocol classes early
- Web UI depends on API endpoints → API design before frontend
- Audit trail touches every component → logging framework must be established first
- Configuration system is used everywhere → build it in the first story

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 5 categories where AI agents could make inconsistent choices — naming, structure, formats, communication, and process patterns.

### Naming Patterns

**Python (backend) — PEP 8 strictly enforced:**
- Files: `snake_case` — `quote_processor.py`, `odoo_adapter.py`
- Classes: `PascalCase` — `QuoteProcessor`, `OdooAdapter`
- Functions/methods: `snake_case` — `process_quote()`, `search_products()`
- Variables: `snake_case` — `confidence_score`, `client_id`
- Constants: `UPPER_SNAKE_CASE` — `MAX_RETRY_COUNT`, `DEFAULT_CONFIDENCE_THRESHOLD`

**Database:**
- Tables: `snake_case` plural — `quotes`, `products`, `audit_logs`, `client_memories`
- Columns: `snake_case` — `created_at`, `confidence_score`, `client_id`
- Foreign keys: `{singular_table}_id` — `client_id`, `product_id`
- Indexes: `ix_{table}_{columns}` — `ix_quotes_client_id`
- Constraints: `uq_{table}_{columns}`, `ck_{table}_{condition}`

**API REST:**
- Endpoints: `kebab-case` plural — `/api/v1/quotes`, `/api/v1/audit-logs`, `/api/v1/health`
- JSON fields: `snake_case` — consistent with Python backend
- Query params: `snake_case` — `?client_id=123&confidence_min=0.85`

**React (frontend):**
- Components: `PascalCase` files and classes — `ConfidenceBadge.tsx`, `LogViewer.tsx`
- Hooks: `camelCase` with `use` prefix — `useQuoteStats()`, `useHealthStatus()`
- Variables/functions: `camelCase` — `confidenceScore`, `formatTimestamp()`

### Structure Patterns

**Test Organization:**
- Tests separated in `tests/` (not co-located) — mirrors `src/` structure
- `tests/unit/agent/test_classifier.py` tests `src/quote_agent/agent/nodes/classifier.py`
- `tests/integration/` for tests with real PostgreSQL/Odoo
- `tests/fixtures/` for shared test data (sample emails, synthetic catalogs)
- Naming: `test_{module}.py`, functions `test_{behavior}_when_{condition}()`

**Adapter Organization:**
- Every adapter follows the same pattern: `protocol.py` (interface), `{impl}.py` (implementation)
- Example ERP:
  ```
  adapters/erp/
  ├── protocol.py      # class ERPAdapter(Protocol)
  ├── odoo.py          # class OdooAdapter (implements ERPAdapter)
  └── models.py        # shared DTOs (UniversalQuote, ProductInfo, etc.)
  ```
- Same structure for `llm/`, `email/`, `notification/`

**Imports:**
- Absolute imports only — `from quote_agent.adapters.erp.protocol import ERPAdapter`
- Never relative imports (`from ..adapters import ...`)
- Order: stdlib → third-party → local (Ruff enforces automatically)

### Format Patterns

**API Response Formats:**

```json
// Success
{"data": {...}, "meta": {"timestamp": "2026-03-15T09:14:23Z"}}

// Error
{"error": {"code": "ERP_CONNECTION_FAILED", "message": "...", "detail": "..."}, "meta": {"timestamp": "..."}}

// List
{"data": [...], "meta": {"timestamp": "...", "count": 42}}
```

**Dates:** ISO 8601 everywhere — `2026-03-15T09:14:23Z`. Storage in UTC in PostgreSQL, local conversion on frontend only.

**Structured Logging Format:**

```json
{
    "timestamp": "2026-03-15T09:14:23.456Z",
    "level": "INFO",
    "component": "agent.classifier",
    "message": "Request classified",
    "context": {
        "quote_id": "q-123",
        "classification": "simple",
        "confidence": 0.92
    }
}
```

- Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `component` follows Python path in dot notation: `agent.classifier`, `adapters.erp.odoo`, `search.engine`
- `context` contains structured data — **never confidential data** (prices, sensitive client info)

### Communication Patterns

**Agent State (LangGraph):**

```python
class AgentState(TypedDict):
    # Inputs
    raw_email: str
    parsed_request: ParsedRequest

    # Processing
    classification: RequestClassification    # simple/ambiguous/complex/out_of_scope
    confidence_score: float                  # 0.0 - 1.0
    matched_products: list[ProductMatch]

    # Outputs
    draft_quote: UniversalQuote | None
    proposals: list[UniversalQuote]          # for multi-proposal

    # Meta
    reasoning_trace: list[ReasoningStep]     # audit trail
    current_node: str                        # for observability
```

- Field names in `snake_case`
- Explicit types (no `Any` or `dict`)
- Clear separation: inputs / processing / outputs / meta

**Adapter Protocol Pattern:**

```python
class ERPAdapter(Protocol):
    async def create_draft_quote(self, quote: UniversalQuote) -> str: ...
    async def get_products(self, filters: ProductFilter) -> list[Product]: ...
    async def get_client(self, client_id: str) -> Client: ...
    async def health_check(self) -> ServiceHealth: ...
```

- All methods are `async`
- Return typed DTOs (never `dict`)
- Every adapter exposes a `health_check()`
- Errors raised via typed custom exceptions (`ERPConnectionError`, `ERPAuthError`, etc.)

### Process Patterns

**Error Handling:**

```python
# Custom exception hierarchy
class QuoteAgentError(Exception): ...
class AdapterError(QuoteAgentError): ...
class ERPConnectionError(AdapterError): ...
class LLMTimeoutError(AdapterError): ...
class ValidationError(QuoteAgentError): ...
class SecurityError(QuoteAgentError): ...
```

- Adapter errors are caught in LangGraph nodes and transformed into agent state (retry/queue/escalate)
- Never bare `except Exception` — always type the exception
- API errors converted to standard HTTP responses via global FastAPI handler

**Retry Pattern for Adapters:**
- Exponential backoff: 1s → 2s → 4s → max 30s
- Max 3 retries for LLM/ERP calls
- Circuit breaker: after 5 consecutive failures, service marked "down" for 60s before retrying
- Every attempt and failure is logged

**Validation:**
- Input validation at system boundaries only (API endpoints, email ingestion)
- Pydantic models for all validation
- No double-validation in internal layers — trust internal code

### Enforcement Guidelines

**All AI Agents MUST:**

1. Follow PEP 8 naming conventions for Python, PascalCase for React components
2. Use absolute imports exclusively
3. Type all functions (parameters + return) — `mypy --strict` must pass
4. Write a test for every new module (minimum one unit test per public function)
5. Log via structured format — never `print()` or `logging.info("string message")`
6. Use Protocol classes for all adapter interactions
7. Return typed Pydantic DTOs — never raw `dict` in public interfaces
8. Document public functions with concise docstrings (one-line description, not novels)

**Anti-Patterns to Avoid:**

| Anti-Pattern | Correction |
|-------------|-----------|
| `except Exception: pass` | Type the exception, log, re-raise or transform to state |
| `response["data"]["products"][0]` | Use typed DTOs with attribute access |
| `import os; os.getenv("API_KEY")` | Use `config.settings.api_key` (pydantic-settings) |
| `from ..adapters import erp` | Absolute import: `from quote_agent.adapters.erp import ...` |
| `# TODO: fix later` | Create an issue or resolve — no orphan TODOs |
| `time.sleep(5)` for retry | Use retry pattern with exponential backoff |
| Confidential data in logs | Use log sanitizer systematically |

## Project Structure & Boundaries

### Complete Project Directory Structure

```
ai-quote-agent/
├── .github/
│   └── workflows/
│       └── ci.yml                          # GitHub Actions: lint → test → build → push
├── .env.example                            # Template with all required env vars
├── .gitignore
├── pyproject.toml                          # uv project config, dependencies, tool configs
├── uv.lock                                 # Lockfile
├── Dockerfile                              # Multi-stage: build frontend → install Python → run
├── docker-compose.yml                      # app + PostgreSQL services
├── alembic.ini                             # Alembic config
│
├── alembic/
│   ├── env.py
│   └── versions/                           # Migration files (auto-generated)
│
├── src/
│   └── quote_agent/
│       ├── __init__.py
│       ├── main.py                         # Application entry point (FastAPI app creation)
│       ├── config.py                       # pydantic-settings: all configuration
│       ├── exceptions.py                   # Exception hierarchy (QuoteAgentError, AdapterError, etc.)
│       │
│       ├── agent/                          # LangGraph agent core
│       │   ├── __init__.py
│       │   ├── graph.py                    # Agent graph definition (nodes, edges, conditionals)
│       │   ├── state.py                    # AgentState TypedDict + supporting types
│       │   ├── nodes/
│       │   │   ├── __init__.py
│       │   │   ├── email_parser.py         # Parse and clean email content
│       │   │   ├── classifier.py           # Request complexity classification
│       │   │   ├── product_searcher.py     # Search products via search engine
│       │   │   ├── confidence_scorer.py    # Calculate confidence score
│       │   │   ├── quote_builder.py        # Build UniversalQuote from matches
│       │   │   ├── self_reviewer.py        # Validate output before submission
│       │   │   └── router.py              # Route based on confidence tier
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── catalog_lookup.py       # Tool: search product catalog
│       │       ├── client_history.py       # Tool: query client memory
│       │       └── erp_operations.py       # Tool: ERP read/write operations
│       │
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── erp/
│       │   │   ├── __init__.py
│       │   │   ├── protocol.py             # ERPAdapter Protocol class
│       │   │   ├── odoo.py                 # OdooAdapter implementation
│       │   │   └── models.py               # UniversalQuote, Product, Client DTOs
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   ├── protocol.py             # LLMAdapter Protocol class
│       │   │   ├── openai_compat.py        # OpenAI-compatible provider (Azure, OpenAI, local)
│       │   │   └── models.py               # LLM request/response DTOs
│       │   ├── email/
│       │   │   ├── __init__.py
│       │   │   ├── protocol.py             # EmailAdapter Protocol class
│       │   │   ├── imap.py                 # IMAP ingestion implementation
│       │   │   └── models.py               # IncomingEmail, ParsedEmail DTOs
│       │   ├── notification/
│       │   │   ├── __init__.py
│       │   │   ├── protocol.py             # NotificationAdapter Protocol class
│       │   │   ├── teams.py                # Teams Adaptive Cards implementation
│       │   │   ├── email_notify.py         # Email notification implementation
│       │   │   └── models.py               # Notification DTOs
│       │   └── embedding/
│       │       ├── __init__.py
│       │       ├── protocol.py             # EmbeddingAdapter Protocol class
│       │       ├── local.py                # Local model (BGE-M3 / multilingual-e5)
│       │       ├── api.py                  # Provider API embeddings
│       │       └── models.py               # EmbeddingRequest/Response DTOs
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── industry.py                 # Industry-level RAG knowledge base
│       │   ├── company.py                  # Company context (catalog, rules, workflows)
│       │   └── client.py                   # Client-level memory (history, preferences, few-shot)
│       │
│       ├── search/
│       │   ├── __init__.py
│       │   ├── engine.py                   # Hybrid search orchestration (vector + keyword)
│       │   ├── vector.py                   # pgvector operations (HNSW index)
│       │   ├── keyword.py                  # PostgreSQL tsvector full-text search
│       │   ├── cache.py                    # PostgreSQL-based result cache with TTL
│       │   └── indexer.py                  # Catalog ingestion (ERP → vector store)
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py                     # SQLAlchemy Base, common mixins (timestamps, etc.)
│       │   ├── quote.py                    # quotes table
│       │   ├── product.py                  # products table + vector column
│       │   ├── client.py                   # clients table
│       │   ├── email_request.py            # email_requests table (tracking)
│       │   ├── audit_log.py                # audit_logs table (append-only)
│       │   ├── job.py                      # jobs table (task queue)
│       │   ├── client_memory.py            # client_memories table
│       │   ├── search_cache.py             # search_cache table
│       │   └── config_version.py           # config_versions table (versioning + rollback)
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── quote_processor.py          # Orchestrates full quote processing pipeline
│       │   ├── feedback_service.py         # Captures corrections, updates client memory
│       │   ├── catalog_service.py          # Manages catalog ingestion and updates
│       │   └── job_service.py              # PostgreSQL job queue management
│       │
│       ├── security/
│       │   ├── __init__.py
│       │   ├── sanitizer.py               # Email content sanitization (prompt injection defense)
│       │   ├── input_isolation.py          # Structural separation of untrusted input
│       │   └── log_redactor.py            # Strip confidential data from logs
│       │
│       ├── audit/
│       │   ├── __init__.py
│       │   ├── logger.py                   # Structured logging setup (JSON format)
│       │   ├── trace.py                    # Reasoning trace capture
│       │   └── store.py                    # Append-only audit log persistence
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py                   # FastAPI router aggregation
│       │   ├── health.py                   # GET /api/v1/health — service health checks
│       │   ├── quotes.py                   # GET /api/v1/quotes — quote history & stats
│       │   ├── logs.py                     # GET /api/v1/logs + WS /api/v1/logs/stream
│       │   ├── connections.py              # GET /api/v1/connections — adapter status
│       │   ├── performance.py              # GET /api/v1/performance — stats & trends
│       │   ├── middleware.py               # Auth middleware (token check), error handler
│       │   └── schemas.py                  # API response/request Pydantic schemas
│       │
│       └── cli/
│           ├── __init__.py
│           ├── main.py                     # CLI entry point (click or typer)
│           ├── deploy.py                   # agent deploy command
│           ├── status.py                   # agent status command
│           ├── logs.py                     # agent logs command
│           ├── config.py                   # agent config command
│           └── notify.py                   # agent notify command (manual notification)
│
├── tests/
│   ├── conftest.py                         # Shared fixtures, test DB setup
│   ├── unit/
│   │   ├── agent/
│   │   │   ├── test_classifier.py
│   │   │   ├── test_product_searcher.py
│   │   │   ├── test_confidence_scorer.py
│   │   │   ├── test_self_reviewer.py
│   │   │   └── test_router.py
│   │   ├── adapters/
│   │   │   ├── test_odoo.py
│   │   │   ├── test_imap.py
│   │   │   ├── test_teams.py
│   │   │   └── test_embedding.py
│   │   ├── search/
│   │   │   ├── test_engine.py
│   │   │   └── test_cache.py
│   │   ├── security/
│   │   │   ├── test_sanitizer.py
│   │   │   └── test_log_redactor.py
│   │   └── services/
│   │       └── test_quote_processor.py
│   ├── integration/
│   │   ├── test_search_pipeline.py         # Full search: embed → index → query → results
│   │   ├── test_odoo_integration.py        # Real Odoo API calls
│   │   ├── test_agent_e2e.py              # Full agent graph: email → draft quote
│   │   └── test_audit_trail.py            # Verify immutability and completeness
│   └── fixtures/
│       ├── emails/                         # Sample quote request emails
│       │   ├── simple_request.eml
│       │   ├── ambiguous_request.eml
│       │   ├── multi_product_request.eml
│       │   └── injection_attempt.eml
│       ├── catalogs/                       # Synthetic product catalogs
│       │   ├── clean_catalog.json
│       │   └── dirty_catalog.json          # Messy data for zero-preprocessing tests
│       └── quotes/                         # Expected quote outputs
│           └── expected_simple_quote.json
│
└── web-ui/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   └── client.ts                   # API client (fetch wrapper, snake_case → camelCase)
        ├── components/
        │   ├── ui/                         # shadcn/ui components (auto-generated)
        │   ├── ConfidenceBadge.tsx
        │   ├── ServiceHealthIndicator.tsx
        │   ├── LogViewer.tsx
        │   ├── StatCard.tsx
        │   └── QuoteActivityRow.tsx
        ├── pages/
        │   ├── Dashboard.tsx
        │   ├── Logs.tsx
        │   ├── Connections.tsx
        │   └── Performance.tsx
        └── lib/
            ├── types.ts                    # TypeScript types matching API schemas
            └── utils.ts                    # Formatting, date utils
```

### Architectural Boundaries

**API Boundaries:**

| Boundary | Direction | Protocol | Auth |
|----------|-----------|----------|------|
| Web UI → FastAPI | Inbound | REST + WebSocket | Static token (HTTP Basic) |
| CLI → FastAPI | Inbound | REST (localhost) | Same static token |
| Docker HEALTHCHECK → FastAPI | Inbound | REST `/api/v1/health` | None (internal) |
| Agent → ERP (Odoo) | Outbound | XML-RPC / JSON-RPC | Scoped ERP credentials |
| Agent → LLM Provider | Outbound | HTTPS (OpenAI-compatible API) | Client's API key |
| Agent → IMAP Server | Outbound | IMAP/TLS | Email credentials |
| Agent → Teams Webhook | Outbound | HTTPS POST | Webhook URL |
| Agent → Embedding Model | Internal/Outbound | In-process (local) or HTTPS (API) | None (local) or API key |

**Component Boundaries:**

```
┌─────────────────────────────────────────────────────────┐
│ API Layer (api/)                                         │
│   Exposes REST/WS endpoints                              │
│   Calls: services/, audit/                               │
│   Never calls: adapters/ directly, agent/ directly       │
├─────────────────────────────────────────────────────────┤
│ CLI Layer (cli/)                                         │
│   Exposes CLI commands                                   │
│   Calls: services/, config, api/ (via HTTP to self)      │
├─────────────────────────────────────────────────────────┤
│ Services Layer (services/)                               │
│   Business logic orchestration                           │
│   Calls: agent/, adapters/, search/, memory/, audit/     │
│   Owns: job queue management, feedback processing        │
├─────────────────────────────────────────────────────────┤
│ Agent Layer (agent/)                                     │
│   LangGraph graph execution                              │
│   Calls: adapters/ (via Protocol), search/, memory/      │
│   Owns: state management, reasoning, routing             │
├─────────────────────────────────────────────────────────┤
│ Adapter Layer (adapters/)                                │
│   External system integration                            │
│   Calls: external APIs only                              │
│   Exposes: Protocol interfaces consumed by agent/services│
├─────────────────────────────────────────────────────────┤
│ Search Layer (search/)                                   │
│   Hybrid search engine                                   │
│   Calls: models/ (DB), adapters/embedding/               │
│   Owns: vector index, keyword index, cache               │
├─────────────────────────────────────────────────────────┤
│ Memory Layer (memory/)                                   │
│   3-layer memory system                                  │
│   Calls: models/ (DB), search/ (for RAG)                 │
│   Owns: industry knowledge, company context, client data │
├─────────────────────────────────────────────────────────┤
│ Security Layer (security/)                               │
│   Input isolation & sanitization                         │
│   Called by: agent/nodes/email_parser, audit/             │
│   No outbound dependencies                               │
├─────────────────────────────────────────────────────────┤
│ Audit Layer (audit/)                                     │
│   Logging & audit trail                                  │
│   Calls: models/ (DB), security/log_redactor             │
│   Called by: all layers                                   │
├─────────────────────────────────────────────────────────┤
│ Models Layer (models/)                                   │
│   SQLAlchemy models + DB access                          │
│   No business logic — pure data layer                    │
│   Called by: all layers needing DB access                 │
└─────────────────────────────────────────────────────────┘
```

**Dependency rule:** Arrows always point downward. Never upward dependencies (e.g., `models/` must never import `services/`).

### Requirements to Structure Mapping

| FR Domain | Primary Directory | Key Files |
|-----------|------------------|-----------|
| FR1-4: Email Processing | `agent/nodes/email_parser.py`, `adapters/email/`, `security/sanitizer.py` | Email ingestion, cleaning, extraction, multi-request handling |
| FR5-10: Product Search | `search/`, `adapters/embedding/`, `models/product.py` | Hybrid search, caching, zero-preprocessing ingestion |
| FR11-16: Adaptive Reasoning | `agent/nodes/classifier.py`, `agent/nodes/router.py`, `agent/graph.py` | Classification, confidence scoring, model routing |
| FR17-23: Memory & Learning | `memory/`, `models/client_memory.py`, `services/feedback_service.py` | 3-layer memory, feedback loop, pattern detection |
| FR24-28: Quality & Safety | `agent/nodes/self_reviewer.py`, `security/` | Self-review, prompt injection defense, anti-hallucination |
| FR29-32: ERP Integration | `adapters/erp/`, `models/quote.py` | Draft creation, catalog/client read, universal format |
| FR33-36: Notifications | `adapters/notification/` | Teams cards, batching, multi-channel adapters |
| FR37-41: Observability | `audit/`, `api/health.py`, `api/logs.py` | Structured logs, audit trail, alerts, monitoring |
| FR42-49: Configuration | `config.py`, `cli/config.py`, `models/config_version.py` | Business rules, thresholds, provider config, versioning |
| FR50-52: Testing & Quality | `tests/`, `services/quote_processor.py` (cohabitation mode) | Scenario replay, config versioning, cohabitation |

### Data Flow

```
Email (IMAP) → EmailAdapter → SecuritySanitizer → AgentGraph
                                                      │
                                                      ├→ EmailParser node
                                                      ├→ Classifier node
                                                      ├→ ProductSearcher node → SearchEngine → pgvector + tsvector
                                                      ├→ MemoryLookup (industry/company/client)
                                                      ├→ ConfidenceScorer node
                                                      ├→ Router node (high/medium/low)
                                                      ├→ QuoteBuilder node
                                                      ├→ SelfReviewer node
                                                      │
                                                      ↓
                                              UniversalQuote
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    ↓                 ↓                 ↓
                              ERPAdapter      NotificationAdapter  AuditStore
                           (create draft)     (Teams/email card)   (reasoning trace)
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices validated as mutually compatible:
- Python 3.12+ / LangGraph / FastAPI — all async-native, same runtime
- PostgreSQL + pgvector + SQLAlchemy — pgvector supports SQLAlchemy via `pgvector-python`
- HNSW index well within pgvector limits for 50K product references
- uv / pyproject.toml / Ruff — all configure via pyproject.toml
- FastAPI serving React static build — standard `StaticFiles` middleware
- Docker Compose with app + PostgreSQL — standard architecture

No contradictions detected between technology choices.

**Pattern Consistency:**
- `snake_case` consistent across Python, DB, API JSON responses
- `PascalCase` consistent for Python classes and React components
- Protocol classes + typed DTOs consistent across all adapters
- Structured logging format unique across entire system

**Structure Alignment:**
- Project structure supports adapter pattern (dedicated directory per adapter type)
- Layer boundaries are clear (API → Services → Agent → Adapters → External)
- Test structure mirrors source structure
- Dependency arrows always point downward — no circular dependencies

### Requirements Coverage Validation ✅

**Functional Requirements Coverage: 52/52 (100%)**

| FR Domain | FRs | Status | Architectural Support |
|-----------|-----|--------|----------------------|
| Email Processing | FR1-4 | ✅ 4/4 | `adapters/email/`, `agent/nodes/email_parser.py`, `security/sanitizer.py` |
| Product Search | FR5-10 | ✅ 6/6 | `search/`, `adapters/embedding/`, `search/cache.py` |
| Adaptive Reasoning | FR11-16 | ✅ 6/6 | `agent/nodes/classifier.py`, `agent/nodes/router.py`, `adapters/llm/` |
| Memory & Learning | FR17-23 | ✅ 7/7 | `memory/` (3 layers), `services/feedback_service.py` |
| Quality & Safety | FR24-28 | ✅ 5/5 | `agent/nodes/self_reviewer.py`, `security/` |
| ERP Integration | FR29-32 | ✅ 4/4 | `adapters/erp/`, `adapters/erp/models.py` (UniversalQuote) |
| Notifications | FR33-36 | ✅ 4/4 | `adapters/notification/` (Teams, email, extensible) |
| Observability | FR37-41 | ✅ 5/5 | `audit/`, `api/health.py`, `api/logs.py` |
| Configuration | FR42-49 | ✅ 8/8 | `config.py`, `cli/`, `models/config_version.py` |
| Testing & Quality | FR50-52 | ✅ 3/3 | `tests/fixtures/`, `models/config_version.py`, cohabitation mode |

**Non-Functional Requirements Coverage: 29/29 (100%)**

| NFR Category | Status | Architectural Support |
|-------------|--------|----------------------|
| Performance (NFR1-6) | ✅ 6/6 | Async pipeline, pgvector HNSW, PostgreSQL cache, non-blocking notifications |
| Security (NFR7-15) | ✅ 9/9 | Self-hosted, TLS, input isolation, .env credentials, least privilege, append-only audit, log redaction |
| Scalability (NFR16-19) | ✅ 4/4 | Stateless app, horizontal scaling, PostgreSQL handles 50K refs, asyncio for peaks |
| Reliability (NFR20-24) | ✅ 5/5 | Job queue for graceful degradation, retry with circuit breaker, email tracking, config versioning |
| Integration (NFR25-29) | ✅ 5/5 | Protocol classes, LLM hot-swap, adapter pattern, IMAP standard, health checks |

### Implementation Readiness Validation ✅

**Decision Completeness:** All critical decisions documented with rationale. Technology versions to be verified at implementation time (latest stable). Implementation sequence defined (12 steps).

**Structure Completeness:** ~70 Python files defined with clear roles. 5 custom React components + 4 pages. All directories have explicit purpose.

**Pattern Completeness:** 8 enforcement rules for AI agents. 7 anti-patterns documented. Naming conventions complete across all surfaces (Python, DB, API, React).

### Gap Analysis Results

**Critical Gaps:** 0

**Important Gaps (non-blocking):**

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| No detailed DB schema | Agents design tables during implementation | Acceptable — done in stories with Alembic migrations |
| FR28 (export control) underspecified | Detection approach remains vague | PRD also notes this — specify during implementation |
| No Teams Adaptive Card JSON spec | Templates to be created | UX spec defines visual content — JSON follows |
| CLI framework not chosen (click vs typer) | Minor decision | Typer recommended — decide in first CLI story |

**Nice-to-Have Gaps:**
- No formal C4 diagrams (textual boundaries are clear)
- No detailed OpenAPI spec (FastAPI auto-generates it)
- No operational runbook (post-MVP)

### Architecture Completeness Checklist

**✅ Requirements Analysis**

- [x] Project context thoroughly analyzed (52 FRs, 29 NFRs)
- [x] Scale and complexity assessed (High)
- [x] Technical constraints identified (8 constraints)
- [x] Cross-cutting concerns mapped (7 concerns)

**✅ Architectural Decisions**

- [x] Critical decisions documented with rationale (14 technology decisions)
- [x] Technology stack fully specified
- [x] Integration patterns defined (adapter pattern everywhere)
- [x] Performance considerations addressed

**✅ Implementation Patterns**

- [x] Naming conventions established (Python, DB, API, React)
- [x] Structure patterns defined (tests, adapters, imports)
- [x] Communication patterns specified (agent state, protocols, DTOs)
- [x] Process patterns documented (errors, retry, validation)

**✅ Project Structure**

- [x] Complete directory structure defined (~70 Python files, ~10 React files)
- [x] Component boundaries established (9 layers)
- [x] Integration points mapped (8 boundaries)
- [x] Requirements to structure mapping complete (52/52 FRs → directories)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Simple architecture — monolith modulaire, no premature microservices
- Minimal infrastructure — PostgreSQL alone (relational + vector + queue + cache)
- Consistent adapter pattern — every integration is interchangeable
- Security from MVP — 3-layer defense-in-depth
- Clear project structure — AI agents know exactly where each file goes
- Full requirements traceability — 52/52 FRs and 29/29 NFRs mapped

**Areas for Future Enhancement:**
- Detailed DB schema (will be created in implementation stories)
- Formal C4 diagrams (if project grows)
- Operational runbook (post-MVP)
- Export control specification (FR28)
- Admin configuration UI architecture (post-MVP)

### Implementation Handoff

**AI Agent Guidelines:**

- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and component boundaries
- Respect dependency direction (always downward, never upward)
- Refer to this document for all architectural questions

**First Implementation Priority:**
1. Project initialization (uv init, dependencies, Docker Compose, CI pipeline)
2. PostgreSQL + pgvector setup (Alembic, base models)
3. Configuration system (pydantic-settings)
4. Audit/logging framework (must be first — used by everything)
