# Story T.12: Memory Architecture Post

Status: done

## Story

As a **solo developer building in public**,
I want to publish a post about the 3-layer memory architecture,
so that I share the design for industry/company/client memory and how it improves over time.

## Acceptance Criteria

1. **AC-T.12.1:** LinkedIn post published — "An AI that remembers: 3-layer memory for B2B quoting"
2. **AC-T.12.2:** Post covers industry knowledge, company context, and client preferences
3. **AC-T.12.3:** Post draft archived in `_bmad-output/build-in-public/t12-memory-architecture-post.md`

## Tasks / Subtasks

- [x] Task 1: Draft LinkedIn post (AC: #1, #2)
  - [x] Write hook about AI systems that forget everything between requests
  - [x] Explain the 3-layer memory architecture with concrete industrial examples (industry: steel standards like NF EN 10088, company: internal product naming and business rules, client: "like last time" resolution from order history)
  - [x] Include real metrics from Epic 4 completion (599 tests, 11/11 stories, 0 regressions) and concrete data infrastructure details from Stories 4.6/4.7 (ERP reads + draft creation enabling the feedback loop)
  - [x] End with a genuine non-technical question for the audience
  - [x] Verify 150-250 words, 3-5 hashtags, no em dashes
- [x] Task 2: Format and archive post draft (AC: #3)
  - [x] Create `_bmad-output/build-in-public/t12-memory-architecture-post.md` using template from `_bmad-output/build-in-public/template.md`
  - [x] Fill metadata, formatting checklist, and series continuity note
- [x] Task 3: Quality review against guidelines
  - [x] Run quality checklist from `_bmad-output/build-in-public/guidelines.md`
  - [x] Verify tone rules (no em dashes, no "it's X not Y", tech vulgarized, non-technical question)
  - [x] Verify series continuity with T.11 and position within Intelligence phase (Epic 4)

## Dev Notes

### CRITICAL: This Is a Design/Vision Post, Not a Code Implementation Post

T.12 is positioned **after Stories 4.6–4.7** (ERP reads + draft creation). The memory system (Epic 6) is not yet built. The post angle is: **the data infrastructure is now in place, and here's the design for the 3-layer memory that will sit on top of it**. Frame as forward-looking architecture, grounded in concrete data flows already working.

Do NOT frame this as "I built a memory system." Frame as "I designed a memory architecture, and the plumbing is already in place."

### The 3-Layer Memory Architecture — The Post's Core Angle

The system's long-term differentiator is a 3-layer memory that deepens with every interaction:

**Layer 1 — Industry Knowledge (RAG):**
- Shared knowledge base of industry conventions, standards, and defaults
- Example: NF EN 10088 stainless steel standards, standard terminology (DN, PN, Ø, lg)
- Stored in PostgreSQL with vector embeddings for RAG retrieval
- Provides baseline reasoning for new clients or unfamiliar product families
- Planned implementation: Epic 6, Story 6.1

**Layer 2 — Company Context:**
- Catalog structure, business rules, internal workflows, preferred suppliers
- Standard product lines and internal naming conventions
- Applied as constraints during reasoning (e.g., "always propose standard variant unless client specifies otherwise")
- Updates without system restart when business rules change
- Planned implementation: Epic 6, Story 6.2

**Layer 3 — Client Memory (Few-Shot):**
- Past quotes, preferences, purchase habits for individual clients
- Enables personalization ("like last time", "same as last month")
- Recent quotes retrieved as few-shot context for the LLM
- Influences both product matching and confidence scoring
- For new clients: falls back to company and industry context
- Planned implementation: Epic 6, Story 6.3

**Key insight for the post:** The 3 layers create a knowledge funnel — industry (broad) → company (specific) → client (personal). A new client benefits from all 3 layers from day 1, even without personal history.

### How Stories 4.6 and 4.7 Enable the Memory Architecture

These two stories created the **data infrastructure** that the memory system will build on:

**Story 4.6 (ERP Reading):**
- `get_client()` reads client data from Odoo (name, contact info, customer rank)
- `get_client_orders()` retrieves recent order history with line details
- `get_product_by_id()` reads product details for enrichment
- This is the **input pipe** for client memory: the system can now read what the client has ordered before

**Story 4.7 (Draft Quote Creation):**
- `create_draft_quote()` writes UniversalQuote to Odoo as draft sales.order
- This is the **output pipe** that creates the feedback loop entry point
- When a sales rep corrects a draft in Odoo, Epic 6's feedback service (Story 6.4) will capture those corrections and feed them back into client memory

**The bidirectional flow: ERP → Agent → ERP → Human → Agent learns.**

This is the core angle: the plumbing for a learning system is already in place. The memory layer (Epic 6) will sit on top of it.

### The Feedback Loop — What Makes Memory Useful

From the architecture (Epic 6, Stories 6.4–6.6):
- **Story 6.4:** Feedback service passively captures corrections when sales rep modifies a draft
- **Story 6.5:** Validated quotes (accepted without changes) become few-shot examples for similar future requests
- **Story 6.6:** Cold start calibration: ingest historical quotes during onboarding so the agent starts with existing knowledge on day 1

**For the post:** Don't explain all 6 stories. Simplify to: "the agent writes a draft → the human corrects it → the agent learns from the correction → next time it gets closer."

### What to Vulgarize for the Post

| Technical reality | Post language |
|------------------|---------------|
| 3-layer RAG/context/few-shot memory architecture | "3 types of memory" or "3 layers of knowledge" |
| pgvector embeddings for industry knowledge | "the AI stores industry knowledge and retrieves it when needed" |
| Business rules as configurable constraints | "company-specific rules that the AI follows" |
| Few-shot learning from client order history | "the AI remembers what each client ordered before" |
| Feedback loop via Odoo correction capture | "when the sales rep corrects a draft, the AI learns from that correction" |
| UniversalQuote DTO written to Odoo | "the AI creates a draft quote in the ERP" |
| `get_client_orders()` with retry/backoff | "the AI reads client order history" |
| Cold start calibration from historical data | "on day 1, it can learn from past quotes" |

### Concrete Examples to Use in the Post

- **Industry layer:** "The AI knows that DN25 means 25mm nominal diameter for pipes, and that 304L is a stainless steel grade. It knows this for every client, because it's industry-wide knowledge."
- **Company layer:** "If the company always proposes galvanized over raw steel for outdoor use, that rule is applied automatically."
- **Client layer:** "Client X always orders 304L instead of 316L when the email says 'inox'. After a few corrections, the AI stops suggesting 316L for that client."
- **Feedback loop:** "Sophie corrects the draft: wrong thickness. Next time Client X asks for 'plaques acier', the AI remembers the correction and proposes the right thickness."

### Metrics to Include

| Metric | Value | Source |
|--------|-------|--------|
| Total tests after Epic 4 | 599 passing | Epic 4 retro |
| Stories completed in Epic 4 | 11/11 (100%) | Epic 4 retro |
| Regressions | 0 | Epic 4 retro |
| CLI commands available | 9 | Epic 4 retro (search, classify, reason, score, review, compliance, erp-read, draft-create, process) |
| ERP read retry | 3 retries, exponential backoff | Story 4.6 |
| New tests in 4.6 + 4.7 | 61 (32 + 29) | Story completion notes |

**Choose 1-2 metrics max for the post.** The memory architecture is the story, not test counts. Use metrics to ground credibility, not to fill space.

### Tone & Voice Rules (CRITICAL)

From `_bmad-output/build-in-public/guidelines.md` and feedback memory:

1. **NO em dashes** (use commas, periods, or parentheses instead)
2. **NO "it's X, not Y" constructions**
3. **Vulgarize tech**: say "3 layers of knowledge" not "3-layer RAG/context/few-shot memory architecture with pgvector embeddings"
4. **First person, conversational**, like explaining over coffee
5. **Authentic, not corporate**: no "leverage," "synergies," "drive value"
6. **Short sentences** preferred
7. **Problem-first approach**: lead with the challenge (AI that forgets/treats every request as new), not the solution
8. **Non-technical final question**: target audience includes B2B decision-makers and managers

### Post Structure (Non-Negotiable from guidelines.md)

1. **Hook** (1-2 sentences): Surprising insight or question about AI and memory
2. **Problem** (2-3 sentences): Real B2B industrial challenge (every request treated as new, no learning, no context)
3. **Solution/Insight** (3-5 sentences): The 3-layer design with concrete examples
4. **Metric/Proof** (1-2 sentences): Concrete number(s) grounding the architecture
5. **Open Question/CTA** (1-2 sentences): Genuine question, not a sales pitch
6. **Hashtags**: 3-5 max. Core: #BuildInPublic #AI. Rotate topic-specific.

### Series Continuity

- **Previous post (T.11):** Confidence tiers. Hook: "Most AI demos show you the perfect answer. Nobody talks about what happens when the AI isn't sure." 3-tier routing system with concrete examples. Ended with: "When you use an AI tool at work, do you trust it more when it gives you a clear answer, or when it tells you it's not sure?" (~213 words)
- **Narrative arc**: T.11 showed how the agent handles uncertainty. T.12 goes deeper: the agent now reads and writes to the ERP, and the design for a learning memory system is in place. The transition: "the agent knows when it's sure. Now it needs to remember what worked before."
- **Next post (T.13):** Intelligence recap (after Epic 4). T.12 should naturally lead into a recap of the full Intelligence phase.
- All previous posts range 207-228 words. Target ~210-220 words.

### What NOT to Do

- Do NOT frame as "I built a memory system" (Epic 6 is not yet built)
- Do NOT repeat T.11's angle (confidence tiers already covered)
- Do NOT get into LangGraph, Pydantic, or pgvector internals. The audience doesn't care about the framework.
- Do NOT frame as a tutorial ("here's how to build a memory layer")
- Do NOT mention past clients by name or share confidential information
- Do NOT use data from outside this repo (synthetic data and benchmarks only)
- Do NOT oversell. Be honest that this is architecture design, not production yet.
- Do NOT use em dashes, "it's X, not Y" constructions, or corporate buzzwords
- Do NOT make the question at the end too technical. Ask something a manager or business owner would relate to.

### Previous Posts Word Counts (for calibration)

| Post | Words |
|------|-------|
| T.1 | ~228 |
| T.2 | ~207 |
| T.3 | ~208 |
| T.4 | ~213 |
| T.5 | ~210 |
| T.6 | ~207 |
| T.7 | ~210 |
| T.8 | ~210 |
| T.9 | ~212 |
| T.10 | ~228 |
| T.11 | ~213 |

### File Output Locations

- Post draft: `_bmad-output/build-in-public/t12-memory-architecture-post.md`
- Use template from: `_bmad-output/build-in-public/template.md`

### Project Structure Notes

- Build-in-public drafts go in `_bmad-output/build-in-public/`
- This is a content story, not a code story. No source code changes required.
- The story file itself lives in `_bmad-output/implementation-artifacts/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story T.12] — AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 6] — Memory, Learning & Feedback Loop (Stories 6.1–6.6)
- [Source: _bmad-output/planning-artifacts/prd.md#FR17-FR23] — Functional requirements for memory system
- [Source: _bmad-output/planning-artifacts/architecture.md] — Memory layer architecture (memory/industry.py, memory/company.py, memory/client.py)
- [Source: _bmad-output/build-in-public/guidelines.md] — Tone, structure, quality checklist
- [Source: _bmad-output/build-in-public/template.md] — Post draft template
- [Source: _bmad-output/build-in-public/t11-confidence-tiers-post.md] — Previous post (series continuity)
- [Source: _bmad-output/implementation-artifacts/4-6-lecture-donnees-erp-catalogue-client.md] — Story 4.6 (ERP reads, 32 tests)
- [Source: _bmad-output/implementation-artifacts/4-7-creation-de-brouillon-devis-dans-erp.md] — Story 4.7 (draft creation, 29 tests)
- [Source: _bmad-output/implementation-artifacts/4-8-orchestration-agent-langgraph-pipeline-complet.md] — Story 4.8 (full pipeline orchestration)
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-22.md] — Epic 4 retro (599 tests, 11/11 stories, 0 regressions)
- [Source: _bmad-output/implementation-artifacts/t-11-confidence-tiers-post.md] — Previous story (learnings, patterns, word count)
- [Source: docs/project-context.md] — Project patterns and conventions
- [Source: ~/.claude/projects/.../memory/feedback_build_in_public_tone.md] — Tone feedback rules

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — content story, no code debugging required.

### Completion Notes List

- Drafted LinkedIn post (205 words) covering 3-layer memory architecture: industry knowledge, company context, client memory
- Used forward-looking framing ("I designed" not "I built") per Dev Notes guidance — Epic 6 not yet implemented
- Included concrete examples: DN25 (industry), galvanized rule (company), "inox" → 304L (client), Sophie correction (feedback loop)
- Metrics: 599 tests, zero regressions from Epic 4
- Mentioned ERP read/write data plumbing from Stories 4.6/4.7
- Non-technical closing question targeting B2B managers
- All tone rules verified: no em dashes, no "it's X not Y", tech vulgarized, conversational
- Series continuity: transitions from T.11 (confidence/uncertainty) to T.12 (memory/learning), positions for T.13 (Epic 4 recap)

### Change Log

- 2026-03-22: Created post draft `_bmad-output/build-in-public/t12-memory-architecture-post.md` — all tasks completed
- 2026-03-22: Code review — fixed #RAG hashtag (vulgarization rule violation, replaced with #Automation) and "plumbing/pipes" redundancy (replaced "the pipes are connected" with "the data flows are connected"). Status → done

### File List

- `_bmad-output/build-in-public/t12-memory-architecture-post.md` (new) — LinkedIn post draft
- `_bmad-output/implementation-artifacts/t-12-memory-architecture-post.md` (modified) — Story file updated
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) — Status updated
