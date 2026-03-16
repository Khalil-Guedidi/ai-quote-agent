---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - '_bmad-output/brainstorming/brainstorming-session-2026-03-14-session.md'
date: 2026-03-15
author: Khalil
---

# Product Brief: ai-quote-agent

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

AI Quote Agent is an autonomous AI agent that transforms how B2B sales teams handle quote requests. It processes incoming emails, understands client needs, matches products from complex catalogs, and generates draft quotes in the company's ERP — so sales reps only need to validate and send. Built on hard-won insights from a v1 deployed at ArcelorMittal, the product embraces real-world messiness: dirty product databases, implicit client knowledge, and rigid enterprise systems. Positioned as a self-hosted-first SaaS solution for industrial companies of all sizes.

---

## Core Vision

### Problem Statement

Inside sales representatives in B2B industrial companies face an unsustainable daily workload: processing ~30 quote request emails per day per agency, each taking 3-20 minutes to handle. The work involves navigating massive, complex product catalogs, interpreting ambiguous client requests, and manually creating quotes in ERP systems. This repetitive, high-stakes work drives one of the highest turnover rates across sales roles — reps burn out from the monotony of sitting in an agency processing emails all day against an overwhelming product catalog.

### Problem Impact

- **Lost deals**: A late quote is often an unsigned quote — every delay directly impacts revenue
- **Product errors**: The most common mistakes are selecting the wrong product or one not suited to the client, eroding client trust and generating costly rework
- **Talent drain**: High turnover means constant recruitment, training, and loss of accumulated client knowledge — each departing rep takes implicit know-how with them
- **Scaling bottleneck**: Revenue growth requires proportionally more sales reps, making the model increasingly expensive to scale

### Why Existing Solutions Fall Short

Current approaches — whether manual processing, ERP configurators, or CPQ tools — all share a fundamental assumption: that product data is clean, structured, and well-maintained. In reality, industrial product catalogs are messy: full of duplicates, one-off custom products, inconsistent naming, and missing metadata. The v1 experience at ArcelorMittal proved this directly — weeks were spent manually cleaning the product database for Solr search, accumulating brittle hardcoded business rules, and constantly patching edge cases. Traditional solutions demand the enterprise adapt to the tool. The real world doesn't work that way.

### Proposed Solution

An autonomous AI agent that processes quote requests end-to-end: from email reception to draft quote creation in the ERP. The agent reasons like a skilled sales rep — classifying requests by complexity, searching products semantically (no manual catalog cleanup needed), managing its own uncertainty through confidence tiers, and learning from every interaction. Sales reps shift from doing the work to validating it, with a long-term vision of full autonomy requiring no human validation at all.

### Key Differentiators

- **Zero preprocessing**: Works with dirty product catalogs out of the box — intelligent representation layer instead of manual data cleanup, eliminating the #1 frustration from v1
- **Adaptive reasoning**: Classifies requests (simple/ambiguous/complex/out-of-scope) and applies the right reasoning pattern, like a skilled sales rep would
- **3-layer memory**: Industry, company, and client-level knowledge that makes the agent better with every quote processed
- **ERP-agnostic**: Universal abstraction layer with adapters for SAP, Odoo, Dynamics, Oracle — and RPA fallback for legacy systems
- **Self-hosted first**: Sensitive data never leaves the client's infrastructure, with a potential SaaS tier for smaller companies
- **Emergent knowledge graph**: A competitive moat that deepens over time — product relationships discovered through passive observation, impossible for competitors to replicate without the data volume

## Target Users

### Primary Users

#### 1. The Inside Sales Rep — "Sophie, 28, Industrial Sales Rep"
- **Role & Context**: Sedentary sales rep in a regional agency, technically skilled with deep product catalog knowledge. Works daily in Outlook + ERP, processing ~30 quote request emails per day.
- **Motivations**: Wants to do her job well, but drowning in repetitive email-to-quote processing. Knows the catalog but still spends 3-20 minutes per quote navigating it.
- **Pain**: The monotony is draining — she's considering leaving like many of her colleagues. Most of her day is mechanical work that doesn't leverage her actual expertise (client relationships, complex technical advice).
- **Success with AI Quote Agent**: Sophie reviews and sends agent-prepared draft quotes instead of building them from scratch. She reclaims time for high-value work — advising clients, handling complex cases, building relationships. The boring part of her job largely disappears.

#### 2. The Sales Manager — "Marc, 45, Regional Sales Director"
- **Role & Context**: Oversees a team of sales reps across one or more agencies. Needs quotes sent fast and accurate — speed and quality directly impact revenue.
- **Motivations**: Team performance, conversion rates, reducing turnover. Every late or incorrect quote is a potential lost deal.
- **Pain**: High turnover means constant onboarding of new reps who take weeks to learn the catalog. Hard to maintain consistent quality across the team.
- **Success with AI Quote Agent**: Quotes go out faster with fewer errors. New reps are productive sooner because the agent handles catalog complexity. Marc gets visibility into quote processing metrics and team performance.

### Secondary Users

#### 3. The IT Team — "Laurent, 38, IT Operations Lead"
- **Role & Context**: Internal IT team or external integrator responsible for deploying, integrating, and monitoring the solution. Manages the bridge between the agent and existing infrastructure (ERP, email, security).
- **Motivations**: Stability, security, minimal maintenance overhead. Sensitive data (pricing, client info) must stay protected.
- **Pain**: New tools often mean integration headaches, security risks, and support tickets. ERP integrations are notoriously fragile.
- **Success with AI Quote Agent**: Self-hosted deployment keeps data in-house. ERP-agnostic abstraction layer means clean integration. Monitoring dashboards provide operational visibility without constant manual oversight.

### User Journey

1. **Discovery**: The sales manager or company leadership identifies the quote processing bottleneck as a growth blocker. They discover AI Quote Agent through industry channels or direct outreach.
2. **Onboarding**: IT deploys the self-hosted solution and connects it to the company's ERP and email system. The agent ingests the product catalog as-is — no cleanup required. Initial phase runs in observation/assisted mode alongside existing workflows.
3. **Core Usage**: Sales reps receive agent-prepared draft quotes in their workflow. Simple quotes arrive ready to validate and send. Ambiguous cases come with multiple product suggestions to choose from. Complex cases are flagged with enriched context.
4. **Success Moment**: The first week Sophie realizes she processed her entire morning queue in half the usual time — and the quotes were accurate. Marc sees average quote response time drop significantly.
5. **Long-term**: The agent improves with every validated or corrected quote. It learns client preferences, product patterns, and team-specific workflows. Gradually moves from assisted to autonomous mode as confidence builds.

## Success Metrics

### User Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Quote generation speed** | < 2 minutes | Time from email arrival to draft quote in ERP |
| **Product matching accuracy** | > 95% | Correct product matched vs. commercial correction rate |
| **Complete quote accuracy** | > 95% | Draft quote sent without any commercial modification |

### Business Objectives

N/A — Product success is measured purely on agent performance. Business metrics will emerge naturally from delivering a fast, accurate solution.

### Key Performance Indicators

- **Primary KPI**: End-to-end processing time (email → ERP draft) < 2 minutes
- **Secondary KPI**: Product match accuracy rate > 95%
- **Secondary KPI**: Full quote accuracy rate (no correction needed) > 95%
- **Coverage rate**: To be defined once real-world usage data is available — intentionally deferred to avoid speculative targets

## MVP Scope

### Prototype Phase (Pre-MVP) — n8n

A low-code prototype using n8n to validate the end-to-end architecture and core flow before investing in the full Python implementation:
- Email reception and content extraction
- Product matching logic (hybrid search)
- Draft quote generation flow
- Validate the overall architecture and feature interactions on simple cases

**Goal**: Architectural validation and concept proof, not production readiness.

### Core Features (MVP — Python/LangGraph)

The MVP targets **simple quote requests** (clear client, obvious products) with all core capabilities active:

1. **Email processing**: Automated reception, cleaning, and structured extraction of quote requests
2. **Hybrid product search**: Vector + keyword search on raw product catalog — zero preprocessing required
3. **Proposability filter**: Exclude custom/obsolete/out-of-stock products before search
4. **Adaptive reasoning**: Request classification (simple/ambiguous/complex/out-of-scope) with appropriate reasoning pattern per category
5. **3-layer memory**: Industry knowledge (RAG), company context (catalog, rules), client-level (few-shot from validated quotes, profile/preferences)
6. **Confidence tiers**: High (>85%) → draft quote ready for review. Medium (50-85%) → multi-proposals. Low (<50%) → escalation with enriched context
7. **Self-review**: Agent validates its own output before submission
8. **ERP integration**: Odoo Community as open-source test ERP, populated with synthetic product catalog and client data
9. **Observability**: Structured logging, reasoning traces, decision traceability

### Out of Scope for MVP

- **Emergent knowledge graph** — deferred to post-MVP (requires data volume to be meaningful)
- **Full autonomy mode** — MVP requires commercial validation before sending
- **Multi-ERP support** — MVP uses Odoo only; abstraction layer designed but additional adapters deferred
- **SaaS deployment** — self-hosted only for MVP
- **Multi-language email support** — French first, other languages post-MVP
- **Attachment processing** (PDF, Excel) — text email body only for MVP
- **Interactive agent-commercial chat** — notifications only, no back-and-forth

### MVP Success Criteria

- Agent processes simple quote requests end-to-end in < 2 minutes
- Product matching accuracy > 95% on simple cases
- Complete quote accuracy > 95% (no commercial correction needed) on simple cases
- System works with a raw, uncleaned synthetic product catalog (validates zero-preprocessing promise)
- Successful integration with Odoo Community as test ERP

### Future Vision

- **v2.1**: Structured logging of every successful match — foundation for emergent graph
- **v2.2**: Pattern detection on accumulated data (batch process)
- **v2.3**: Emergent knowledge graph activated as agent context enrichment
- **v2.4**: Cross-client graph by industry (opt-in, anonymized)
- **Full autonomy**: Progressive removal of commercial validation as confidence builds
- **Multi-ERP**: SAP, Dynamics, Oracle adapters + RPA fallback for legacy systems
- **SaaS tier**: Hosted option for smaller companies
- **Advanced inputs**: PDF/Excel attachments, multi-language, multi-request emails
