---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
status: 'complete'
completedAt: '2026-03-15'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
---

# ai-quote-agent - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ai-quote-agent, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: The agent can receive and process incoming quote request emails automatically
- FR2: The agent can clean email content (signatures, threads, noise) to extract the actual request
- FR3: The agent can extract structured data from email body (client identity, requested products, quantities, specifications)
- FR4: The agent can detect and handle multiple quote requests within a single email
- FR5: The agent can search products using semantic understanding and exact reference matching on raw, uncleaned product catalogs
- FR6: The agent can filter out non-proposable products (custom, obsolete, out-of-stock) before search results
- FR7: The agent can match client-specific terminology, abbreviations, and jargon to catalog products
- FR8: The agent can generate 2-5 product proposals when a single best match is uncertain
- FR9: The agent can ingest product catalog data from ERP (API or export) without manual preprocessing
- FR10: The agent can cache search results for similar or recurring requests to reduce processing time and LLM costs
- FR11: The agent can classify incoming requests by complexity (simple / ambiguous / complex / out-of-scope)
- FR12: The agent can apply different reasoning strategies based on request classification
- FR13: The agent can calculate a confidence score for each product match and quote decision
- FR14: The agent can route decisions based on confidence tiers: high (>85%) → draft ready, medium (50-85%) → multi-proposals, low (<50%) → escalation with context
- FR15: The agent can detect out-of-scope requests and notify the sales rep with enriched context explaining why the request is out of scope
- FR16: The agent can route requests to different LLM models based on complexity (lighter models for simple cases, more capable models for complex ones)
- FR17: The agent can access industry-level knowledge (conventions, norms, defaults) from a shared knowledge base
- FR18: The agent can access company-level context (catalog, business rules, workflows)
- FR19: The agent can access client-level memory (past quotes, preferences, habits) for personalized matching
- FR20: The agent can capture sales rep corrections and use them to improve future matching (feedback loop)
- FR21: The agent can use validated past quotes as contextual examples for similar future requests
- FR22: The agent can detect recurring quote patterns ("same as last month") and propose reuse of previous quotes
- FR23: The agent can be calibrated on historical quotes during onboarding to accelerate cold start
- FR24: The agent can self-review its own output before submission to ERP
- FR25: The agent can detect and mitigate prompt injection attempts in email content
- FR26: The agent can separate untrusted input (email) from agent instructions (system prompts)
- FR27: The agent can validate that proposed products exist in the current catalog (anti-hallucination)
- FR28: The agent can detect and flag requests involving export-controlled products or sanctioned entities
- FR29: The agent can create draft quotes in the ERP (Odoo Community for MVP)
- FR30: The agent can read product catalog data from the ERP
- FR31: The agent can read client data and order history from the ERP
- FR32: The agent can produce quotes in a universal format that is translated to ERP-specific format via adapter
- FR33: The agent can notify sales reps when a quote is ready for review (via at least one channel)
- FR34: The agent can present multi-proposal options to sales reps for selection
- FR35: The agent can notify sales reps when a request has been escalated with enriched context
- FR36: The notification system can support multiple channel adapters (Teams, Slack, email, webhook)
- FR37: The system can log every agent decision with full reasoning trace (structured logs)
- FR38: The system can maintain an immutable audit trail of all quote processing decisions
- FR39: The system can trace the complete decision chain from email to draft quote for any processed request
- FR40: The system can generate alerts for critical errors (ERP connection lost, LLM timeout, abnormal error rate)
- FR41: The system can expose monitoring data via dashboard (CLI or web) showing uptime, latency, volume, alerts
- FR42: An administrator can configure proposability filter rules (which products are proposable)
- FR43: An administrator can configure confidence thresholds per client
- FR44: An administrator can configure client-specific business rules
- FR45: An IT operator can deploy the agent on client infrastructure (self-hosted)
- FR46: An IT operator can configure ERP and email connections
- FR47: An IT operator can configure the LLM provider (endpoint, API key, model)
- FR48: An IT operator can configure notification channel preferences
- FR49: An IT operator can configure model routing rules (which LLM model for which complexity level)
- FR50: The system can replay past quote processing scenarios for regression testing and validation
- FR51: The system can version prompts and agent configurations with rollback capability
- FR52: The system can run in cohabitation mode (agent processes in parallel with human, results compared but not sent)

### NonFunctional Requirements

**Performance:**
- NFR-P1: End-to-end quote processing < 2 minutes (email arrival to draft in ERP)
- NFR-P2: Product search latency < 3 seconds (hybrid search on raw catalog)
- NFR-P3: Email extraction < 10 seconds (cleaning + structured data extraction)
- NFR-P4: Confidence scoring < 5 seconds (classification + confidence calculation)
- NFR-P5: Notification delivery < 30 seconds (draft creation to sales rep notification)
- NFR-P6: Cache hit response < 1 second (recurring or similar requests)

**Security:**
- NFR-S1: All data at rest encrypted on client infrastructure, verified by infrastructure security audit
- NFR-S2: All data in transit uses TLS encryption, verified by TLS certificate validation and penetration testing
- NFR-S3: Email content (untrusted input) processed in isolation from agent instructions, verified by input boundary testing
- NFR-S4: ERP credentials stored securely (not in plaintext configuration), verified by secrets management audit
- NFR-S5: Agent operates on principle of least privilege: draft-only ERP write, read-only catalog, verified by permission scope testing
- NFR-S6: Audit logs immutable — no modification or deletion after creation, verified by tamper-detection checks
- NFR-S7: Confidential data (pricing, client info) never appears in external-facing logs or traces beyond the client's chosen LLM provider, verified by log content scanning
- NFR-S8: LLM API calls use the client's own credentials and endpoint — no shared keys
- NFR-S9: Export-controlled product detection active from MVP

**Scalability:**
- NFR-SC1: System handles at least 300 quotes/day per instance without performance degradation
- NFR-SC2: System scales linearly with demand without requiring architectural changes
- NFR-SC3: Peak handling: Monday morning spikes (up to 3x average volume) without failures or significant latency increase
- NFR-SC4: Catalog size: supports at least 50,000 product references per instance

**Reliability:**
- NFR-R1: System uptime > 99.5% during business hours
- NFR-R2: Graceful degradation: if LLM provider unavailable, queue emails for later processing
- NFR-R3: ERP connection failure: buffer draft quotes and retry, notify IT via alert
- NFR-R4: No data loss: every received email acknowledged and tracked to completion or explicit failure
- NFR-R5: Prompt and configuration versioning with rollback prevents broken deployments

**Integration:**
- NFR-I1: ERP adapter interface versioned with semantic versioning — adding a new ERP does not break existing adapter contracts
- NFR-I2: LLM provider interface supports hot-swapping without system restart
- NFR-I3: Notification channel interface allows adding new channels via adapter implementation only
- NFR-I4: Email ingestion supports standard IMAP protocol for maximum compatibility
- NFR-I5: All integrations have health checks and automated alerting on failure

### Additional Requirements

**Project Initialization & Stack:**
- Custom project structure using `uv init` (UV package manager, not pip), Python 3.12+
- Core dependencies: langgraph, langchain-core, langchain-community, psycopg, pgvector, sqlalchemy, alembic, fastapi, uvicorn, python-dotenv, pydantic, pydantic-settings
- Dev dependencies: pytest, pytest-asyncio, pytest-cov, ruff, mypy
- Frontend: Vite + React + TypeScript + Tailwind + shadcn/ui
- pyproject.toml for all tool configs, .env.example template

**Database & Storage:**
- PostgreSQL + pgvector as single database (relational + vector data together)
- Vector indexing with HNSW algorithm (optimized for 50K product references)
- Alembic migrations for database schema version control
- Append-only audit log table (immutable by design — no UPDATE/DELETE)
- PostgreSQL cache table with TTL-based invalidation for query results
- Email request tracking table for persistent email tracking and zero data loss
- Row-Level Security (RLS) support for future multi-tenant capability

**Infrastructure & Deployment:**
- Docker Compose deployment (two services: app container + PostgreSQL container)
- Multi-stage Docker build: frontend build → Python app
- No Redis dependency — use PostgreSQL job table + asyncio for task processing
- Stateless application design for horizontal scaling behind load balancer
- Self-hosted deployment only (no cloud dependencies)
- GitHub Actions for CI/CD pipeline
- .github/workflows/ci.yml configuration

**Integration Architecture:**
- Adapter pattern mandatory for all integrations: email, LLM, ERP, notifications, embedding
- All adapters must expose health_check() method and be async
- IMAP ingestion for email processing
- Odoo Community for MVP (via XML-RPC / JSON-RPC)
- Teams Adaptive Cards for MVP notifications
- OpenAI-compatible API abstraction for LLM providers
- Embedding model support: local multilingual by default (BGE-M3 or multilingual-e5-large)
- Universal quote format for ERP translation via adapter
- Draft-only write access to ERP

**API & Communication:**
- REST API with /api/v1/ versioning
- Consistent API response format: {"data": {...}, "meta": {"timestamp": "ISO8601"}}
- Error response format: {"error": {"code": "...", "message": "...", "detail": "..."}, "meta": {"timestamp": "..."}}
- ISO 8601 dates everywhere (UTC in storage)
- Snake_case for JSON fields
- WebSocket endpoint at /api/v1/logs/stream for log streaming
- Static token authentication (HTTP Basic) for MVP

**Security Architecture:**
- 3-layer defense-in-depth for prompt injection: (1) Structural separation, (2) Sanitization layer, (3) Self-review node
- Credentials stored in .env (environment variables, no plaintext in code)
- Log sanitization mandatory via security/log_redactor.py
- Input isolation layer separating untrusted email content from agent instructions

**Agent Architecture:**
- LangGraph agent with TypedDict state: raw_email, parsed_request, classification, confidence_score, matched_products, draft_quote, proposals, reasoning_trace, current_node
- Hybrid search (pgvector semantic + PostgreSQL tsvector keyword/exact reference)
- 3-layer memory system: industry RAG, company context, client few-shot
- Feedback loop from ERP corrections
- Multi-proposal support based on confidence tier routing
- Cohabitation mode (parallel processing without sending)
- Config versioning with rollback capability

**Monitoring & Observability:**
- Structured JSON logging format (mandatory)
- /health endpoint for Docker HEALTHCHECK, CLI status, and web UI dashboard
- Per-service health status reporting
- Alerting system for service failures
- WebSocket endpoint for log streaming (real-time feed for CLI terminal mode)
- Dashboard polling every 30 seconds for non-critical updates
- Confidential data stripped from logs

**CLI Requirements:**
- CLI commands for: deploy, status, logs, config, notify
- CLI framework: Typer
- Status command shows per-service health
- Log streaming capability for terminal mode

**Code Quality Mandates:**
- No bare `except Exception` — always type exceptions
- No raw dict access — use typed DTOs
- No `import os; os.getenv()` — use config.settings
- No relative imports — absolute imports only
- No `time.sleep()` for retry — use exponential backoff (1s → 2s → 4s → max 30s, max 3 retries, circuit breaker after 5 consecutive failures)
- No `print()` — use structured JSON logging
- mypy --strict must pass
- Ruff linting (PEP 8 strict enforcement)
- Minimum one unit test per public function

**Testing Architecture:**
- Test structure mirrors source structure (tests/unit/, tests/integration/)
- Shared fixtures in tests/fixtures/ (sample emails, synthetic catalogs, expected outputs)
- Integration tests with real PostgreSQL/Odoo
- Vitest for frontend testing
- CI/CD steps: Ruff lint → pytest + Vitest → Docker build → push image

**Frontend Architecture:**
- 4 pages only: Dashboard, Logs, Connections, Performance
- React Query (TanStack Query) for server state management
- Vite build → static files served by FastAPI (single process, single port)
- shadcn/ui components
- TypeScript required for all React code
- API client must handle snake_case → camelCase conversion

### UX Design Requirements

- UX-DR1: Implement color system with primary palette tokens (primary #4A6FA5, secondary #0D9488, with dark/light variants)
- UX-DR2: Implement semantic color palette for cross-surface consistency (neutral palette tokens + confidence tier colors: high green #16A34A, medium amber #D97706, low red #DC2626)
- UX-DR3: Implement confidence tier visual language with triple redundancy (color + icon + text) across all surfaces
- UX-DR4: Establish typography system with system font stack (Inter, system fallbacks) and monospace stack (JetBrains Mono, fallbacks)
- UX-DR5: Implement type scale with 8 typography levels (h1 30px/700 through mono 13px/400) with specific line heights
- UX-DR6: Establish 4px-based spacing scale (space-1 through space-12) with card/section/table spacing rules
- UX-DR7: Define responsive breakpoints for desktop-first approach (sm 640px, md 768px, lg 1024px, xl 1280px)
- UX-DR8: Implement web UI responsive layout system (2-column with sidebar on desktop, 1-column collapsed on smaller)
- UX-DR9: Define sidebar responsive behavior (fixed 240px desktop, icon-only 60px at md, hamburger toggle at sm)
- UX-DR10: Build ConfidenceBadge component (shadcn/ui Badge composition) with compact and full variants, ARIA labels
- UX-DR11: Build ServiceHealthIndicator component showing ERP/Email/LLM/VectorDB/Teams status with auto-refresh 30s
- UX-DR12: Build StatCard component with Default, Trend, and Target variants for KPI display
- UX-DR13: Build LogViewer component with Table View (filterable, color-coded) and Terminal View (monospace, auto-scroll) modes
- UX-DR14: Build QuoteActivityRow component (40px table row with timestamp, client, product, ConfidenceBadge, status, expandable)
- UX-DR15: Implement Teams Adaptive Card template - quote-ready.json (high confidence, green accent, casual French tone)
- UX-DR16: Implement Teams Adaptive Card template - quote-multi-proposal.json (medium confidence, amber accent, 3 options)
- UX-DR17: Implement Teams Adaptive Card template - quote-escalation.json (low confidence, red accent, context + ambiguity explanation)
- UX-DR18: Implement Teams Adaptive Card template - batch-summary.json (morning digest with confidence tier breakdown)
- UX-DR19: Implement Teams Adaptive Card template - manager-weekly.json (Marc weekly report with KPIs and per-rep breakdown)
- UX-DR20: Implement Teams Adaptive Card template - manager-stats.json (on-demand bot command response)
- UX-DR21: Establish Teams Adaptive Card structural consistency (accent bar + bot avatar "Q" + conversational French + structured data + action buttons)
- UX-DR22: Implement Teams notification feedback patterns and tone (7 notification patterns, tutoiement, short sentences, admit uncertainty)
- UX-DR23: Implement web UI feedback patterns (toast success 3s auto-dismiss, persistent warning/error with suggested fix, info toast)
- UX-DR24: Implement loading state patterns (skeleton screens for page load, subtle spinner for refresh, progress indicator >3s)
- UX-DR25: Implement empty state patterns with contextual messaging (4 patterns explaining WHY and WHAT makes content appear)
- UX-DR26: Define number and metric formatting rules (percentages integer, durations human-readable, timestamps contextual, trend arrows)
- UX-DR27: Implement table display patterns (default sort descending timestamp, 40px rows, hover highlight, click-to-expand, virtual scroll)
- UX-DR28: Implement sidebar navigation structure (4 items: Dashboard/Logs/Connections/Performance with teal active indicator)
- UX-DR29: Implement page layout consistency (h1 title, stat cards row + 2-column grid for dashboard, filter bar + content for others)
- UX-DR30: Establish max content width 1280px and spacing strategy (sidebar 240px, fluid content, card-based layout, 12-column grid)
- UX-DR31: Define notification timing and delivery rules (immediate for individual quotes, scheduled for batch/weekly, per-state-change for system)
- UX-DR32: Implement notification batching rules (>5 quotes in 10 min → batch, max 1 notification/min/user)
- UX-DR33: Ensure WCAG 2.1 AA color contrast compliance (validated ratios for all palette colors, amber always paired with icon)
- UX-DR34: Implement triple-redundancy color coding for confidence tiers (color + icon + text, never color alone)
- UX-DR35: Implement keyboard navigation for all interactive elements (tab order, skip link, Enter to expand, Escape to close, visible focus indicators)
- UX-DR36: Implement semantic HTML and ARIA patterns (proper landmarks, heading hierarchy, ARIA labels, live regions, role="status")
- UX-DR37: Implement screen reader optimized content (ARIA live regions for dynamic updates, semantic badges, table headers)
- UX-DR38: Implement RGAA French accessibility compliance (lang attribute, unique page titles, alt text, labels, accessibility statement)
- UX-DR39: Implement responsive accessibility (browser zoom 200%, rem units, prefers-reduced-motion, no flashing, CLS=0)
- UX-DR40: Define browser testing matrix (Chrome/Edge primary, Firefox secondary for RGAA, desktop only, 640px minimum)
- UX-DR41: Establish web UI performance targets (<2s load, CLS=0, skeleton screens, non-blocking data fetch)
- UX-DR42: Define cross-surface consistency rules (confidence language universal, time format contextual, agent identity consistent, progressive disclosure)
- UX-DR43: Implement automated accessibility testing in CI (axe-core, eslint-plugin-jsx-a11y, Lighthouse CI >=95)
- UX-DR44: Define manual accessibility testing checklist (keyboard-only, screen reader, contrast, color blindness, split-screen, reduced motion)
- UX-DR45: Prioritize MVP component development order (StatCard → ServiceHealthIndicator → QuoteActivityRow → ConfidenceBadge → LogViewer → Teams cards → CLI)

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | Réception et traitement automatique des emails |
| FR2 | Epic 2 | Nettoyage du contenu email |
| FR3 | Epic 2 | Extraction de données structurées |
| FR4 | Epic 2 | Gestion multi-demandes dans un seul email |
| FR5 | Epic 3 | Recherche hybride sémantique + exacte sur catalogues bruts |
| FR6 | Epic 3 | Filtre de proposabilité |
| FR7 | Epic 3 | Matching terminologie/jargon client |
| FR8 | Epic 4 | Génération 2-5 propositions quand incertain |
| FR9 | Epic 3 | Ingestion catalogue sans preprocessing |
| FR10 | Epic 3 | Cache de résultats de recherche |
| FR11 | Epic 4 | Classification par complexité |
| FR12 | Epic 4 | Stratégies de raisonnement adaptatives |
| FR13 | Epic 4 | Scoring de confiance |
| FR14 | Epic 4 | Routage par tiers de confiance |
| FR15 | Epic 4 | Détection hors-scope avec contexte |
| FR16 | Epic 4 | Routage multi-modèle LLM |
| FR17 | Epic 6 | Mémoire industrie (RAG) |
| FR18 | Epic 6 | Contexte entreprise |
| FR19 | Epic 6 | Mémoire client (few-shot) |
| FR20 | Epic 6 | Boucle de feedback (corrections) |
| FR21 | Epic 6 | Réutilisation de devis validés |
| FR22 | Epic 6 | Détection de patterns récurrents |
| FR23 | Epic 6 | Calibration sur historique |
| FR24 | Epic 4 | Self-review avant soumission |
| FR25 | Epic 2 | Détection prompt injection |
| FR26 | Epic 2 | Séparation input/instructions |
| FR27 | Epic 4 | Validation anti-hallucination |
| FR28 | Epic 4 | Détection export-controlled/sanctionné |
| FR29 | Epic 4 | Création brouillon devis dans ERP |
| FR30 | Epic 4 | Lecture catalogue produits ERP |
| FR31 | Epic 4 | Lecture données client/historique ERP |
| FR32 | Epic 4 | Format universel de devis + adapter |
| FR33 | Epic 5 | Notification devis prêt |
| FR34 | Epic 5 | Présentation multi-propositions |
| FR35 | Epic 5 | Notification d'escalade |
| FR36 | Epic 5 | Support multi-canaux (adapter) |
| FR37 | Epic 7 | Logging structuré avec traces de raisonnement |
| FR38 | Epic 7 | Audit trail immutable |
| FR39 | Epic 7 | Traçabilité décision email→devis |
| FR40 | Epic 7 | Alertes erreurs critiques |
| FR41 | Epic 7 | Dashboard monitoring (CLI/web) |
| FR42 | Epic 8 | Config filtres de proposabilité |
| FR43 | Epic 8 | Config seuils de confiance par client |
| FR44 | Epic 8 | Config règles métier par client |
| FR45 | Epic 1 | Déploiement self-hosted |
| FR46 | Epic 1 | Configuration connexions ERP/email |
| FR47 | Epic 1 | Configuration LLM provider |
| FR48 | Epic 1 | Configuration canal de notification |
| FR49 | Epic 1 | Configuration routage modèle |
| FR50 | Epic 9 | Replay de scénarios |
| FR51 | Epic 9 | Versionnage prompts/configs avec rollback |
| FR52 | Epic 9 | Mode cohabitation |

## Epic List

### Epic 0: Prototype n8n — Validation Pré-MVP
Valider les hypothèses techniques les plus risquées (matching produit sur catalogue sale, chemin d'ingestion Odoo, flow end-to-end) via un prototype low-code n8n avant d'investir dans le build Python/LangGraph complet.
**FRs covered:** Validation transverse — FR5, FR9 (prototype-level)

### Epic 1: Fondation Système & Déploiement
Laurent peut déployer le système sur l'infrastructure client. L'application tourne avec la base de données, les health checks fonctionnent, et la configuration de base est en place.
**FRs covered:** FR45, FR46, FR47, FR48, FR49

### Epic 2: Réception Email & Extraction des Demandes
L'agent reçoit automatiquement les emails de demande de devis et en extrait les données structurées (client, produits, quantités). Sécurisé dès le jour 1 contre l'injection de prompt.
**FRs covered:** FR1, FR2, FR3, FR4, FR25, FR26

### Epic 3: Catalogue Produits & Recherche Intelligente
L'agent ingère des catalogues produits "sales" sans nettoyage préalable et trouve les bons produits via recherche hybride sémantique + mot-clé. La promesse "zero-preprocessing" est validée. Précédé par 3 stories de fondation (E2E tests, project-context, catalogue test 50K) issues de la rétro Epic 2.
**FRs covered:** FR5, FR6, FR7, FR9, FR10

### Epic 4: Raisonnement Adaptatif & Génération de Devis
L'agent classifie les demandes par complexité, applique un raisonnement adaptatif avec scoring de confiance, s'auto-vérifie, et crée des brouillons de devis dans Odoo. Parcours complet de Sophie (happy path + cas ambigus).
**FRs covered:** FR8, FR11, FR12, FR13, FR14, FR15, FR16, FR24, FR27, FR28, FR29, FR30, FR31, FR32

### Epic 5: Notifications & Workflow Commercial
Sophie reçoit des notifications Teams quand un devis est prêt, peut voir les multi-propositions et sélectionner, est informée des escalades avec contexte enrichi.
**FRs covered:** FR33, FR34, FR35, FR36

### Epic 6: Mémoire, Apprentissage & Boucle de Feedback
L'agent maintient une mémoire à 3 couches (industrie/entreprise/client), apprend des corrections de Sophie, et s'améliore à chaque devis validé.
**FRs covered:** FR17, FR18, FR19, FR20, FR21, FR22, FR23

### Epic 7: Observabilité & Tableau de Bord de Monitoring
Laurent peut monitorer le système via dashboard web et CLI : logs structurés, traces de raisonnement, alertes, santé des services. Chaque décision de l'agent est traçable et auditable.
**FRs covered:** FR37, FR38, FR39, FR40, FR41

### Epic 8: Configuration & Règles Métier
Un administrateur métier peut configurer les règles de proposabilité, les seuils de confiance par client, et les règles métier spécifiques — via fichiers de config pour le MVP.
**FRs covered:** FR42, FR43, FR44

### Epic 9: Assurance Qualité & Mode Cohabitation
Le système peut rejouer des scénarios passés pour tests de régression, versionner les prompts/configs avec rollback, et tourner en mode cohabitation pour valider en conditions réelles.
**FRs covered:** FR50, FR51, FR52

## Epic 0: Prototype n8n — Validation Pré-MVP

Valider les hypothèses techniques les plus risquées (matching produit sur catalogue sale, chemin d'ingestion Odoo, flow end-to-end) via un prototype low-code n8n avant d'investir dans le build Python/LangGraph complet.

**Goal:** Architectural validation and concept proof, not production readiness (PRD: Prototype Phase).

**Exit Criteria:**
- Taux de matching satisfaisant sur catalogue brut sans nettoyage manuel
- Chemin d'ingestion Odoo validé (API, export, ou mixte)
- Flow end-to-end fonctionnel sur cas simples (email → matching → brouillon devis)

**Out of Scope:** Raisonnement adaptatif, couches mémoire, observabilité production, hardening sécurité.

### Story 0.1: Setup Environnement n8n + Odoo Community

As a **developer**,
I want a local Docker environment with n8n and Odoo Community running and connected,
So that I have the infrastructure to build and test the prototype workflows.

**Acceptance Criteria:**
- [ ] AC-0.1.1: Docker Compose file with n8n and Odoo Community services running
- [ ] AC-0.1.2: Odoo Community accessible and initialized with demo data
- [ ] AC-0.1.3: n8n accessible and able to connect to Odoo API
- [ ] AC-0.1.4: Basic health verification of both services

### Story 0.2: Ingestion Catalogue Odoo → Stockage Intermédiaire

As a **developer**,
I want to ingest the product catalog from Odoo (API or export) into an intermediate storage,
So that I can validate the ingestion path and prepare data for vector indexing.

**Acceptance Criteria:**
- [ ] AC-0.2.1: n8n workflow that extracts product catalog from Odoo (API or CSV export)
- [ ] AC-0.2.2: Raw catalog data stored in intermediate format (JSON/CSV) without manual cleaning
- [ ] AC-0.2.3: Odoo populated with synthetic dirty catalog (~500+ products with noise, duplicates, custom items)
- [ ] AC-0.2.4: Ingestion path documented (API vs export vs mixed)

### Story 0.3: Génération Embeddings + Index Vectoriel sur Catalogue Brut

As a **developer**,
I want to generate vector embeddings from the raw product catalog and create a searchable vector index,
So that I can test semantic search on uncleaned product data.

**Acceptance Criteria:**
- [ ] AC-0.3.1: Embedding generation pipeline on raw catalog entries (no preprocessing)
- [ ] AC-0.3.2: Vector index created and queryable (e.g., Qdrant, ChromaDB, or Pinecone via n8n)
- [ ] AC-0.3.3: Basic semantic search returning relevant results on test queries
- [ ] AC-0.3.4: Embedding model selection documented with rationale

### Story 0.4: Recherche Hybride (Vector + Keyword) — Benchmark Accuracy

As a **developer**,
I want to benchmark hybrid search (vector + keyword) accuracy on the dirty catalog,
So that I can validate the core technical assumption: product matching works without manual catalog cleaning.

**Acceptance Criteria:**
- [ ] AC-0.4.1: Hybrid search combining vector similarity + keyword/reference matching
- [ ] AC-0.4.2: Test suite of 20+ realistic product queries (jargon, typos, abbreviations, exact refs)
- [ ] AC-0.4.3: Accuracy metrics documented (precision, recall, top-k hit rate)
- [ ] AC-0.4.4: Comparison: hybrid vs vector-only vs keyword-only
- [ ] AC-0.4.5: GO/NO-GO decision documented based on results

**This is the critical story — the #1 technical risk validation.**

### Story 0.5: Réception Email + Extraction Données Structurées

As a **developer**,
I want an n8n workflow that receives emails and extracts structured quote request data,
So that I can validate the email-to-structured-data pipeline.

**Acceptance Criteria:**
- [ ] AC-0.5.1: n8n workflow triggered by incoming email (IMAP or webhook)
- [ ] AC-0.5.2: LLM-based extraction of structured data (client, products, quantities, specs)
- [ ] AC-0.5.3: Extraction tested on 5+ sample quote request emails
- [ ] AC-0.5.4: Structured output format defined and validated

### Story 0.6: Flow End-to-End — Email → Matching → Brouillon Devis Odoo

As a **developer**,
I want the complete prototype flow working end-to-end: email reception → data extraction → product matching → draft quote creation in Odoo,
So that I can validate the overall architecture before committing to the Python/LangGraph build.

**Acceptance Criteria:**
- [ ] AC-0.6.1: Complete n8n workflow chaining stories 0.1 through 0.5
- [ ] AC-0.6.2: Draft quote created in Odoo with matched products and quantities
- [ ] AC-0.6.3: End-to-end test on 3+ simple quote request scenarios
- [ ] AC-0.6.4: Architecture validation report: what works, what doesn't, lessons for Python build
- [ ] AC-0.6.5: GO/NO-GO decision for proceeding to Epic 1

## Epic 1: Fondation Système & Déploiement

Laurent peut déployer le système sur l'infrastructure client. L'application tourne avec la base de données, les health checks fonctionnent, et la configuration de base est en place.

### Story 1.1: Scaffolding Projet & Système de Configuration

As an **IT operator**,
I want the project initialized with the correct tech stack (Python 3.12+, uv, LangGraph) and a centralized type-safe configuration system (pydantic-settings),
So that all system parameters can be configured via environment variables and .env files with validation.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I run `uv sync`
**Then** all core dependencies are installed (langgraph, langchain-core, fastapi, sqlalchemy, pydantic-settings, etc.)
**And** dev dependencies are available (pytest, ruff, mypy)

**Given** a `.env.example` file exists
**When** I copy it to `.env` and fill in required values
**Then** the configuration system loads and validates all settings with clear error messages for missing/invalid values

**Given** the configuration system is loaded
**When** code accesses settings
**Then** it uses `config.settings` (never `os.getenv()`), with typed, validated access to all parameters

### Story 1.2: Base de Données PostgreSQL & Migrations

As an **IT operator**,
I want a PostgreSQL+pgvector database with Alembic migration management,
So that the system has a versioned, reliable data store ready for application tables.

**Acceptance Criteria:**

**Given** a PostgreSQL instance is configured in .env
**When** I run Alembic migrations (`alembic upgrade head`)
**Then** the database is initialized with pgvector extension enabled
**And** the initial migration creates the database schema version tracking

**Given** the database connection is configured
**When** the application starts
**Then** SQLAlchemy connects successfully using async session management
**And** connection parameters come from pydantic-settings (not hardcoded)

### Story 1.3: Serveur API & Health Check

As an **IT operator**,
I want a running FastAPI server with a `/health` endpoint that reports system status,
So that I can verify the application is alive and check service health.

**Acceptance Criteria:**

**Given** the FastAPI application is started
**When** I call `GET /health`
**Then** I receive a JSON response with overall status and per-service health (database connection at minimum)
**And** the response follows the API format: `{"data": {...}, "meta": {"timestamp": "ISO8601"}}`

**Given** the API server is running
**When** I call `GET /api/v1/` (base)
**Then** I receive a valid API response confirming the server is operational
**And** all endpoints use /api/v1/ versioning

**Given** the database is unreachable
**When** I call `GET /health`
**Then** the response indicates degraded status with the failing service identified

### Story 1.4: Configuration LLM Provider & Adapter

As an **IT operator**,
I want to configure the LLM provider (endpoint, API key, model) and model routing rules,
So that the agent can use the company's chosen AI provider without code changes.

**Acceptance Criteria:**

**Given** LLM provider settings are in .env (endpoint, API key, model name)
**When** the application loads the LLM adapter
**Then** it connects using the OpenAI-compatible API abstraction
**And** the adapter exposes an async `health_check()` method

**Given** model routing rules are configured (e.g., simple→gpt-4o-mini, complex→gpt-4o)
**When** the configuration is loaded
**Then** the routing rules are available as typed configuration
**And** invalid routing rules produce clear validation errors

**Given** the LLM provider is unavailable
**When** the adapter's `health_check()` is called
**Then** it returns unhealthy status with error details
**And** the `/health` endpoint reflects LLM degradation

### Story 1.5: Configuration Connexions ERP & Email

As an **IT operator**,
I want to configure ERP (Odoo) and email (IMAP) connection parameters,
So that the system knows how to connect to the company's existing infrastructure.

**Acceptance Criteria:**

**Given** Odoo connection settings are in .env (URL, database, username, API key)
**When** the ERP adapter is initialized
**Then** it validates the connection parameters and exposes an async `health_check()` method
**And** credentials are never logged (log redaction active)

**Given** IMAP email settings are in .env (server, port, username, password, folder)
**When** the email adapter is initialized
**Then** it validates the connection parameters and exposes an async `health_check()` method

**Given** ERP or email connection fails
**When** health_check() is called
**Then** it returns unhealthy with error details
**And** /health endpoint reflects the degradation

### Story 1.6: Configuration Canal de Notification

As an **IT operator**,
I want to configure notification channel preferences (Teams webhook URL),
So that the system can notify sales reps through the company's communication tools.

**Acceptance Criteria:**

**Given** Teams webhook URL is configured in .env
**When** the notification adapter is initialized
**Then** it validates the webhook URL format and exposes an async `health_check()` method

**Given** the notification adapter follows the adapter pattern
**When** a new channel needs to be added later
**Then** the Protocol interface is documented and extensible (Teams is the first implementation)

**Given** the Teams webhook is unreachable
**When** health_check() is called
**Then** it returns unhealthy status with error context

### Story 1.7: Déploiement Docker & Outils CLI

As an **IT operator**,
I want to deploy the entire system via Docker Compose and manage it through CLI commands,
So that I can operate the system on client infrastructure with minimal effort.

**Acceptance Criteria:**

**Given** a server with Docker installed
**When** I run `docker compose up -d`
**Then** two services start: app container (FastAPI) and PostgreSQL container
**And** the app container uses a multi-stage Docker build (frontend build → Python app)
**And** the PostgreSQL container has pgvector extension available

**Given** the system is running
**When** I run `agent status` (CLI via Typer)
**Then** I see per-service health status (database, LLM, ERP, email, notification)

**Given** the system is running
**When** I run `agent logs` (CLI)
**Then** I see structured JSON log output from the application

**Given** the Dockerfile exists
**When** Docker builds the image
**Then** the HEALTHCHECK instruction calls /health and reports container health

### Story 1.8: Pipeline CI/CD

As an **IT operator**,
I want automated quality checks (linting, type-checking, testing, Docker build) on every push,
So that code quality is maintained and deployments are reliable.

**Acceptance Criteria:**

**Given** code is pushed to the repository
**When** GitHub Actions CI runs
**Then** the pipeline executes in order: Ruff lint → mypy --strict → pytest → Docker build

**Given** Ruff linting is configured
**When** CI runs
**Then** PEP 8 strict enforcement is applied and violations fail the build

**Given** mypy is configured
**When** CI runs
**Then** all functions must have typed parameters and return types (--strict mode)

**Given** pytest is configured
**When** CI runs
**Then** tests execute with coverage tracking (pytest-cov)
**And** the test structure mirrors source structure (tests/unit/, tests/integration/)

## Epic 2: Réception Email & Extraction des Demandes

L'agent reçoit automatiquement les emails de demande de devis et en extrait les données structurées (client, produits, quantités). Sécurisé dès le jour 1 contre l'injection de prompt.

### Story 2.1: Réception Email via IMAP

As a **sales rep (Sophie)**,
I want the agent to automatically receive incoming quote request emails from the mail server,
So that I don't have to forward or manually trigger processing for each request.

**Acceptance Criteria:**

**Given** the IMAP connection is configured and active
**When** a new email arrives in the monitored folder
**Then** the agent detects and retrieves the email within its polling cycle
**And** the email is persisted in the email tracking table with status "received"
**And** no email is ever lost (acknowledged and tracked to completion or explicit failure)

**Given** the IMAP server is temporarily unavailable
**When** the agent attempts to poll
**Then** it retries with exponential backoff (1s → 2s → 4s, max 3 retries)
**And** an alert is raised after circuit breaker threshold (5 consecutive failures)

### Story 2.2: Nettoyage du Contenu Email

As a **sales rep (Sophie)**,
I want the agent to clean email content by removing signatures, reply threads, and noise,
So that only the actual quote request is processed, avoiding confusion from irrelevant content.

**Acceptance Criteria:**

**Given** a raw email with signature block, forwarded thread, and disclaimers
**When** the agent processes the email
**Then** the cleaning step strips signatures, previous thread replies, legal disclaimers, and HTML formatting
**And** the cleaned content contains only the actual request text

**Given** a simple email with no noise
**When** the agent processes it
**Then** the content passes through cleaning unchanged (no over-stripping)

**Given** any email processed
**When** cleaning is complete
**Then** the email tracking record is updated with status "cleaned"
**And** both raw and cleaned versions are stored for audit

### Story 2.3: Extraction de Données Structurées

As a **sales rep (Sophie)**,
I want the agent to extract structured data from the email (client identity, requested products, quantities, specifications),
So that the request is machine-readable and ready for product matching.

**Acceptance Criteria:**

**Given** a cleaned email containing a quote request
**When** the agent runs extraction via LLM
**Then** it produces a structured output with: client name/identifier, list of requested products (description, quantity, specifications)
**And** the extraction completes within 10 seconds (NFR-P3)

**Given** a request with partial information (e.g., no quantity specified)
**When** extraction runs
**Then** missing fields are flagged as absent (not hallucinated)
**And** the structured output clearly indicates which fields are missing

**Given** extraction is complete
**When** the result is stored
**Then** the email tracking record is updated with status "extracted"
**And** the full reasoning trace is logged (structured JSON)

### Story 2.4: Gestion Multi-Demandes dans un Seul Email

As a **sales rep (Sophie)**,
I want the agent to detect and handle multiple quote requests within a single email,
So that each product request is processed independently without losing any.

**Acceptance Criteria:**

**Given** an email containing 3 distinct product requests
**When** the agent runs extraction
**Then** it identifies and separates each request into its own structured record
**And** each sub-request is tracked independently in the system

**Given** an email with a single request
**When** the agent runs extraction
**Then** it correctly identifies one request (no false splitting)

**Given** a multi-request email is processed
**When** all sub-requests are extracted
**Then** each sub-request can proceed independently through the pipeline
**And** the parent email tracks the status of all its sub-requests

### Story 2.5: Défense contre l'Injection de Prompt (Couches 1 & 2)

As an **IT operator (Laurent)**,
I want email content (untrusted input) to be structurally separated from agent instructions and sanitized,
So that malicious content in emails cannot manipulate the agent's behavior.

**Acceptance Criteria:**

**Given** an email is received
**When** it enters the agent pipeline
**Then** the email content is placed in a dedicated `user_input` field with explicit delimiters
**And** it is never injected into system prompts or agent instructions (Layer 1: structural separation)

**Given** email content contains potential injection patterns (e.g., "ignore previous instructions", "you are now...")
**When** the sanitization layer processes it
**Then** suspicious patterns are detected, escaped, and logged
**And** the sanitized content proceeds to extraction (Layer 2: sanitization)

**Given** a legitimate email that coincidentally contains instruction-like text
**When** sanitization runs
**Then** the content is flagged but not destroyed — extraction still works on the sanitized version

### Story 2.6: Séparation Input/Instructions & Logging Sécurisé

As an **IT operator (Laurent)**,
I want a strict boundary between untrusted email data and agent instructions with secure logging,
So that every email processing step is auditable without leaking sensitive data.

**Acceptance Criteria:**

**Given** the agent processes an email through the pipeline
**When** any LLM call is made
**Then** the system prompt and email content are in separate, clearly delimited sections
**And** no email content appears in the system instruction zone

**Given** an email contains confidential information (client names, pricing references)
**When** the processing is logged
**Then** structured JSON logs capture the decision process
**And** confidential data is redacted from logs (log_redactor active)

**Given** any email enters the pipeline
**When** processing completes (success or failure)
**Then** the complete decision chain is traceable: reception → cleaning → extraction → status
**And** the email tracking record reflects the final state

## Epic 3: Catalogue Produits & Recherche Intelligente

L'agent ingère des catalogues produits "sales" sans nettoyage préalable et trouve les bons produits via recherche hybride sémantique + mot-clé. La promesse "zero-preprocessing" est validée.

**Note:** 3 foundation stories (3.0a, 3.0b, 3.0c) added during Epic 2 retrospective (2026-03-19). All 3 are blockers for Stories 3.1+.

### Story 3.0a: Tests End-to-End Pipeline Epic 2

As an **IT operator (Laurent)**,
I want the Epic 2 email pipeline tested end-to-end with real services (IMAP, PostgreSQL, LLM),
So that we validate the pipeline behaves correctly as an assembled system before building on top of it.

**Acceptance Criteria:**

**Given** a real IMAP server with a test email containing a French industrial quote request
**When** the full pipeline runs (polling → cleaning → extraction → splitting)
**Then** the email is persisted in a real PostgreSQL database with status "split"
**And** QuoteRequest records are created with correct line items extracted by a real LLM
**And** the complete decision chain is traceable via structured logs

**Given** an email with prompt injection attempts
**When** the pipeline processes it
**Then** the sanitization layer detects and escapes the threats
**And** extraction still produces valid structured output

**Given** the IMAP server is temporarily unavailable
**When** the poller attempts to connect
**Then** exponential backoff and circuit breaker activate as designed

**Blocks:** All stories 3.1+. Epic 2 pipeline must be validated before building Epic 3 on top of it.

### Story 3.0b: Génération du project-context.md

As a **developer (human or AI)**,
I want a centralized `project-context.md` documenting established patterns, conventions, and known pitfalls,
So that every story starts with full project context instead of rediscovering it from scratch.

**Acceptance Criteria:**

**Given** the project has completed Epics 1 and 2
**When** the project-context.md is generated
**Then** it contains: adapter pattern, LLM structured output pattern, pipeline integration pattern, security layer pattern, test conventions, known pitfalls (annotations + SQLAlchemy, lexicographic string comparisons, regex edge cases), naming conventions, and quality gates (mypy strict, ruff, coverage)

**Given** a new story is created
**When** the dev agent reads project-context.md
**Then** it has sufficient context to avoid previously-identified anti-patterns without relying on per-story dev notes

**Blocks:** All stories 3.1+. Context must be centralized before new development.

### Story 3.0c: Génération Catalogue Test 50K Réaliste

As a **QA engineer (Dana)**,
I want a realistic synthetic French industrial product catalog of 50,000 references,
So that Epic 3 search and matching features are validated against data representative of real-world conditions.

**Acceptance Criteria:**

**Given** public sources of French industrial product naming conventions (RS Components, Würth, etc.)
**When** the catalog generation pipeline runs
**Then** it produces 50,000 product records with realistic attributes: reference codes, abbreviated French names (e.g., "TB RD INOX 304L 25x1.5 LG6000"), categories, prices, stock status, and metadata

**Given** the generated catalog
**When** analyzed for realism
**Then** it includes controlled noise: ~30% missing metadata, naming inconsistencies, duplicates with variant names, mix of French/English descriptions, truncated fields

**Given** the catalog is generated
**When** loaded into the test infrastructure
**Then** it is versioned as a project asset and reusable across epics

**Blocks:** Story 3.1 (ingestion). Cannot validate ingestion without realistic data.

### Story 3.1: Ingestion Catalogue depuis l'ERP (Zero-Preprocessing)

As an **IT operator (Laurent)**,
I want the agent to ingest product catalog data from Odoo (API or export) without any manual preprocessing,
So that the system works with dirty, unstructured catalogs out of the box — no cleanup required.

**Acceptance Criteria:**

**Given** an Odoo instance with a messy product catalog (inconsistent naming, duplicates, missing metadata, abbreviations)
**When** the ingestion process runs
**Then** all products are indexed as-is without requiring manual cleanup
**And** product data includes: reference, name, description, category, price, stock status, and any available metadata

**Given** a catalog with 50,000 product references
**When** ingestion runs
**Then** it completes successfully without memory or performance issues
**And** progress is logged with structured JSON

**Given** the catalog has already been ingested
**When** ingestion runs again (re-sync)
**Then** new/updated products are processed and stale entries are flagged

**E2E Test Requirement:** Story 3.1 E2E tests must load the 50K catalog (from `tests/fixtures/catalog_50k.jsonl`, generated by Story 3.0c) into the test Odoo instance via a seed fixture, then validate ingestion through the real `ERPAdapter.get_products()` path. The JSONL file is the data source, not a substitute for the real ERP integration.

### Story 3.2: Génération d'Embeddings & Index Vectoriel

As an **IT operator (Laurent)**,
I want product data to be embedded into vectors and indexed for semantic search,
So that the agent can find products by meaning, not just exact text match.

**Acceptance Criteria:**

**Given** products are ingested into the system
**When** embedding generation runs
**Then** each product receives a vector embedding using the configured multilingual model (BGE-M3 or multilingual-e5-large)
**And** embeddings are stored in PostgreSQL with pgvector

**Given** 50,000 products are embedded
**When** the HNSW index is built
**Then** vector similarity search returns results in < 3 seconds (NFR-P2)

**Given** the embedding model is configurable
**When** the operator changes the embedding model in configuration
**Then** the system uses the new model without code changes
**And** re-embedding can be triggered for the full catalog

### Story 3.3: Recherche Hybride (Sémantique + Mot-Clé)

As a **sales rep (Sophie)**,
I want the agent to search products using both semantic understanding and exact reference matching,
So that it finds the right product whether I describe it in natural language or use a catalog code.

**Acceptance Criteria:**

**Given** a search query like "tubes inox 304L Ø25 lg 6m"
**When** hybrid search runs
**Then** it returns the correct product even if the catalog entry reads "TUBE ROND SS 304L 25x1.5 LONGUEUR 6000mm"
**And** the search combines pgvector semantic similarity with PostgreSQL tsvector keyword/exact matching

**Given** a search with an exact product reference (e.g., "REF-12345")
**When** the search runs
**Then** the exact reference match is prioritized over semantic results

**Given** a search query with client jargon or abbreviations
**When** the search runs
**Then** semantic understanding handles jargon without requiring manual synonym configuration (FR7)
**And** results are returned within 3 seconds (NFR-P2)

### Story 3.4: Filtre de Proposabilité

As a **sales rep (Sophie)**,
I want non-proposable products (custom, obsolete, out-of-stock) filtered out before I see search results,
So that I never receive proposals for products the company can't actually sell.

**Acceptance Criteria:**

**Given** search results include products marked as custom, obsolete, or out-of-stock
**When** the proposability filter is applied
**Then** non-proposable products are removed from the results
**And** the filter criteria come from configuration (not hardcoded)

**Given** all matching products are non-proposable
**When** the filter runs
**Then** an empty result set is returned with a clear explanation
**And** the agent can escalate if no proposable products match

**Given** a product's stock status changes in the ERP
**When** the catalog is re-synced
**Then** the proposability status is updated accordingly

### Story 3.5: Cache de Résultats de Recherche

As a **sales rep (Sophie)**,
I want search results for recurring or similar requests cached,
So that repeated queries are answered faster and LLM costs are reduced.

**Acceptance Criteria:**

**Given** a search query has been executed before with identical or semantically equivalent parameters
**When** the same query is submitted again within the TTL window
**Then** cached results are returned in < 1 second (NFR-P6)
**And** no LLM call is made for the cached response

**Given** the cache TTL has expired for a query
**When** the query is submitted
**Then** a fresh search is executed and the cache is updated

**Given** the product catalog is re-ingested (new products or updates)
**When** ingestion completes
**Then** relevant cache entries are invalidated
**And** cache invalidation is logged

### Story 3.6: Matching Terminologie Client & Jargon

As a **sales rep (Sophie)**,
I want the agent to match client-specific terminology, abbreviations, and industry jargon to catalog products,
So that it understands requests the way a human sales rep would — without needing manual synonym configuration.

**Acceptance Criteria:**

**Given** a request uses abbreviations common in the industry (e.g., "inox" for "acier inoxydable", "Ø" for diameter)
**When** the search runs
**Then** the agent resolves these through semantic understanding and returns correct products

**Given** a client uses their own product nicknames or internal references
**When** the search runs
**Then** semantic matching attempts to resolve against catalog descriptions and metadata
**And** if uncertain, this is reflected in the confidence score (not silently guessed)

**Given** the system operates primarily in French
**When** requests mix French and technical English terms
**Then** the multilingual embedding model handles cross-language matching correctly

## Epic 4: Raisonnement Adaptatif & Génération de Devis

L'agent classifie les demandes par complexité, applique un raisonnement adaptatif avec scoring de confiance, s'auto-vérifie, et crée des brouillons de devis dans Odoo. Parcours complet de Sophie (happy path + cas ambigus).

**Note:** 3 foundation stories (4.0a, 4.0b, 4.0c) added during Epic 3 retrospective (2026-03-20). All 3 block stories 4.1+.

### Story 4.0a: Fix CI/CD Pipeline GitHub Actions

As an **IT operator (Laurent)**,
I want the CI/CD pipeline on GitHub Actions to pass reliably,
So that every push is validated automatically and regressions are caught before merge.

**Acceptance Criteria:**

**Given** a push to any branch on GitHub
**When** GitHub Actions runs
**Then** unit tests pass in CI (no heavy dependencies like sentence-transformers/torch required)
**And** linting (ruff) and type checking (mypy --strict) pass
**And** E2E tests are either run with service containers or gracefully skipped

**Given** the pipeline has been broken since Epic 1
**When** the root cause is investigated
**Then** the fix addresses the actual failure (likely: heavy deps timeout/memory, missing PostgreSQL service container)

**Blocks:** All stories 4.1+. No more development without CI validation.

### Story 4.0b: CLI Flux Testable Search

As a **Project Lead (Khalil)**,
I want a CLI command that executes a product search and displays formatted results,
So that I can manually test the search engine, judge result quality, and catch product regressions.

**Acceptance Criteria:**

**Given** products are ingested and embedded in PostgreSQL
**When** I run `uv run quote-agent search "tubes inox 304L Ø25"`
**Then** the top results are displayed with: product name, reference, category, score, match source (semantic/keyword/hybrid/exact_ref), is_proposable flag
**And** if jargon expansion occurred, the expanded query is shown
**And** the search duration is displayed

**Given** the CLI is extensible
**When** Epic 4 is developed
**Then** additional commands can be added (`classify`, `process`) to expose the full agent reasoning pipeline

**Blocks:** All stories 4.1+. The Project Lead must see the system work before building the reasoning layer.

### Story 4.0c: Résolution Dictionnaire Jargon Story 3.6

As a **Project Lead (Khalil)**,
I want the jargon dictionary regression from Story 3.6 evaluated and resolved,
So that the "zero-preprocessing" product vision is restored and we don't carry a synonym table into Epic 4.

**Acceptance Criteria:**

**Given** the jargon benchmark (25 queries from `tests/e2e/fixtures/jargon_benchmark.json`)
**When** run with `expansion_enabled=False` (no dictionary, pure semantic search)
**Then** the pass rate is measured and compared to the expansion-enabled result

**Given** the benchmark results
**When** analyzed
**Then** a decision is made:
- If BGE-M3 alone meets ≥ 80% pass rate → remove the dictionary entirely
- If not → investigate embedding strategy improvements (text building, model tuning) rather than growing the dictionary

**Given** the decision is made
**When** implemented
**Then** the `JargonSettings.expansion_enabled` default reflects the decision
**And** the rationale is documented in `project-context.md`

**Blocks:** All stories 4.1+. The zero-preprocessing vision must be restored before building the reasoning layer.

### Story 4.1: Classification de Complexité des Demandes

As a **sales rep (Sophie)**,
I want the agent to classify each quote request by complexity (simple / ambiguous / complex / out-of-scope),
So that it applies the right reasoning strategy and I know upfront how much attention each request needs.

**Acceptance Criteria:**

**Given** an extracted quote request with clear product reference and quantity
**When** the classification node runs
**Then** it classifies the request as "simple"
**And** classification completes within 5 seconds (NFR-P4)

**Given** a request with vague description ("like last time but longer")
**When** classification runs
**Then** it classifies as "ambiguous" with reasons documented in reasoning trace

**Given** a request involving multiple custom products with special conditions
**When** classification runs
**Then** it classifies as "complex"

**Given** a request for a service or product outside the company's catalog
**When** classification runs
**Then** it classifies as "out-of-scope" with an explanation of why

### Story 4.2: Scoring de Confiance & Routage par Tiers

As a **sales rep (Sophie)**,
I want the agent to calculate a confidence score for each match and route decisions accordingly,
So that high-confidence quotes go straight to review while uncertain ones come with options or context.

**Acceptance Criteria:**

**Given** a product match with high confidence (>85%)
**When** routing runs
**Then** the request proceeds to draft quote creation
**And** the confidence score and reasoning are recorded in the trace

**Given** a product match with medium confidence (50-85%)
**When** routing runs
**Then** the agent generates 2-5 alternative proposals (FR8)
**And** each proposal includes its own confidence score and brief reasoning

**Given** a match with low confidence (<50%)
**When** routing runs
**Then** the request is escalated to the sales rep with enriched context
**And** the context includes: what was understood, what was uncertain, and suggested next steps

**Given** an out-of-scope classification
**When** routing runs
**Then** the sales rep is notified with an explanation of why the request is out of scope (FR15)

### Story 4.3: Stratégies de Raisonnement Adaptatives

As a **sales rep (Sophie)**,
I want the agent to apply different reasoning strategies based on request complexity,
So that simple requests are processed efficiently while complex ones get deeper analysis.

**Acceptance Criteria:**

**Given** a "simple" classified request
**When** the reasoning strategy runs
**Then** it applies a direct match strategy (search → top result → confidence check)
**And** uses the lighter LLM model as per routing configuration (FR16)

**Given** an "ambiguous" classified request
**When** the reasoning strategy runs
**Then** it applies an exploration strategy (broader search → multiple candidates → comparative scoring)
**And** uses the more capable LLM model

**Given** a "complex" classified request
**When** the reasoning strategy runs
**Then** it applies a deep analysis strategy (search + context enrichment + multi-step reasoning)
**And** the reasoning trace documents each step taken

### Story 4.4: Self-Review avant Soumission

As a **sales rep (Sophie)**,
I want the agent to self-review its own output before creating the draft quote,
So that errors, hallucinations, and manipulated outputs are caught before they reach me.

**Acceptance Criteria:**

**Given** the agent has produced a draft quote result
**When** the self-review node runs
**Then** it validates: (1) proposed product exists in the current catalog (anti-hallucination FR27), (2) quantities are plausible, (3) output is coherent with the original request

**Given** the self-review detects a hallucinated product (not in catalog)
**When** validation fails
**Then** the draft is rejected and the request is re-routed for re-processing or escalation
**And** the failure reason is logged in the reasoning trace

**Given** the self-review is the 3rd layer of prompt injection defense
**When** it validates output
**Then** it checks that the output is coherent with system instructions (not influenced by email content manipulation)
**And** any detected anomaly is flagged and logged

### Story 4.5: Détection Export-Controlled & Entités Sanctionnées

As a **sales rep (Sophie)**,
I want the agent to detect and flag requests involving export-controlled products or sanctioned entities,
So that the company avoids legal liability from processing prohibited transactions.

**Acceptance Criteria:**

**Given** a request involves a product that may be export-controlled
**When** the detection check runs
**Then** the request is flagged with a clear warning and escalated to the sales rep
**And** the flag includes the specific concern (export control, sanctioned entity, etc.)

**Given** a request from a client whose name matches a sanctions list
**When** the detection runs
**Then** the request is blocked from automatic processing and flagged for human review

**Given** detection is active
**When** any request is processed
**Then** the check runs as part of the standard pipeline (not optional)
**And** the result is recorded in the audit trail

### Story 4.6: Lecture Données ERP (Catalogue & Client)

As a **sales rep (Sophie)**,
I want the agent to read product catalog data and client order history from Odoo,
So that it has the full context needed to match products and personalize quotes.

**Acceptance Criteria:**

**Given** the Odoo adapter is configured and healthy
**When** the agent needs product details for a match
**Then** it reads product data (price, availability, full description) from Odoo via XML-RPC/JSON-RPC (FR30)
**And** the adapter uses read-only access (least privilege)

**Given** a known client sends a request
**When** the agent processes the request
**Then** it reads client data and recent order history from Odoo (FR31)
**And** this data is available for personalization and "like last time" resolution

**Given** the ERP is temporarily unavailable
**When** a read is attempted
**Then** the adapter retries with exponential backoff
**And** if all retries fail, the request is queued for later processing (graceful degradation)

### Story 4.7: Création de Brouillon Devis dans l'ERP

As a **sales rep (Sophie)**,
I want the agent to create draft quotes in Odoo with the matched products and quantities,
So that I find ready-to-validate drafts in my ERP when I start my day.

**Acceptance Criteria:**

**Given** a high-confidence match has passed self-review
**When** the agent creates a draft quote
**Then** a draft quotation is created in Odoo with: client, product(s), quantities, unit prices
**And** the draft is in "draft" status (never sent directly — draft-only access FR29)

**Given** the agent produces a quote
**When** it generates the ERP record
**Then** the quote is first produced in a universal format (FR32)
**And** the Odoo adapter translates it to Odoo-specific API calls

**Given** the ERP is unavailable when the draft should be created
**When** creation fails
**Then** the draft is buffered locally and retried (NFR-R3)
**And** IT is notified via alert

**Given** the full pipeline runs end-to-end
**When** measured from email arrival to draft in ERP
**Then** processing completes in < 2 minutes (NFR-P1)

### Story 4.8: Orchestration Agent LangGraph (Pipeline Complet)

As a **sales rep (Sophie)**,
I want the complete agent pipeline to orchestrate all steps automatically (extract → search → classify → reason → self-review → draft),
So that quote requests are processed end-to-end without manual intervention.

**Acceptance Criteria:**

**Given** an email has been extracted (from Epic 2)
**When** the LangGraph agent processes the request
**Then** it executes the graph: classification → reasoning strategy → product search → confidence scoring → routing → self-review → draft creation
**And** the agent state (TypedDict) flows through all nodes with: raw_email, parsed_request, classification, confidence_score, matched_products, draft_quote, proposals, reasoning_trace, current_node

**Given** any node in the graph fails
**When** an error occurs
**Then** the error is captured in the agent state
**And** the request is gracefully routed to escalation (not silently dropped)

**Given** the agent processes a batch of emails
**When** processing runs
**Then** each request is processed independently via async pipeline
**And** the system handles 300 quotes/day without degradation (NFR-SC1)

## Epic 5: Notifications & Workflow Commercial

Sophie reçoit des notifications Teams quand un devis est prêt, peut voir les multi-propositions et sélectionner, est informée des escalades avec contexte enrichi.

### Story 5.1: Notification Devis Prêt (High Confidence)

As a **sales rep (Sophie)**,
I want to receive a Teams notification when a high-confidence quote is ready for review,
So that I know immediately when a draft is waiting in the ERP and can validate it quickly.

**Acceptance Criteria:**

**Given** the agent creates a high-confidence draft quote in Odoo
**When** draft creation succeeds
**Then** a Teams Adaptive Card is sent to Sophie within 30 seconds (NFR-P5)
**And** the card uses the quote-ready template: green accent bar, bot avatar "Q", casual French message ("Salut ! Devis pour [Client] prêt..."), structured data (Client, Product, Quantity, Confidence %), "Voir dans l'ERP" action button (UX-DR15)

**Given** the notification is sent
**When** Sophie reads it
**Then** she can click "Voir dans l'ERP" to go directly to the draft quote in Odoo

### Story 5.2: Notification Multi-Propositions (Medium Confidence)

As a **sales rep (Sophie)**,
I want to receive a Teams notification with multiple product proposals when the agent is uncertain,
So that I can quickly pick the right option instead of searching the catalog myself.

**Acceptance Criteria:**

**Given** the agent generates 2-5 proposals for an ambiguous request
**When** the notification is sent
**Then** a Teams Adaptive Card uses the multi-proposal template: amber accent bar, bot avatar "Q", message ("Pas sûr à 100% sur le produit. Voici mes 3 options"), each option with product name, brief reasoning, and individual confidence score, ERP link button (UX-DR16)

**Given** Sophie receives the multi-proposal card
**When** she reviews the options
**Then** she can identify the correct product from the proposals and navigate to the ERP to finalize (FR34)

### Story 5.3: Notification d'Escalade (Low Confidence)

As a **sales rep (Sophie)**,
I want to receive a Teams notification with enriched context when the agent escalates a request,
So that I understand why the agent couldn't process it and have the context I need to handle it manually.

**Acceptance Criteria:**

**Given** the agent classifies a request as low confidence or out-of-scope
**When** escalation is triggered
**Then** a Teams Adaptive Card uses the escalation template: red accent bar, bot avatar "Q", honest message ("Celui-là est compliqué..."), context section (client request, parsed understanding, ambiguity explanation), ERP link button (UX-DR17, FR35)

**Given** the escalation card is sent
**When** Sophie reads it
**Then** the context explains: what was understood, what is uncertain, and why the agent couldn't proceed

### Story 5.4: Résumé Batch Matinal & Rapport Hebdomadaire Manager

As a **sales manager (Marc)**,
I want to receive a batch summary each morning and a weekly performance report,
So that I have visibility into the agent's activity without checking the system manually.

**Acceptance Criteria:**

**Given** the agent has processed multiple quotes overnight/morning
**When** the scheduled batch summary time is reached (configurable, default 08:00)
**Then** a Teams Adaptive Card uses the batch-summary template: brand accent bar, count by confidence tier (X ready, Y need choice, Z need expertise), total processed, ERP queue link (UX-DR18)

**Given** it's Monday morning
**When** the weekly report is triggered
**Then** a Teams Adaptive Card uses the manager-weekly template: total quotes processed, average confidence, per-rep breakdown table (rep, quotes, accuracy %), weekly trend arrow + percentage (UX-DR19)

**Given** Marc sends a bot command requesting stats
**When** the command is processed
**Then** a manager-stats card is returned with the requested metrics and available commands (UX-DR20)

### Story 5.5: Règles de Timing & Batching des Notifications

As a **sales rep (Sophie)**,
I want notifications to be intelligently timed and batched,
So that I'm not overwhelmed by a flood of individual notifications during busy periods.

**Acceptance Criteria:**

**Given** more than 5 quotes are processed within 10 minutes
**When** notifications would normally be sent individually
**Then** they are batched into a single summary notification instead (UX-DR32)

**Given** any notification scenario
**When** timing rules are applied
**Then** no more than 1 notification per minute is sent to the same user (UX-DR32)
**And** individual quote notifications are immediate, batch summaries are scheduled, system status is per-state-change (UX-DR31)

**Given** the agent has nothing to process
**When** no quotes are in the queue
**Then** no notification is sent (silence — UX-DR22)

### Story 5.6: Adapter Pattern Multi-Canal & Consistance

As an **IT operator (Laurent)**,
I want the notification system to use an adapter pattern supporting multiple channels,
So that new channels (Slack, email, webhook) can be added without modifying the core notification logic.

**Acceptance Criteria:**

**Given** the notification adapter Protocol is defined
**When** the Teams adapter sends a notification
**Then** it follows the Protocol interface (send, health_check, format_card)
**And** all cards follow the structural consistency rules: accent bar + bot avatar "Q" + casual French tone + structured data + action buttons (UX-DR21)

**Given** the notification system is configured for Teams
**When** a new channel (e.g., Slack) needs to be added later
**Then** only a new adapter implementation is required — no changes to core logic (FR36)

**Given** the agent's tone is consistent across all notifications
**When** any card is generated
**Then** it uses tutoiement, short sentences, admits uncertainty when relevant, never uses corporate speak (UX-DR22)

## Epic 6: Mémoire, Apprentissage & Boucle de Feedback

L'agent maintient une mémoire à 3 couches (industrie/entreprise/client), apprend des corrections de Sophie, et s'améliore à chaque devis validé.

**Note:** 2 foundation stories (6.0a, 6.0b) added during Epic 5.5 retrospective (2026-03-28). 6.0a blocks stories 6.1+.

### Story 6.0a: Refactor asyncio.run (Dette Technique)

As a **developer (human or AI)**,
I want all `asyncio.run()` calls in the codebase refactored to proper async patterns,
So that the codebase is clean, testable, and free of nested event loop risks before building the memory layer.

**Acceptance Criteria:**

**Given** 15+ occurrences of `asyncio.run()` across 11 files
**When** the refactor is applied
**Then** all sync-to-async bridge calls use a consistent pattern (e.g., proper async entry points)
**And** no `asyncio.run()` remains inside library/module code (only allowed at top-level CLI entry points)
**And** all existing tests pass with zero regressions

**Given** the refactored code
**When** unit and E2E tests run
**Then** no nested event loop errors occur
**And** the test suite (800 unit + 28 E2E) passes fully

**Blocks:** All stories 6.1+. Technical debt tracked across 3 consecutive retros.

### Story 6.0b: Fix "Voir dans l'ERP" sur Cartes Escalade/Rejet

As a **sales rep (Sophie)**,
I want the "Voir dans l'ERP" link to be contextually appropriate on escalation and rejection notification cards,
So that I'm not presented with a useless link when no draft quote exists in Odoo.

**Acceptance Criteria:**

**Given** a notification card for an escalation (low confidence) or rejection (compliance blocked)
**When** no draft quote has been created in the ERP
**Then** the "Voir dans l'ERP" link is either hidden or replaced with a contextually appropriate action (e.g., "Voir la demande" linking to the original request)

**Given** a notification card for a high/medium confidence quote
**When** a draft quote exists in the ERP
**Then** the "Voir dans l'ERP" link continues to work as before (no regression)

**Given** the fix is applied
**When** E2E tests covering notification cards run
**Then** all pass and the link behavior is validated for each confidence tier

### Story 6.1: Mémoire Industrie (RAG Knowledge Base)

As a **sales rep (Sophie)**,
I want the agent to access industry-level knowledge (conventions, norms, standard defaults),
So that it understands general industry context even for new clients or unfamiliar product families.

**Acceptance Criteria:**

**Given** the industry knowledge base is populated (industry conventions, norms, standard terminology)
**When** the agent processes a request referencing industry standards (e.g., "NF EN 10088" for stainless steel)
**Then** it retrieves relevant industry context via RAG and uses it to inform product matching
**And** the knowledge base is stored in PostgreSQL with vector embeddings for retrieval

**Given** the industry knowledge base exists
**When** the agent processes a request with no client history
**Then** industry-level knowledge provides a baseline for reasoning (not a blank slate)

**Given** new industry knowledge needs to be added
**When** documents are added to the knowledge base
**Then** they are embedded and indexed without requiring system restart

### Story 6.2: Contexte Entreprise (Catalogue, Règles, Workflows)

As a **sales rep (Sophie)**,
I want the agent to understand company-specific context (catalog structure, business rules, internal workflows),
So that it proposes products according to how our company actually operates.

**Acceptance Criteria:**

**Given** company-level context is configured (which product families are primary, internal naming conventions, default workflows)
**When** the agent processes a request
**Then** it applies company context to prioritize results (e.g., preferred suppliers, standard product lines)

**Given** company business rules exist (e.g., "always propose the standard variant unless client specifies otherwise")
**When** the agent reasons about product selection
**Then** business rules are applied as constraints in the reasoning process (FR18)

**Given** company context is updated (new business rule, catalog reorganization)
**When** the context is refreshed
**Then** the agent applies updated context on subsequent requests without restart

### Story 6.3: Mémoire Client (Historique & Préférences)

As a **sales rep (Sophie)**,
I want the agent to remember each client's past quotes, preferences, and habits,
So that it can personalize proposals ("like last time") and anticipate client needs.

**Acceptance Criteria:**

**Given** a client has order history in the ERP
**When** the agent processes a request from that client
**Then** it retrieves recent quotes and preferences as few-shot context for the LLM (FR19)
**And** the client memory influences product matching and confidence scoring

**Given** a client requests "comme la dernière fois" or "same as last month"
**When** the agent processes the request
**Then** it identifies the most recent matching order and proposes the same product/configuration (FR22)

**Given** a new client with no history
**When** the agent processes their first request
**Then** it falls back to company and industry context (no client memory available)
**And** the first interaction begins building the client profile

### Story 6.4: Boucle de Feedback (Capture des Corrections)

As a **sales rep (Sophie)**,
I want the agent to capture my corrections when I modify a draft quote,
So that it learns from its mistakes and improves future matching for similar requests.

**Acceptance Criteria:**

**Given** Sophie corrects a draft quote in Odoo (e.g., changes product thickness)
**When** the correction is detected by the agent (passive capture from ERP)
**Then** the correction is recorded: original proposal, correction made, client, product family
**And** the correction feeds into client memory for future requests (FR20)

**Given** multiple corrections show a pattern (e.g., client X always prefers 3mm over 2mm)
**When** the agent processes a new request from client X
**Then** the learned preference influences product selection and confidence scoring

**Given** a quote is validated without changes
**When** the agent detects the validation
**Then** the successful match is recorded as a positive signal (reinforcing the agent's accuracy)

### Story 6.5: Réutilisation de Devis Validés

As a **sales rep (Sophie)**,
I want the agent to use validated past quotes as contextual examples for similar future requests,
So that recurring orders are processed faster and more accurately.

**Acceptance Criteria:**

**Given** a new request is similar to a previously validated quote
**When** the agent detects the similarity
**Then** it uses the validated quote as a few-shot example for the LLM (FR21)
**And** the confidence score increases for matches that align with validated history

**Given** a client sends a recurring order pattern (e.g., monthly restock)
**When** the agent detects the pattern (FR22)
**Then** it proactively proposes reuse of the previous quote configuration
**And** flags this as a "recurring pattern" in the notification

**Given** a validated quote is available as context
**When** it's used as an example
**Then** confidential pricing data is only used within the client's own context (never cross-client)

### Story 6.6: Calibration sur Historique (Cold Start)

As an **IT operator (Laurent)**,
I want to calibrate the agent on historical quotes during onboarding,
So that it starts with existing knowledge instead of learning from scratch.

**Acceptance Criteria:**

**Given** a company has historical quote data in Odoo
**When** the calibration process runs during onboarding
**Then** past quotes are ingested and used to populate client memories and product matching context (FR23)
**And** the agent can leverage this history from its first day of operation

**Given** historical data has varying quality (some quotes corrected, some with missing data)
**When** calibration processes the data
**Then** it weights validated/uncorrected quotes higher than corrected ones
**And** incomplete records are used partially (not discarded entirely)

**Given** calibration is complete
**When** the agent processes its first live request
**Then** it already has client preferences, product matching context, and pattern data available
**And** calibration results are logged for audit

## Epic 7: Observabilité & Tableau de Bord de Monitoring

Laurent peut monitorer le système via dashboard web et CLI : logs structurés, traces de raisonnement, alertes, santé des services. Chaque décision de l'agent est traçable et auditable.

### Story 7.1: Logging Structuré & Traces de Raisonnement

As an **IT operator (Laurent)**,
I want every agent decision logged with full reasoning trace in structured JSON format,
So that I can diagnose any issue and reconstruct the agent's decision process.

**Acceptance Criteria:**

**Given** the agent processes any request
**When** decisions are made at each node
**Then** structured JSON logs are emitted with: timestamp, level, component (dot notation), message, context (structured data)
**And** the reasoning trace captures: inputs, processing steps, outputs, metadata

**Given** logs are written
**When** they contain confidential data (pricing, client info, credentials)
**Then** the log_redactor strips confidential fields before writing (NFR-S7)
**And** no `print()` or unstructured `logging.info("string")` exists in the codebase

**Given** the agent completes a quote processing
**When** the full trace is reviewed
**Then** the complete decision chain is reconstructable: email → extraction → classification → search → reasoning → self-review → draft (FR39)

### Story 7.2: Audit Trail Immutable

As an **IT operator (Laurent)**,
I want an immutable audit trail of all quote processing decisions stored in PostgreSQL,
So that every agent action is auditable for compliance and can never be tampered with.

**Acceptance Criteria:**

**Given** the agent makes any decision (classification, product match, draft creation, escalation)
**When** the decision is recorded
**Then** it is written to the append-only audit log table in PostgreSQL (FR38)
**And** the table enforces no UPDATE or DELETE operations (immutable by design)

**Given** an audit log entry exists
**When** an attempt is made to modify or delete it
**Then** the operation is rejected by the database constraints

**Given** audit log retention is configurable
**When** the retention period is set per client
**Then** logs are retained for at least that duration before any cleanup process runs

### Story 7.3: Système d'Alertes

As an **IT operator (Laurent)**,
I want the system to generate alerts for critical errors (ERP down, LLM timeout, abnormal error rate),
So that I'm notified immediately when something requires my attention.

**Acceptance Criteria:**

**Given** the ERP connection is lost
**When** health_check() detects the failure
**Then** an alert is generated and sent to the configured notification channel (FR40)
**And** the alert includes: what failed, when, error details, suggested action

**Given** the LLM provider times out repeatedly
**When** the circuit breaker threshold is reached (5 consecutive failures)
**Then** an alert is generated with timeout details and affected request count

**Given** the error rate exceeds normal thresholds
**When** anomaly detection triggers
**Then** an alert is sent with: error rate, comparison to baseline, affected components

**Given** a system recovers from a failure
**When** health_check() returns healthy
**Then** a recovery notification is sent (brief, positive tone — UX-DR22)

### Story 7.4: Design System & Tokens Frontend

As an **IT operator (Laurent)**,
I want the web UI built on a consistent design system with defined color, typography, and spacing tokens,
So that the monitoring interface is professional, readable, and visually consistent.

**Acceptance Criteria:**

**Given** the frontend project is initialized (Vite + React + TypeScript + Tailwind + shadcn/ui)
**When** the design system is configured in tailwind.config.ts
**Then** all color tokens are defined: primary (#4A6FA5), secondary (#0D9488), confidence tiers (green/amber/red), neutral palette (UX-DR1, UX-DR2)
**And** typography scale is configured: 8 levels from h1 (30px/700) to mono (13px/400) with system font stack (UX-DR4, UX-DR5)
**And** spacing scale is defined: 4px-based (space-1 through space-12) (UX-DR6)

**Given** the responsive layout system is configured
**When** the browser is resized
**Then** breakpoints work correctly: sm 640px, md 768px, lg 1024px, xl 1280px (UX-DR7)
**And** the sidebar is 240px on desktop, icon-only 60px at md, hamburger at sm (UX-DR9)

**Given** the frontend loads
**When** measured on internal network
**Then** it loads in < 2 seconds with no layout shift (CLS=0) (UX-DR41)

### Story 7.5: Composants UI Réutilisables (StatCard, ConfidenceBadge, ServiceHealth)

As an **IT operator (Laurent)**,
I want reusable UI components for displaying KPIs, confidence levels, and service health,
So that the dashboard presents information consistently and accessibly.

**Acceptance Criteria:**

**Given** the StatCard component is built
**When** rendered with data
**Then** it displays: large value (colored), label (small gray), detail/trend line, in three variants: Default, Trend (arrow + percentage), Target (vs. target indicator) (UX-DR12)

**Given** the ConfidenceBadge component is built
**When** rendered with a confidence score
**Then** it shows triple-redundancy: color + icon + text (green/checkmark/High, amber/question/Medium, red/flag/Low) (UX-DR10, UX-DR34)
**And** compact variant (icon + %) for table rows, full variant for cards
**And** ARIA label reads "Confidence: 94 percent, high" (UX-DR36)

**Given** the ServiceHealthIndicator component is built
**When** rendered with service status
**Then** it shows: Healthy (green dot + latency), Degraded (amber dot + warning), Down (red dot + error), Unknown (gray dot) (UX-DR11)
**And** auto-refreshes every 30 seconds, click to expand last 5 status changes
**And** role="status" for screen readers (UX-DR36)

### Story 7.6: Page Dashboard

As an **IT operator (Laurent)**,
I want a Dashboard page showing today's stats, recent quote activity, and service health at a glance,
So that I can assess the system's state in seconds without digging through logs.

**Acceptance Criteria:**

**Given** the Dashboard page is loaded
**When** data is available
**Then** it displays: stat cards row (quotes today, avg confidence, avg processing time), recent QuoteActivityRows (expandable, 40px height, click for agent trace), service health indicators for all connected services (UX-DR14, UX-DR29)

**Given** no quotes have been processed today
**When** the dashboard loads
**Then** empty state shows: "No quotes processed yet today. The agent is monitoring incoming emails." (UX-DR25)

**Given** data is loading
**When** the page renders
**Then** skeleton screens are shown (not blank space), data fetching does not block initial render (UX-DR24)
**And** stat cards use aria-live="polite" for screen reader updates (UX-DR36)

### Story 7.7: Page Logs (LogViewer)

As an **IT operator (Laurent)**,
I want a Logs page with filterable table view and terminal streaming view,
So that I can search through structured logs and watch real-time log output for debugging.

**Acceptance Criteria:**

**Given** the Logs page is loaded in Table View (default)
**When** logs are displayed
**Then** the table shows: Timestamp, Level, Component, Message, Client, Quote ID columns (UX-DR13)
**And** filter bar provides: level dropdown (INFO/WARN/ERROR), time range selector, text search, client filter
**And** rows are color-coded by level, expandable for full details
**And** default sort is most recent first (UX-DR27)

**Given** the Terminal View is selected
**When** the WebSocket connection to /api/v1/logs/stream is active
**Then** logs stream in real-time with monospace output, color-coded by level
**And** auto-scroll toggle and search within stream (Ctrl+F) are available

**Given** filters are applied but no logs match
**When** the table is empty
**Then** empty state shows: "No logs match your filters." with a "Clear filters" button (UX-DR25)

### Story 7.8: Pages Connections & Performance

As an **IT operator (Laurent)**,
I want Connections and Performance pages showing service health details and system trends,
So that I can monitor integrations and track the agent's accuracy over time.

**Acceptance Criteria:**

**Given** the Connections page is loaded
**When** services are configured
**Then** each service (ERP, Email, LLM, Vector DB, Teams) shows a ServiceHealthIndicator with: status, latency, last activity, error details if degraded (UX-DR11)

**Given** a service is not configured
**When** the Connections page loads
**Then** it shows: "[Service] not configured." with "See CLI: agent config --[service]" hint (UX-DR25)

**Given** the Performance page is loaded
**When** data is available
**Then** it displays: processing time trends, accuracy stats, confidence distribution
**And** numbers follow formatting rules: percentages integer, durations human-readable, trends with arrow + percentage (UX-DR26)

### Story 7.9: Accessibilité WCAG/RGAA & Tests CI

As an **IT operator (Laurent)**,
I want the web UI to meet WCAG 2.1 AA and RGAA accessibility standards with automated testing,
So that the interface is usable by all team members and compliant with French accessibility requirements.

**Acceptance Criteria:**

**Given** the web UI is built
**When** tested for accessibility
**Then** all color contrasts meet WCAG 2.1 AA ratios (UX-DR33)
**And** keyboard navigation works for all interactive elements (tab, Enter, Escape) (UX-DR35)
**And** semantic HTML is used throughout (main, nav, header, section, proper heading hierarchy) (UX-DR36)
**And** ARIA labels exist on all icon-only buttons, live regions on dynamic content (UX-DR37)

**Given** RGAA compliance is required
**When** the HTML is rendered
**Then** lang="en" attribute is set, unique page titles per page, alt text on images, form labels associated (UX-DR38)
**And** browser zoom to 200% works without layout breakage, rem units used for text (UX-DR39)

**Given** CI pipeline runs
**When** frontend tests execute
**Then** axe-core runs with zero critical/serious violations, eslint-plugin-jsx-a11y passes with zero errors, Lighthouse Accessibility >= 95 (UX-DR43)

## Epic 8: Configuration & Règles Métier

Un administrateur métier peut configurer les règles de proposabilité, les seuils de confiance par client, et les règles métier spécifiques — via fichiers de config pour le MVP.

### Story 8.1: Configuration des Filtres de Proposabilité

As a **business administrator**,
I want to configure which products are proposable by the agent (excluding custom, obsolete, or restricted products),
So that the agent only proposes products the company can actually sell.

**Acceptance Criteria:**

**Given** a configuration file defines proposability rules (product families to include/exclude, stock status rules, custom product flags)
**When** the configuration is loaded
**Then** the rules are validated by pydantic-settings with clear error messages for invalid entries
**And** the agent applies these rules during product search filtering (FR42)

**Given** the administrator updates the proposability rules in the config file
**When** the configuration is reloaded (via CLI `agent config reload` or restart)
**Then** the new rules take effect on subsequent requests
**And** the previous configuration version is stored for rollback

**Given** an administrator wants to see current proposability rules
**When** they run `agent config show --proposability`
**Then** the current rules are displayed in a readable format

### Story 8.2: Configuration des Seuils de Confiance par Client

As a **business administrator**,
I want to configure confidence thresholds per client (e.g., stricter thresholds for new clients, relaxed for trusted regulars),
So that the agent's autonomy level matches the business relationship with each client.

**Acceptance Criteria:**

**Given** a configuration file defines per-client confidence thresholds (high/medium/low boundaries)
**When** the agent processes a request from a specific client
**Then** it uses the client-specific thresholds for routing decisions (FR43)
**And** if no client-specific config exists, global default thresholds are used

**Given** a new client threshold configuration is added
**When** the configuration is reloaded
**Then** the new thresholds apply to future requests for that client
**And** the change is logged in the audit trail with before/after values

**Given** an invalid threshold is configured (e.g., high < medium)
**When** validation runs
**Then** a clear error message is produced and the invalid config is rejected

### Story 8.3: Configuration des Règles Métier par Client

As a **business administrator**,
I want to configure client-specific business rules (special conditions, preferred products, pricing exceptions),
So that the agent respects each client's unique commercial relationship.

**Acceptance Criteria:**

**Given** a configuration file defines client-specific business rules (e.g., "Client X always gets 10% discount", "Client Y prefers product family Z")
**When** the agent processes a request from that client
**Then** the business rules are applied as constraints in the reasoning process (FR44)
**And** the applied rules are visible in the reasoning trace

**Given** business rules are versioned in PostgreSQL
**When** a rule change causes issues
**Then** the administrator can rollback to a previous version via CLI `agent config rollback --version N`
**And** the rollback is logged in the audit trail

**Given** an administrator wants to review all rules for a client
**When** they run `agent config show --client [client_name]`
**Then** all applicable rules are displayed: proposability, thresholds, and business rules

## Epic 9: Assurance Qualité & Mode Cohabitation

Le système peut rejouer des scénarios passés pour tests de régression, versionner les prompts/configs avec rollback, et tourner en mode cohabitation pour valider en conditions réelles.

### Story 9.1: Replay de Scénarios (Tests de Régression)

As an **IT operator (Laurent)**,
I want to replay past quote processing scenarios for regression testing,
So that I can validate agent behavior hasn't regressed after updates or configuration changes.

**Acceptance Criteria:**

**Given** a set of test fixtures exists (sample emails, synthetic catalog data, expected outputs) in tests/fixtures/
**When** Laurent runs a scenario replay via CLI (`agent replay --scenario [name]`)
**Then** the agent processes the fixture email through the full pipeline
**And** the output is compared against expected results (product matched, confidence score, draft content)

**Given** a previously processed real quote is stored with its full trace
**When** the replay command is run on that scenario
**Then** the agent reprocesses with current configuration/prompts
**And** differences between original and replayed output are highlighted (FR50)

**Given** multiple scenarios are available
**When** Laurent runs `agent replay --all`
**Then** all scenarios execute in sequence with a summary report: passed, failed, changed

### Story 9.2: Versionnage Prompts & Configs avec Rollback

As an **IT operator (Laurent)**,
I want prompts and agent configurations versioned with rollback capability,
So that a broken prompt or config change can be reverted instantly without downtime.

**Acceptance Criteria:**

**Given** a prompt or configuration is updated
**When** the change is saved
**Then** the new version is stored in PostgreSQL with: version number, timestamp, author, content, diff from previous (FR51)
**And** the previous version remains available for rollback

**Given** a recent prompt change caused degraded accuracy
**When** Laurent runs `agent config rollback --version N`
**Then** the system reverts to version N immediately
**And** subsequent requests use the rolled-back configuration
**And** the rollback action is logged in the audit trail (NFR-R5)

**Given** Laurent wants to compare versions
**When** he runs `agent config diff --from N --to M`
**Then** the differences between versions are displayed clearly

### Story 9.3: Mode Cohabitation

As a **sales rep (Sophie)**,
I want the agent to run in cohabitation mode alongside my manual workflow,
So that I can verify the agent's accuracy before trusting it to process quotes autonomously.

**Acceptance Criteria:**

**Given** the system is configured in cohabitation mode
**When** the agent processes a quote request
**Then** it runs the full pipeline (extraction → search → reasoning → draft creation)
**But** the draft is NOT sent to the ERP and notifications are NOT sent to Sophie (FR52)
**And** the result is stored internally for comparison

**Given** cohabitation mode is active
**When** Sophie processes the same quote manually
**Then** Laurent can compare: agent's proposed draft vs. Sophie's actual quote
**And** the comparison is logged with: match/mismatch, fields that differ, confidence score

**Given** cohabitation results are accumulated over time
**When** Laurent reviews the comparison report
**Then** he sees: accuracy rate, common mismatch patterns, confidence calibration data
**And** this data informs the decision to transition to autonomous mode

## Epic T: Build in Public — Content & Visibility

Cross-cutting epic that runs in parallel with technical epics. Each story produces a LinkedIn post (English) and optionally a Contra portfolio update. Goal: document the journey publicly to build personal brand, attract clients/collaborators, and create accountability.

**Goal:** Regular public content (1 post/week cadence) chronicling the build from prototype to production, anchored on real technical decisions and metrics.

**Guidelines:**
- Language: English
- Tone: technical but accessible, authentic, problem → solution → metric → open question
- Never mention past clients by name or share confidential information
- All content based exclusively on this repo's code, synthetic data, and metrics
- Frame professional experience as domain expertise: "After working on B2B industrial quoting systems professionally..."

**Exit Criteria:**
- Consistent posting cadence maintained throughout development
- LinkedIn profile active with growing engagement
- Contra portfolio showcasing the project as a case study

### Story T.0: Content Pipeline Setup

As a **solo developer building in public**,
I want a content creation workflow set up (templates, guidelines, profiles),
So that I can produce posts efficiently with a consistent voice throughout the project.

**Acceptance Criteria:**
- [ ] AC-T.0.1: LinkedIn bio updated to reflect AI + B2B industrial domain expertise
- [ ] AC-T.0.2: Contra project created with project description and prototype overview
- [ ] AC-T.0.3: Post template created in `_bmad-output/build-in-public/template.md`
- [ ] AC-T.0.4: Content guidelines documented (tone, rules, structure)

### Story T.1: Prototype Launch Post

**After:** Epic 0 completion

As a **solo developer building in public**,
I want to publish my first post announcing the prototype results,
So that I establish my public presence and set the narrative for the series.

**Acceptance Criteria:**
- [ ] AC-T.1.1: LinkedIn post (~200 words) published — hook: "AI that reads messy B2B emails and generates quotes in 3 seconds"
- [ ] AC-T.1.2: Post includes concrete metrics (96.2% accuracy, 2.9s latency, 3/3 scenarios)
- [ ] AC-T.1.3: Contra project page updated with prototype case study (metrics, architecture overview, GO decision)
- [ ] AC-T.1.4: Post draft archived in `_bmad-output/build-in-public/`

### Story T.2: Stack Decision Post

**After:** Stories 1.1–1.2 (scaffold + DB)

As a **solo developer building in public**,
I want to publish a post about the technology choices for production,
So that I share the reasoning behind moving from n8n prototype to Python/LangGraph.

**Acceptance Criteria:**
- [ ] AC-T.2.1: LinkedIn post published — "Why I moved from n8n to Python/LangGraph for production"
- [ ] AC-T.2.2: Post covers trade-offs: prototyping speed vs production control, low-code vs code-first
- [ ] AC-T.2.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.3: Dirty Data Problem Post

**After:** Stories 1.5–1.6 (ERP + email adapters)

As a **solo developer building in public**,
I want to publish a post about the real challenge of industrial product catalogs,
So that I highlight the core problem that makes this project technically interesting.

**Acceptance Criteria:**
- [ ] AC-T.3.1: LinkedIn post published — "The ugly truth about industrial product catalogs"
- [ ] AC-T.3.2: Post includes anonymized examples of catalog noise (from synthetic data only)
- [ ] AC-T.3.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.4: Foundation Recap Post

**After:** Epic 1 completion

As a **solo developer building in public**,
I want to publish a milestone recap of the foundation phase,
So that I mark the transition from prototype to production-ready infrastructure.

**Acceptance Criteria:**
- [ ] AC-T.4.1: LinkedIn post published — "From prototype to production-ready: what I had to rebuild and why"
- [ ] AC-T.4.2: Post reflects on lessons learned during Epic 1
- [ ] AC-T.4.3: Contra project updated with architecture diagram + stack decisions
- [ ] AC-T.4.4: Post draft archived in `_bmad-output/build-in-public/`

### Story T.5: French Industrial Jargon Post

**After:** Stories 2.1–2.2 (IMAP + extraction)

As a **solo developer building in public**,
I want to publish a post about the NLP challenges of French industrial emails,
So that I showcase the domain-specific complexity that generic AI tools miss.

**Acceptance Criteria:**
- [ ] AC-T.5.1: LinkedIn post published — "Teaching an AI to read DN, Ø, lg and French industrial shorthand"
- [ ] AC-T.5.2: Post includes real examples of jargon extraction (from synthetic test fixtures only)
- [ ] AC-T.5.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.6: Error & Edge Cases Post

**After:** Story 2.4 (validation)

As a **solo developer building in public**,
I want to publish a post about handling failure and edge cases in AI pipelines,
So that I show the engineering rigor behind the "happy path" demos.

**Acceptance Criteria:**
- [ ] AC-T.6.1: LinkedIn post published — "What happens when the AI can't understand the email"
- [ ] AC-T.6.2: Post covers graceful degradation, fallback strategies, and escalation design
- [ ] AC-T.6.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.7: It's Alive Post

**After:** Epic 2 completion

As a **solo developer building in public**,
I want to publish a milestone post about the first real email processed end-to-end,
So that I mark the moment the system goes from prototype to functional pipeline.

**Acceptance Criteria:**
- [ ] AC-T.7.1: LinkedIn post published — "First real email processed end-to-end"
- [ ] AC-T.7.2: Post compares prototype metrics vs production metrics
- [ ] AC-T.7.3: Contra project updated with production pipeline results
- [ ] AC-T.7.4: Post draft archived in `_bmad-output/build-in-public/`

### Story T.8: Search Deep Dive Post

**After:** Stories 3.1–3.2 (hybrid search production)

As a **solo developer building in public**,
I want to publish a technical deep dive on the search architecture,
So that I share the hybrid search approach with the AI/ML community.

**Acceptance Criteria:**
- [ ] AC-T.8.1: LinkedIn post published — "96.2% accuracy on 680 products — will it hold on 10,000?"
- [ ] AC-T.8.2: Post covers dense + sparse + RRF fusion approach
- [ ] AC-T.8.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.9: LLM Re-ranking Post

**After:** Story 3.4 (proposability filter) or 3.6 (jargon matching)

As a **solo developer building in public**,
I want to publish a post about adding LLM re-ranking to improve the last few percent of accuracy,
So that I show the iterative improvement process.

**Acceptance Criteria:**
- [ ] AC-T.9.1: LinkedIn post published — "When vector search isn't enough: adding an LLM judge"
- [ ] AC-T.9.2: Post includes before/after accuracy comparison
- [ ] AC-T.9.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.10: Search Recap Post

**After:** Epic 3 completion

As a **solo developer building in public**,
I want to publish a milestone recap of the intelligent search phase,
So that I consolidate the search narrative and share final production metrics.

**Acceptance Criteria:**
- [ ] AC-T.10.1: LinkedIn post published — "Building a search engine that works on data no one cleaned"
- [ ] AC-T.10.2: Contra project updated with search architecture and final metrics
- [ ] AC-T.10.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.11: Confidence Tiers Post

**After:** Stories 4.1–4.2 (complexity classification + confidence scoring)

As a **solo developer building in public**,
I want to publish a post about the confidence-based routing system,
So that I show how the agent handles uncertainty instead of guessing.

**Acceptance Criteria:**
- [ ] AC-T.11.1: LinkedIn post published — "When your AI isn't sure: 3 levels of certainty in quote generation"
- [ ] AC-T.11.2: Post explains high/medium/low confidence routing with concrete examples
- [ ] AC-T.11.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.12: Memory Architecture Post

**After:** Story 4.6–4.7 (ERP reading + quote creation) or Epic 6 stories

As a **solo developer building in public**,
I want to publish a post about the 3-layer memory architecture,
So that I share the design for industry/company/client memory and how it improves over time.

**Acceptance Criteria:**
- [ ] AC-T.12.1: LinkedIn post published — "An AI that remembers: 3-layer memory for B2B quoting"
- [ ] AC-T.12.2: Post covers industry knowledge, company context, and client preferences
- [ ] AC-T.12.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.13: Intelligence Recap Post

**After:** Epic 4 completion

As a **solo developer building in public**,
I want to publish a milestone recap of the adaptive reasoning phase,
So that I mark the transition from "matcher" to "reasoning agent."

**Acceptance Criteria:**
- [ ] AC-T.13.1: LinkedIn post published — "From pattern matching to reasoning: how the agent got smarter"
- [ ] AC-T.13.2: Contra project updated with intelligence layer architecture and metrics
- [ ] AC-T.13.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.14: Human-AI Collaboration Post

**After:** Stories 5.2–5.3 (review UI + notifications)

As a **solo developer building in public**,
I want to publish a post about designing the human-in-the-loop workflow,
So that I share why full automation is the wrong goal for high-stakes B2B decisions.

**Acceptance Criteria:**
- [ ] AC-T.14.1: LinkedIn post published — "Why full automation is a trap: designing the human-in-the-loop"
- [ ] AC-T.14.2: Post covers trust, oversight, and the notification/review workflow
- [ ] AC-T.14.3: Post draft archived in `_bmad-output/build-in-public/`

### Story T.15: Full Loop Recap Post

**After:** Epic 5 completion

As a **solo developer building in public**,
I want to publish a final milestone post celebrating the complete pipeline,
So that I close the build-in-public series with a comprehensive retrospective.

**Acceptance Criteria:**
- [ ] AC-T.15.1: LinkedIn post published — "The complete pipeline: email → AI → human review → quote sent"
- [ ] AC-T.15.2: Contra project fully updated as a polished case study
- [ ] AC-T.15.3: Series retrospective: what worked, what didn't, metrics evolution from prototype to production
- [ ] AC-T.15.4: Post draft archived in `_bmad-output/build-in-public/`
