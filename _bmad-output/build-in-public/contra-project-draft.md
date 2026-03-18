# Contra Project Page Draft

## Project Title

AI-Powered B2B Quoting Agent — Building in Public

## Project Description

An end-to-end AI system that automates B2B industrial quote generation: from email reception to product matching to draft quote creation in an ERP.

This is a solo build-in-public project, documented from prototype to production. Every architectural decision, benchmark result, and lesson learned is shared publicly.

## Prototype Overview

### Architecture

- **Orchestration:** n8n (prototype) → Python/LangGraph (production)
- **ERP:** Odoo 18 Community — product catalog, customer data, quote management
- **Vector Database:** Qdrant — semantic search on product embeddings
- **Embeddings:** OpenAI text-embedding-3-small
- **LLM:** Claude (structured extraction + product matching + quote reasoning)
- **Pipeline:** Email → Extract structured data → Hybrid search → Match products → Draft quote

### What Makes It Interesting

- **Domain complexity:** B2B industrial catalogs have inconsistent naming, French jargon, abbreviations, and unit variations. Pure keyword search fails. Pure semantic search hallucinates. Hybrid search with domain-aware reranking works.
- **Real-world constraints:** ERP integration, email parsing, multi-line quote requests — this isn't a demo app, it's designed for production use.

### Roadmap Highlights

- **Confidence-based routing (planned):** Not every quote can be automated. The production system will score its own confidence and route low-confidence requests to humans — building trust by knowing its limits.
- **Export compliance checks (planned):** Automated detection of export-controlled items and sanctioned entities.
- **Memory & learning (planned):** Client preference history, feedback loops, and industry knowledge base for continuous improvement.

## Technology Stack

Python 3.12 | LangGraph | PostgreSQL + pgvector | FastAPI | OpenAI | Claude | Odoo 18 | Docker

## Prototype Case Study

### The Challenge

B2B industrial distributors process dozens of quote requests daily. Each email contains product references in inconsistent formats — abbreviations, French jargon, mixed units — that must be matched against a catalog of hundreds of products. Manual quoting is slow and error-prone.

### The Prototype

Built an end-to-end AI pipeline: Email → LLM-based structured extraction → Hybrid search (semantic + keyword) → Product matching → Draft quote in ERP.

Orchestrated with n8n, using Qdrant for vector search, OpenAI embeddings, and Claude for reasoning. Tested against a 680-product synthetic catalog with realistic B2B industrial naming variations.

### Results

| Metric | Result |
|--------|--------|
| Hybrid search accuracy (Hit@5) | 96.2% |
| End-to-end latency | 2.9s average |
| Scenario coverage | 3/3 (simple, multi-line, ambiguous) |

### GO Decision

Results validated the approach. The production build will rewrite from n8n to Python/LangGraph, adding confidence-based routing, proper error handling, and human-in-the-loop review for edge cases.

### Architecture Overview

The prototype demonstrated that hybrid search (combining semantic embeddings with keyword matching) significantly outperforms either approach alone for B2B industrial catalogs, where product naming conventions vary widely between companies and languages.

## Production Foundation (Epic 1 Complete)

### Production Architecture

The production system uses an **adapter pattern** with 5 integration points, each independently testable and swappable:

| Adapter | Purpose | Technology |
|---------|---------|------------|
| Database | Product catalog, quotes, audit trail | PostgreSQL + pgvector, SQLAlchemy async, Alembic migrations |
| LLM Provider | Structured extraction, reasoning, matching | OpenAI-compatible API abstraction with model routing |
| ERP | Product catalog, customer data, quote creation | Odoo XML-RPC with credential redaction |
| Email | Quote request reception | IMAP with structured parsing |
| Notification | Sales team alerts | Microsoft Teams Adaptive Cards with webhook health check |

### Stack Decisions

- **Language:** Python 3.12 with strict typing (mypy --strict on all source files)
- **AI Framework:** LangGraph (agent orchestration, state management)
- **Database:** PostgreSQL + pgvector (relational data + vector search in one DB)
- **API:** FastAPI with per-service health checks
- **Deployment:** Docker Compose (multi-stage build, app + PostgreSQL containers)
- **CI/CD:** GitHub Actions (Ruff linting + mypy type-check + pytest + Docker build)

### Quality Metrics

| Metric | Value |
|--------|-------|
| Automated tests | 68 |
| Test coverage | 95% |
| Type-checked source files (mypy --strict) | 41 |
| Integration adapters | 5 |
| Stories completed | 8 |
| Manual deployment steps | 0 (docker compose up) |

### High-Level Architecture

```
Email (IMAP) → FastAPI → LangGraph Agent → Quote Draft
                  ↕            ↕
              PostgreSQL    LLM Provider
              + pgvector   (OpenAI-compat)
                  ↕            ↕
             ERP (Odoo)    Notifications
            XML-RPC         (Teams)
```

Each adapter follows the same pattern: abstract interface, concrete implementation, health check endpoint, independent configuration. This allows swapping any integration (e.g., switching from Odoo to SAP, or from Teams to Slack) without touching the rest of the system.

## Project Links

- GitHub: {add_repo_url_when_public}
- LinkedIn Series: {add_first_post_url_when_published}

## Page Notes

- Epic 1 (Foundation) is complete. Architecture and quality metrics sections added.
- Update metrics as production build progresses through Epics 2-9
- Link to LinkedIn posts as they're published
