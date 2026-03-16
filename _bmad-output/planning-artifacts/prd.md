---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-ai-quote-agent-2026-03-15.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-03-14-session.md'
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 1
  projectDocs: 0
classification:
  projectType: 'SaaS B2B (self-hosted first)'
  domain: 'Industrial Sales Automation / ERP Integration'
  complexity: 'high'
  projectContext: 'greenfield'
workflowType: 'prd'
date: 2026-03-15
author: Khalil
lastEdited: 2026-03-15
editHistory:
  - date: 2026-03-15
    changes: 'Validation-driven fixes: FR5/FR8/FR15/FR17/FR21 measurability and implementation leakage, NFR security measurement methods, NFR scalability/integration rephrasing, added Journey 7 (zero-preprocessing), added coverage rate KPI'
---

# Product Requirements Document - ai-quote-agent

**Author:** Khalil
**Date:** 2026-03-15

## Executive Summary

AI Quote Agent is an autonomous AI agent that processes B2B quote requests end-to-end — from email reception to draft quote creation in the company's ERP. It targets inside sales teams in industrial companies who spend 3-20 minutes per quote request navigating massive, messy product catalogs and manually building quotes. The agent reasons like a skilled sales rep: it classifies requests by complexity, searches products semantically, manages its own uncertainty through confidence tiers, and learns from every validated quote. Sales reps shift from building quotes to validating them — in seconds, not minutes.

Built on hard-won lessons from a v1 deployed at ArcelorMittal (pipeline LLM + microservices + Solr), the v2 is a ground-up rebuild as a true autonomous agent. The timing is right: LLMs alone proved insufficient (fragile pipelines, rigid rules, manual data cleanup), but agent architectures have reached the maturity needed for reliable, adaptive reasoning in production.

### What Makes This Special

**"Branchez et c'est opérationnel."** Unlike CPQ tools and traditional solutions that demand months of data cleanup, catalog structuring, and IT projects before delivering value, AI Quote Agent works with dirty product catalogs out of the box. The intelligent representation layer adapts to the data — not the other way around. This eliminates the #1 frustration from the v1: weeks spent manually cleaning product databases just to make search work.

The core insight is architectural: an agent with adaptive reasoning (simple/ambiguous/complex/out-of-scope routing), 3-layer memory (industry/company/client), and built-in uncertainty management delivers what a pipeline LLM cannot — the ability to reason, doubt, learn, and improve with every interaction. The emergent knowledge graph, built passively over time, creates a competitive moat that deepens with data volume and is impossible for competitors to replicate.

## Project Classification

- **Project Type:** SaaS B2B (self-hosted first, potential SaaS tier for smaller companies)
- **Domain:** Industrial Sales Automation / ERP Integration
- **Complexity:** High — multi-ERP abstraction, sensitive data (pricing, clients), 3-layer adaptive memory, semantic search on unstructured catalogs, confidence-based decision routing
- **Project Context:** Greenfield — complete rebuild from v1 learnings, Python/LangGraph stack

## Success Criteria

### User Success

- **Quote processing transformation**: Sales reps shift from building quotes (3-20 min) to validating agent-prepared drafts (seconds). The "aha moment" is the first morning where the entire queue is processed in half the usual time.
- **Trust through transparency**: Agent expresses its confidence level — high confidence drafts go straight to review, uncertain cases come with multiple proposals or enriched context for the rep to decide. No black-box surprises.
- **Reduced cognitive load**: Reps no longer navigate the product catalog manually. The agent handles catalog complexity, freeing reps for high-value work (client relationships, complex technical advice).

### Business Success

No formal business metrics tracked. Product success is measured purely on agent performance — if the agent works well, business outcomes follow naturally. This is a deliberate choice: build something that works, not something that reports.

### Technical Success

| Metric | Target | Measurement |
|--------|--------|-------------|
| **End-to-end processing time** | < 2 minutes | Email arrival → draft quote in ERP |
| **Product matching accuracy** | > 95% | Correct product matched vs. commercial correction rate (simple cases) |
| **Complete quote accuracy** | > 95% | Draft quote sent without any commercial modification (simple cases) |
| **System uptime** | > 99.5% | Agent availability during business hours |
| **Search latency** | < 3s | Product search response time (hybrid vector + keyword) |
| **New client deployment time** | < 1 day | From infrastructure setup to first processed quote |
| **Zero preprocessing validation** | Pass/Fail | System works with raw, uncleaned synthetic product catalog |

| **Coverage rate** | To be defined | Percentage of incoming quote requests the agent can process (vs. requiring full manual handling) — deferred to post-MVP once real-world usage data is available |

### Measurable Outcomes

- Agent processes simple quote requests end-to-end without human intervention (beyond validation)
- Product matching works on dirty catalog data without manual cleanup
- Successful integration with Odoo Community as test ERP
- Every agent decision is traceable and diagnosable (structured logs, reasoning traces)

## User Journeys

### Journey 1: Sophie — The Happy Path (Simple Quote)

Sophie, 28, arrives at the office Monday morning. 14 quote request emails are waiting. Before the agent, that was 2 hours of mechanical work. Now, she opens Teams: the agent has already processed the queue. First quote — a regular client orders 200 stainless steel tubes, clear reference. The agent generated the complete draft in Odoo: right product, right price, right quantities. Sophie verifies in 10 seconds, validates, sends to client. Next. In 30 minutes, her morning is done. She spends the rest calling back a client on a complex project — the kind of work she actually enjoys.

**Capabilities revealed:** Email processing, product matching, ERP draft creation, Teams/email notification, one-click validation flow.

### Journey 2: Sophie — The Ambiguous Case (Multi-Proposals)

An email arrives: "500 steel bars, like last time but longer". The agent classifies the request as ambiguous — the client didn't specify the grade or exact dimensions. The agent generates 3 proposals based on client history and similar products: (1) same product as last order in 6m instead of 3m, (2) a variant with surface treatment, (3) a standard catalog product matching the description. Sophie sees the 3 options in her Teams notification, immediately recognizes the first as correct, selects it, and sends. 15 seconds instead of 10 minutes searching the catalog.

**Capabilities revealed:** Request classification, ambiguity detection, client memory (few-shot from history), multi-proposal generation, confidence tiers, quick selection interface.

### Journey 3: Sophie — Error Correction (Learning Loop)

The agent proposes a quote with an almost-correct product — right family, but wrong thickness. Sophie corrects the thickness in the ERP draft and sends. This correction is captured by the agent: next time this client orders a similar product, the agent will know this client prefers that specific thickness. Today's error makes the agent more accurate tomorrow.

**Capabilities revealed:** Draft editing in ERP, correction capture, feedback loop, client profile enrichment, continuous learning.

### Journey 4: Marc — Performance Visibility

Marc, regional director, receives a weekly Teams summary report every Friday: number of quotes processed by the agent this week, accuracy rate, average processing time, and cases where the agent escalated. He sees the accuracy rate went from 91% to 96% in one month — the agent is learning. He also sees that Sophie now processes 40 quotes/day instead of 30, with fewer errors. Marc shares the numbers at the team meeting.

**Capabilities revealed:** Periodic reporting (Teams/email), performance metrics aggregation, accuracy trend tracking, team-level dashboards.

### Journey 5: Laurent — Deployment & Monitoring

Laurent, IT ops, deploys the agent on the company's infrastructure. He connects the agent to the mail server and Odoo via configuration. Day one: he monitors structured logs — every agent decision is traceable (why this product, what confidence score, which memory was used). He configures alerts for critical errors (ERP connection lost, LLM timeout, abnormal error rate). Day-to-day, he checks a dashboard (CLI or web) showing uptime, latency, quote volume processed, and active alerts. When a problem occurs, he receives an alert and can diagnose via reasoning traces.

**Capabilities revealed:** Self-hosted deployment, ERP/email configuration, structured logging, reasoning traces, alerting system, monitoring dashboard (CLI/web), decision traceability.

### Journey 6: Admin — Business Rules Configuration

A business administrator (e.g., a senior sales manager) configures the agent's rules for their company: which products are proposable, which clients have special conditions, what confidence thresholds to apply, which product families to exclude. They access a configuration interface to adjust these parameters without touching code. When a new product is added to the catalog or a business rule changes, they update the configuration and the agent adapts immediately.

**Capabilities revealed:** Business rules configuration interface, proposability filter management, confidence threshold tuning, client-specific rules, no-code configuration, dynamic rule updates.

### Journey 7: Laurent — Zero-Preprocessing Onboarding

Laurent connects the agent to the company's Odoo instance. The product catalog is a mess: 45,000 references with inconsistent naming, duplicate entries for the same product with different codes, one-off custom items mixed in with standard products, missing metadata on half the entries, and abbreviations that only the sales team understands. Laurent does not clean any of it. He points the agent at the catalog API, triggers ingestion, and waits. The agent indexes everything as-is. The next morning, Sophie sends a test request: "200 tubes inox 304L Ø25 lg 6m". The agent returns the correct product — matched through semantic understanding despite the catalog entry reading "TUBE ROND SS 304L 25x1.5 LONGUEUR 6000mm". No synonyms configured, no manual mapping, no Solr tuning. Laurent checks three more test cases with jargon and abbreviations — all matched correctly. The system is operational in under a day, on raw data.

**Capabilities revealed:** Zero-preprocessing catalog ingestion, semantic product matching on dirty data, jargon/abbreviation handling without manual configuration, rapid deployment timeline.

### Journey Requirements Summary

| Capability Area | Revealed By Journeys |
|----------------|---------------------|
| Email processing & extraction | Sophie (all) |
| Product matching (hybrid search) | Sophie happy path, ambiguous |
| Multi-proposal generation | Sophie ambiguous |
| Confidence tiers & routing | Sophie ambiguous, error correction |
| ERP integration (draft creation) | Sophie (all) |
| Notification system (Teams/email) | Sophie (all), Marc |
| Client memory & learning | Sophie ambiguous, error correction |
| Feedback loop (correction capture) | Sophie error correction |
| Performance reporting | Marc |
| Deployment & configuration | Laurent |
| Monitoring & observability | Laurent |
| Alerting system | Laurent |
| Business rules configuration | Admin |
| Proposability filter management | Admin |
| Zero-preprocessing catalog ingestion | Laurent (zero-preprocessing) |
| Semantic matching on dirty data | Laurent (zero-preprocessing) |

## Domain-Specific Requirements

### Data Privacy & Sensitivity

- **Self-hosted architecture**: All data (client info, pricing, order history, product catalog) stays on the client's infrastructure. No data leaves the perimeter.
- **LLM provider is the client's responsibility**: The solution is LLM-agnostic — the client chooses their provider (Azure OpenAI, local model, etc.). The agent provides the technical solution, not the AI infrastructure.
- **SaaS tier data handling**: Deferred — no solution defined yet for smaller clients who want hosted deployment. To be addressed post-MVP.
- **Confidential pricing**: Prices must never leak into logs, traces, or external API calls beyond the client's chosen LLM provider.

### Security

- **Prompt injection mitigation**: Must be addressed from MVP. Email content (untrusted user input) must be strictly separated from agent instructions. Defense-in-depth approach: input sanitization, instruction/data boundary enforcement, output validation via self-review.
- **Principle of least privilege**: Agent creates draft quotes only — never final quotes. Read-only access to product catalog. No destructive operations on ERP data.
- **Authentication & access control**: Agent access to ERP and email systems uses scoped credentials with minimal permissions.
- **Export controls & illegal requests**: Agent must detect and flag requests that may involve sanctioned entities, export-controlled products, or otherwise illegal transactions.

### Integration Constraints

- **ERP integration**: Draft-only write access to ERP (Odoo for MVP). Read access to product catalog, client data, and order history. Abstraction layer designed for future multi-ERP support.
- **Email integration**: Read access to incoming quote request emails. Send notifications via Teams or email (no direct client-facing email from agent).
- **LLM integration**: Abstraction layer — swap providers without code changes. Client configures their own endpoint, API key, and model.

### Audit & Traceability

- **Formal audit trail**: Every agent decision must be auditable — immutable logs capturing: what was decided, why (reasoning trace), what data was used, what confidence score, what memory was consulted.
- **Long-term retention**: Audit logs retained for compliance purposes (retention period configurable per client).
- **Decision traceability**: Full reasoning chain from email reception to draft quote, reconstructable after the fact for any processed quote.

### Risk Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Prompt injection via client email | Agent manipulated into wrong behavior | Input/instruction separation, sanitization, self-review validation |
| Wrong product matched | Client receives incorrect quote, trust eroded | Confidence tiers, multi-proposals for uncertain cases, self-review |
| Confidential data leak | Pricing/client data exposed | Self-hosted, no external data transfer beyond client's LLM provider |
| ERP data corruption | Damaged production data | Draft-only access, read-only catalog, least privilege |
| LLM hallucination (nonexistent product) | Quote with fake product | Product matching against real catalog only, self-review validation |
| Audit failure | Unable to explain agent decision | Immutable structured logs, full reasoning traces |
| Export-controlled or illegal request | Legal liability | Detection and flagging of sanctioned entities and controlled products |

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Zero-Preprocessing Product Catalog Ingestion**
The core promise: the agent works with dirty, unstructured product catalogs without manual cleanup. Instead of forcing clean data, an intelligent representation layer (vector embeddings + hybrid search) handles the messiness. This directly eliminates the #1 pain point from v1 (weeks of manual catalog cleaning for Solr).

**2. Autonomous Agent with Uncertainty Management**
A paradigm shift from pipeline LLM (linear, fire-and-forget) to an agent that classifies request complexity, applies different reasoning strategies, expresses doubt through confidence tiers, and proposes alternatives when uncertain. No existing B2B quoting solution operates this way.

**3. Emergent Knowledge Graph (Post-MVP)**
A competitive moat built through passive observation: the agent logs every successful product match, detects patterns over time, and activates discovered relationships as context enrichment. The more quotes processed, the smarter the agent becomes — impossible for competitors to replicate without equivalent data volume.

### Open Questions & Unknowns

These are genuine unknowns that need exploration during prototype/MVP:

**Catalog Ingestion Reality:**
- How do ERPs actually expose product catalogs? API? Export? Multiple fragmented files?
- What happens when the catalog is split across different sources or formats?
- Can the agent ingest directly from ERP APIs, or does it need an intermediate step?
- What's the minimum viable ingestion path that still delivers on the "just plug it in" promise?

**Emergent Knowledge Graph:**
- Never built before by the team — concept is theoretical at this stage
- Validation approach undefined — needs research and experimentation post-MVP
- Core question: how much data volume is needed before patterns become meaningful?

### Validation Approach

| Innovation | Validation Method | When |
|-----------|-------------------|------|
| Zero-preprocessing | Benchmark on synthetic dirty catalog — measure matching accuracy vs. manually cleaned catalog | Prototype (n8n) + MVP |
| Catalog ingestion flexibility | Test with Odoo API first, then simulate fragmented exports | MVP |
| Adaptive reasoning | Compare classification accuracy across request types on test dataset | MVP |
| Uncertainty management | Measure correlation between confidence scores and actual accuracy | MVP |
| Emergent graph | Deferred — requires data volume from production usage | Post-MVP (v2.1-v2.3) |

### Innovation Risk Mitigation

| Innovation Risk | Fallback |
|----------------|----------|
| Zero-preprocessing doesn't hold on certain catalog types | Accept minimal preprocessing as an option — the goal is to minimize it, not necessarily eliminate it 100% of the time |
| ERP catalog access is fragmented or inconsistent | Build flexible ingestion layer that supports multiple input methods (API, file export, mixed) |
| Confidence scores don't correlate with actual accuracy | Calibrate thresholds empirically per client, start conservative (more escalation, fewer autonomous decisions) |
| Emergent graph doesn't produce meaningful patterns | The agent works without the graph — it's an enhancement, not a dependency. No graph = no loss of core functionality |

## SaaS B2B Specific Requirements

### Tenant Model

- **MVP**: Single-tenant, self-hosted. Each client runs their own instance with full data isolation by design.
- **Future SaaS tier**: Architecture undecided (multi-tenant shared vs. single-tenant hosted). Decision deferred — no premature optimization on a model that doesn't exist yet.
- **Design principle**: Keep the codebase tenant-aware from the start (configuration per client, data scoping) so that either model is viable later.

### Permission Model (RBAC)

| Role | Capabilities |
|------|-------------|
| **Sales Rep** (Sophie) | View agent-prepared drafts, validate/correct/send quotes, provide feedback |
| **Sales Manager** (Marc) | View performance reports, team-level metrics, accuracy trends |
| **IT Ops** (Laurent) | Deploy, configure infrastructure, monitor system health, manage alerts, access logs |
| **Business Admin** | Configure business rules, proposability filters, confidence thresholds, client-specific rules |

### Subscription & Monetization Readiness

No pricing model defined — deliberate choice to focus on building a product that works first. Architecture should make future monetization straightforward:

- **Metered primitives**: Track usage at natural boundaries (quotes processed, users, ERP connections) so any pricing model can be applied later.
- **Feature boundaries**: Keep capabilities modular so tiers can be created by enabling/disabling modules (e.g., emergent graph, multi-ERP, advanced reporting).
- **No premature tier design**: Don't build tier logic — just ensure the data and architecture make it easy to add later.

### Integration Architecture

| Integration | MVP | Approach |
|------------|-----|----------|
| **ERP** | Odoo Community | Abstraction layer with adapter pattern. Agent produces universal quote format, adapter translates to ERP-specific API. |
| **Email** | IMAP ingestion | Read incoming quote request emails. Standard protocol, works with any mail server. |
| **Notification channel** | Teams or email | Modular "communication channel" abstraction — adapter pattern: Teams, Slack, WhatsApp, email, webhook — all interchangeable. |
| **LLM** | Client's choice | Abstraction layer — client configures their provider (Azure OpenAI, local model, etc.). |

### Implementation Considerations

- **Adapter pattern everywhere**: ERP, notification channels, LLM providers — all behind abstraction layers. Adding a new ERP or notification channel = new adapter, not codebase change.
- **Configuration-driven**: Client-specific behavior (business rules, thresholds, channel preferences) lives in configuration, not code.
- **Monolith modulaire**: Single Python service with LangGraph, modular internally. Horizontal scaling by adding instances, not by splitting services.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — deliver the full agent experience on simple cases. The differentiator IS the agent behavior (reasoning, uncertainty, learning), not a stripped-down pipeline. Cutting adaptive reasoning or memory would produce a v1 clone, defeating the entire purpose.

**Resource Requirements:** Solo developer (Khalil) + AI agent team (BMAD). Capable setup for a focused product — requires ruthless prioritization on what gets built first.

**Adoption Strategy:** Cohabitation phase — the agent runs alongside existing human workflows during initial deployment. Sales reps process quotes in parallel with the agent to build trust and validate accuracy before transitioning to agent-first workflows.

### Prototype Phase (n8n) — Pre-MVP

**Goal:** Validate the riskiest assumption before investing in the full Python build.

**Focus:** Catalog ingestion + product matching on dirty data. This is the #1 technical risk — if the agent can't find the right product in a messy catalog, nothing else matters.

**Prototype validates:**
- Can hybrid search (vector + keyword) match products accurately on raw, uncleaned catalog data?
- What does the ingestion path look like? (Odoo API? Export? Mixed?)
- End-to-end flow: email → extraction → search → draft generation
- Architecture viability before committing to Python/LangGraph

**Prototype does NOT need:** Adaptive reasoning, memory layers, production-grade observability, security hardening.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Sophie happy path (simple quote, end-to-end)
- Sophie ambiguous case (multi-proposals)
- Sophie error correction (learning loop)
- Laurent deployment & monitoring (basic)

**Must-Have Capabilities:**

| # | Capability | Justification |
|---|-----------|---------------|
| 1 | Email processing (reception, cleaning, extraction) | Entry point — without this, nothing works |
| 2 | Hybrid product search (vector + keyword) on raw catalog | Core differentiator — zero-preprocessing promise |
| 3 | Proposability filter | Prevents agent from proposing custom/obsolete products |
| 4 | Adaptive reasoning (simple/ambiguous/complex/out-of-scope) | THIS is what makes it an agent, not a pipeline |
| 5 | 3-layer memory (industry/company/client) | What makes the agent better over time |
| 6 | Confidence tiers with routing | Uncertainty management — high/medium/low → different actions |
| 7 | Self-review before submission | Safety net — agent checks its own work |
| 8 | ERP integration (Odoo Community) | Output — draft quote in ERP |
| 9 | Observability (structured logs, reasoning traces) | Debuggability + audit trail |
| 10 | Notification channel (at least one: email or Teams) | How Sophie knows a quote is ready |
| 11 | Prompt injection defense | Security — must be there from day 1 |

**Deferred from MVP (explicitly NOT in scope):**
- Marc's reporting dashboard (manual query of logs is acceptable for MVP)
- Admin business rules UI (configuration via files/env for MVP)
- Multiple notification channels (one is enough for MVP)
- Multiple ERP adapters (Odoo only)

### Post-MVP Roadmap

**Phase 2 — Growth:**
- Emergent knowledge graph (v2.1-v2.3: logging → pattern detection → graph activation)
- Marc's performance reporting dashboard
- Admin business rules configuration UI (no-code)
- Additional notification channel adapters (Slack, WhatsApp, webhook)
- Attachment processing (PDF, Excel)
- Multi-language email support
- Calibration on historical quotes for faster onboarding

**Phase 3 — Expansion:**
- Multi-ERP adapters (SAP, Dynamics, Oracle) + RPA fallback
- Progressive autonomy (gradual removal of human validation)
- SaaS tier for smaller companies
- Cross-client knowledge graph (opt-in, anonymized)
- Interactive agent-commercial chat
- Industry templates for accelerated onboarding

### Risk Mitigation Strategy

| Risk | Severity | Mitigation |
|------|----------|------------|
| Dirty catalog matching fails | Critical | Prototype phase (n8n) validates FIRST. Fallback: accept minimal preprocessing if needed. |
| Catalog ingestion path unclear | High | Explore with Odoo API in prototype. Build flexible ingestion layer supporting multiple methods. |
| LLM reasoning quality insufficient | Medium | LLM-agnostic — swap models. Self-review catches bad outputs. Confidence tiers route uncertain cases to humans. |
| Prompt injection via email | Medium | Defense-in-depth from MVP: input/instruction separation, sanitization, self-review. |
| Solo dev bottleneck | Medium | AI agent team (BMAD) augments capacity. Prototype de-risks before major investment. |

## Functional Requirements

### Email Processing & Extraction

- FR1: The agent can receive and process incoming quote request emails automatically
- FR2: The agent can clean email content (signatures, threads, noise) to extract the actual request
- FR3: The agent can extract structured data from email body (client identity, requested products, quantities, specifications)
- FR4: The agent can detect and handle multiple quote requests within a single email

### Product Search & Matching

- FR5: The agent can search products using semantic understanding and exact reference matching on raw, uncleaned product catalogs
- FR6: The agent can filter out non-proposable products (custom, obsolete, out-of-stock) before search results
- FR7: The agent can match client-specific terminology, abbreviations, and jargon to catalog products
- FR8: The agent can generate 2-5 product proposals when a single best match is uncertain
- FR9: The agent can ingest product catalog data from ERP (API or export) without manual preprocessing
- FR10: The agent can cache search results for similar or recurring requests to reduce processing time and LLM costs

### Adaptive Reasoning & Decision

- FR11: The agent can classify incoming requests by complexity (simple / ambiguous / complex / out-of-scope)
- FR12: The agent can apply different reasoning strategies based on request classification
- FR13: The agent can calculate a confidence score for each product match and quote decision
- FR14: The agent can route decisions based on confidence tiers: high (>85%) → draft ready, medium (50-85%) → multi-proposals, low (<50%) → escalation with context
- FR15: The agent can detect out-of-scope requests and notify the sales rep with enriched context explaining why the request is out of scope
- FR16: The agent can route requests to different LLM models based on complexity (lighter models for simple cases, more capable models for complex ones)

### Memory & Learning

- FR17: The agent can access industry-level knowledge (conventions, norms, defaults) from a shared knowledge base
- FR18: The agent can access company-level context (catalog, business rules, workflows)
- FR19: The agent can access client-level memory (past quotes, preferences, habits) for personalized matching
- FR20: The agent can capture sales rep corrections and use them to improve future matching (feedback loop)
- FR21: The agent can use validated past quotes as contextual examples for similar future requests
- FR22: The agent can detect recurring quote patterns ("same as last month") and propose reuse of previous quotes
- FR23: The agent can be calibrated on historical quotes during onboarding to accelerate cold start

### Quality Assurance & Safety

- FR24: The agent can self-review its own output before submission to ERP
- FR25: The agent can detect and mitigate prompt injection attempts in email content
- FR26: The agent can separate untrusted input (email) from agent instructions (system prompts)
- FR27: The agent can validate that proposed products exist in the current catalog (anti-hallucination)
- FR28: The agent can detect and flag requests involving export-controlled products or sanctioned entities

### ERP Integration

- FR29: The agent can create draft quotes in the ERP (Odoo Community for MVP)
- FR30: The agent can read product catalog data from the ERP
- FR31: The agent can read client data and order history from the ERP
- FR32: The agent can produce quotes in a universal format that is translated to ERP-specific format via adapter

### Notification & Communication

- FR33: The agent can notify sales reps when a quote is ready for review (via at least one channel)
- FR34: The agent can present multi-proposal options to sales reps for selection
- FR35: The agent can notify sales reps when a request has been escalated with enriched context
- FR36: The notification system can support multiple channel adapters (Teams, Slack, email, webhook)

### Observability & Audit

- FR37: The system can log every agent decision with full reasoning trace (structured logs)
- FR38: The system can maintain an immutable audit trail of all quote processing decisions
- FR39: The system can trace the complete decision chain from email to draft quote for any processed request
- FR40: The system can generate alerts for critical errors (ERP connection lost, LLM timeout, abnormal error rate)
- FR41: The system can expose monitoring data via dashboard (CLI or web) showing uptime, latency, volume, alerts

### Configuration & Administration

- FR42: An administrator can configure proposability filter rules (which products are proposable)
- FR43: An administrator can configure confidence thresholds per client
- FR44: An administrator can configure client-specific business rules
- FR45: An IT operator can deploy the agent on client infrastructure (self-hosted)
- FR46: An IT operator can configure ERP and email connections
- FR47: An IT operator can configure the LLM provider (endpoint, API key, model)
- FR48: An IT operator can configure notification channel preferences
- FR49: An IT operator can configure model routing rules (which LLM model for which complexity level)

### Testing & Quality

- FR50: The system can replay past quote processing scenarios for regression testing and validation
- FR51: The system can version prompts and agent configurations with rollback capability
- FR52: The system can run in cohabitation mode (agent processes in parallel with human, results compared but not sent)

## Non-Functional Requirements

### Performance

| Requirement | Target | Context |
|------------|--------|---------|
| End-to-end quote processing | < 2 minutes | From email arrival to draft quote in ERP |
| Product search latency | < 3 seconds | Hybrid search response time on raw catalog |
| Email extraction | < 10 seconds | Cleaning + structured data extraction |
| Confidence scoring | < 5 seconds | Classification + confidence calculation |
| Notification delivery | < 30 seconds | From draft creation to sales rep notification |
| Cache hit response | < 1 second | For recurring or similar requests with cached results |

### Security

- All data at rest encrypted on client infrastructure, as verified by infrastructure security audit
- All data in transit uses TLS encryption, as verified by TLS certificate validation and penetration testing
- Email content (untrusted input) processed in isolation from agent instructions, as verified by input boundary testing
- ERP credentials stored securely (not in plaintext configuration), as verified by secrets management audit
- Agent operates on principle of least privilege: draft-only ERP write, read-only catalog, as verified by permission scope testing
- Audit logs immutable — no modification or deletion after creation, as verified by tamper-detection checks
- Confidential data (pricing, client info) never appears in external-facing logs or traces beyond the client's chosen LLM provider, as verified by log content scanning
- LLM API calls use the client's own credentials and endpoint — no shared keys
- Export-controlled product detection active from MVP

### Scalability

- System handles at least 300 quotes/day per instance (10 agencies × 30 quotes/day) without performance degradation
- System scales linearly with demand without requiring architectural changes
- Peak handling: Monday morning spikes (up to 3x average volume) without failures or significant latency increase
- Catalog size: supports at least 50,000 product references per instance

### Reliability

- System uptime > 99.5% during business hours
- Graceful degradation: if LLM provider is unavailable, queue emails for later processing rather than losing them
- ERP connection failure: buffer draft quotes and retry, notify IT via alert
- No data loss: every received email acknowledged and tracked to completion or explicit failure
- Prompt and configuration versioning with rollback prevents broken deployments

### Integration

- ERP adapter interface versioned with semantic versioning — adding a new ERP does not break existing adapter contracts
- LLM provider interface supports hot-swapping without system restart
- Notification channel interface allows adding new channels via adapter implementation only
- Email ingestion supports standard IMAP protocol for maximum compatibility
- All integrations have health checks and automated alerting on failure
