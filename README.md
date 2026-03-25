# ai-quote-agent

**Turn quote request emails into ERP draft quotes in seconds, without cleaning your catalog first.**

An autonomous AI agent that processes inbound B2B quote request emails, searches product catalogs using hybrid semantic + keyword search, and creates draft quotes directly in your ERP. Built for industrial distributors where sales reps spend 3 to 20 minutes per quote manually digging through massive, messy product catalogs.

> **Plug and run.** The agent works with your raw, uncleaned catalog data. No months of data preprocessing. No CPQ implementation project.

## How It Works

```mermaid
flowchart LR
    A["📧 Email\n(IMAP)"] --> B["🔍 Extract\n& Classify"]
    B --> C["🧠 Reason\n& Search"]
    C --> D{"Confidence?"}
    D -- High --> E["✅ Review\n& Comply"]
    E --> F["📝 Draft\nERP Quote"]
    F --> G["🔔 Notify\nSales Rep"]
    D -- Medium --> H["📋 Propose\nOptions"]
    H --> G
    D -- Low --> I["⚠️ Escalate\nto Human"]
    I --> G
```

**Sales reps stop building quotes manually. They just validate AI-prepared drafts.**

## Features

- **Email Ingestion**: IMAP polling, HTML cleaning, multi-request splitting (1 email = N quote requests)
- **Hybrid Search**: semantic (pgvector) + keyword (tsvector) + exact reference matching, fused via Reciprocal Rank Fusion
- **Zero Preprocessing**: works with raw ERP catalogs out of the box, no manual data cleanup
- **Adaptive Reasoning**: LangGraph pipeline with 11 nodes (classify, reason, score, route, review, compliance, draft, notify)
- **Self-Review & Compliance**: automated quality gate before ERP draft creation
- **Smart Notifications**: Microsoft Teams (Adaptive Cards), with batching, throttling, and weekly reports
- **Multi-Tier Routing**: high confidence = auto-draft, medium = proposals, low = human escalation
- **Security**: prompt injection detection, input isolation, log redaction, structured audit trail

## Architecture

```mermaid
flowchart TB
    subgraph Ingestion
        IMAP[IMAP Poller] --> Cleaner[Email Cleaner]
        Cleaner --> Extractor[LLM Extractor]
        Extractor --> Splitter[Request Splitter]
    end

    subgraph Agent["LangGraph Agent Pipeline"]
        Classify[Classifier] --> Reason[Reasoner]
        Reason --> Score[Confidence Scorer]
        Score --> Route[Router]
        Route --> Review[Self Reviewer]
        Review --> Compliance[Compliance Checker]
        Compliance --> Draft[ERP Drafter]
        Route --> NotifyP[Notify Proposals]
        Route --> NotifyE[Notify Escalation]
        Compliance --> NotifyR[Notify Rejection]
        Draft --> NotifyQ[Notify Quote Ready]
    end

    subgraph Search["Hybrid Search Engine"]
        Vector[pgvector Semantic]
        Keyword[tsvector Full-Text]
        Exact[Exact Reference]
        RRF[RRF Fusion]
        Vector & Keyword & Exact --> RRF
    end

    subgraph Infrastructure
        PG[(PostgreSQL 16\n+ pgvector)]
        ERP[Odoo ERP]
        Teams[MS Teams]
    end

    Splitter --> Classify
    Reason --> RRF
    Draft --> ERP
    NotifyQ & NotifyP & NotifyE & NotifyR --> Teams
    Search & Agent --> PG
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12, async-first |
| Agent Framework | LangGraph + LangChain |
| LLM | OpenAI-compatible (GPT-4o default) |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | sentence-transformers (BAAI/bge-m3, 1024-dim) |
| Web Framework | FastAPI + Uvicorn |
| ERP | Odoo 17 (XML-RPC) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| CLI | Typer |
| Package Manager | uv |
| Quality | ruff + mypy (strict) + pytest |
| Deployment | Docker + docker-compose |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker & Docker Compose (for PostgreSQL)

### 1. Clone & install

```bash
git clone https://github.com/your-org/ai-quote-agent.git
cd ai-quote-agent

# Install all dependencies (including ML/embeddings)
uv sync --locked --group ml

# Or without ML group (CI/lightweight)
uv sync --locked
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials:
#   DATABASE__URL, LLM__API_KEY, EMAIL__*, ERP__*, NOTIFICATION__*
```

### 3. Start services & migrate

```bash
# Start PostgreSQL with pgvector
docker compose up -d postgres

# Apply database migrations
alembic upgrade head
```

### 4. Run

```bash
# Start the API server
uvicorn quote_agent.main:app --host 0.0.0.0 --port 8000

# Or use Docker for everything
docker compose up --build
```

### 5. Ingest your catalog

```bash
# Pull products from Odoo ERP
agent erp-read

# Generate embeddings
agent search --reindex
```

## CLI Reference

The `agent` CLI provides direct access to every pipeline stage:

```bash
# Full pipeline
agent process <request_id>        # Process a quote request end-to-end
agent status                      # Show system status

# Individual nodes (debugging/testing)
agent classify <request_id>       # Classify request complexity
agent reason <request_id>         # Apply reasoning strategy
agent score <request_id>          # Score confidence
agent review <request_id>         # Run self-review
agent compliance <request_id>     # Check compliance
agent draft-create <request_id>   # Create ERP draft

# Search & catalog
agent search "stainless steel tubes"  # Test hybrid search
agent erp-read                        # Ingest catalog from ERP

# Notifications
agent batch-notify                # Dispatch batched notifications
agent scheduler-status            # Check scheduler health
agent notify-test                 # Send test notification

# Utilities
agent seed-odoo                   # Generate test data in Odoo
agent logs                        # View structured logs
```

## Testing

```bash
# Unit + integration tests (default, no external services needed)
pytest

# E2E tests (requires PostgreSQL + LLM API key)
docker compose up -d postgres
pytest -m e2e

# Scale tests (50K products, slow)
pytest -m scale

# With coverage report
pytest --cov=quote_agent --cov-report=term-missing
```

**Test markers:**
- `e2e`: end-to-end tests hitting real PostgreSQL, IMAP, and LLM services
- `scale`: large-scale performance tests (50K product catalog)

## Configuration

All configuration uses environment variables with `__` (double underscore) nesting:

| Variable | Description | Example |
|---|---|---|
| `DATABASE__URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/quote_agent` |
| `LLM__API_KEY` | OpenAI-compatible API key | `sk-...` |
| `LLM__DEFAULT_MODEL` | Default LLM model | `gpt-4o` |
| `EMAIL__IMAP_SERVER` | IMAP server for polling | `imap.gmail.com` |
| `EMAIL__POLL_INTERVAL` | Polling interval (seconds) | `60` |
| `ERP__URL` | Odoo instance URL | `https://odoo.example.com` |
| `NOTIFICATION__CHANNEL` | Notification channel (`teams` or `log`) | `teams` |
| `NOTIFICATION__TEAMS_WEBHOOK_URL` | Teams webhook URL | `https://...` |
| `EMBEDDING__DEVICE` | Embedding device (`cpu` or `cuda`) | `cpu` |

See [`.env.example`](.env.example) for the full list.

## Project Structure

```
src/quote_agent/
├── agent/              # LangGraph pipeline (graph, state, 11 nodes)
├── adapters/           # Integration adapters (LLM, ERP, Email, Notification, Embedding)
├── search/             # Hybrid search engine (vector, keyword, exact, RRF fusion, cache)
├── models/             # SQLAlchemy ORM (Product, EmailRequest, QuoteRequest, SearchCache)
├── services/           # Business logic (email poller, catalog, notifications, scheduling)
├── security/           # Prompt injection defense, input isolation, log redaction
├── audit/              # Structured JSON logging with auto-redaction
├── cli/                # Typer CLI (16 commands)
├── api/                # FastAPI endpoints (/health, /v1/*)
└── config.py           # Pydantic Settings (centralized configuration)
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **PostgreSQL-only** (no Redis) | Simplifies deployment. pgvector for search, native caching via TTL table |
| **Zero preprocessing** | Industrial catalogs are messy. Semantic matching handles dirty data without months of cleanup |
| **Adapter pattern** | Protocol + Factory + `@lru_cache` singletons. Swap ERP/LLM/notification providers without touching the pipeline |
| **Fire-and-forget notifications** | Notification failures never block the quote pipeline |
| **Self-hosted** | No cloud dependencies. All infrastructure stays client-controlled for industrial security requirements |
| **State-driven errors** | Errors flow through LangGraph state. Post-pipeline check ensures no silent drops |

## Contributing

```bash
# Install dev dependencies
uv sync --locked --group dev --group ml

# Run linter + formatter
ruff check src tests
ruff format src tests

# Type checking (strict mode)
mypy src

# Run all checks before committing
ruff check src tests && ruff format --check src tests && mypy src && pytest
```

## License

This project is proprietary. All rights reserved.
