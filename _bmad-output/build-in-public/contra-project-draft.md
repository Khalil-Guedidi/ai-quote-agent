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

Python | LangGraph | Qdrant | OpenAI | Claude | Odoo 18 | PostgreSQL | Docker

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

## Project Links

- GitHub: {add_repo_url_when_public}
- LinkedIn Series: {add_first_post_url_when_published}

## Page Notes

- Update metrics and architecture details as the production build progresses
- Add screenshots/demos after Epic 1 (foundation) is complete
- Link to LinkedIn posts as they're published
