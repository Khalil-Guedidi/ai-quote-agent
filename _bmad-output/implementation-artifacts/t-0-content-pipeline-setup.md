# Story T.0: Content Pipeline Setup

Status: done

## Story

As a **solo developer building in public**,
I want a content creation workflow set up (templates, guidelines, profiles),
So that I can produce posts efficiently with a consistent voice throughout the project.

## Acceptance Criteria

1. **AC-T.0.1:** LinkedIn bio updated to reflect AI + B2B industrial domain expertise
2. **AC-T.0.2:** Contra project created with project description and prototype overview
3. **AC-T.0.3:** Post template created in `_bmad-output/build-in-public/template.md`
4. **AC-T.0.4:** Content guidelines documented (tone, rules, structure)

## Tasks / Subtasks

- [x] Task 1: Create `_bmad-output/build-in-public/` directory structure (AC: 3, 4)
  - [x] 1.1 Create `_bmad-output/build-in-public/template.md` — reusable LinkedIn post template
  - [x] 1.2 Create `_bmad-output/build-in-public/guidelines.md` — content guidelines document
- [x] Task 2: Draft LinkedIn post template (AC: 3)
  - [x] 2.1 Template must include: hook, problem statement, solution/insight, metric/proof, open question/CTA
  - [x] 2.2 Target length: ~150–250 words per post
  - [x] 2.3 Include placeholders and structure markers for consistent formatting
- [x] Task 3: Document content guidelines (AC: 4)
  - [x] 3.1 Tone: technical but accessible, authentic, conversational — not corporate
  - [x] 3.2 Structure: problem → solution → metric → open question
  - [x] 3.3 Rules: English only, no past client names, no confidential info, synthetic data only
  - [x] 3.4 Frame professional experience as domain expertise (e.g., "After working on B2B industrial quoting systems professionally...")
  - [x] 3.5 Posting cadence: target 1 post/week, aligned to story milestones
  - [x] 3.6 Include series narrative arc: prototype → foundation → intelligence → full loop
- [x] Task 4: Draft LinkedIn bio text (AC: 1)
  - [x] 4.1 Bio emphasizes: AI engineering, B2B industrial domain, building in public
  - [x] 4.2 Mentions the ai-quote-agent project as a public case study
  - [x] 4.3 Save draft in `_bmad-output/build-in-public/linkedin-bio-draft.md`
- [x] Task 5: Draft Contra project page content (AC: 2)
  - [x] 5.1 Project title and description referencing the AI quoting agent
  - [x] 5.2 Include prototype overview: architecture (n8n + Odoo + Qdrant + LLM), metrics (96.2% Hit@5, 2.9s latency, 3/3 scenarios), GO decision
  - [x] 5.3 Save draft in `_bmad-output/build-in-public/contra-project-draft.md`

## Dev Notes

### Context

This is a **content/marketing story**, not a code story. The outputs are markdown files and text drafts — no application code, tests, or infrastructure changes. The dev agent creates the files in the repo; the user manually updates LinkedIn and Contra profiles using the generated drafts.

### Key Project Metrics for Content (from Epic 0 prototype)

These metrics are the foundation for all early content and should be referenced accurately:

- **Hybrid search accuracy:** 96.2% Hit@5 on 680-product synthetic catalog
- **End-to-end latency:** 2.9s average per quote request
- **Scenario coverage:** 3/3 test scenarios passed (simple, multi-line, ambiguous)
- **Stack:** n8n (orchestration) + Odoo 18 Community (ERP) + Qdrant (vector DB) + OpenAI embeddings + Claude (LLM extraction + matching)
- **Decision:** GO for production build (Python/LangGraph rewrite)

[Source: epics.md — Epic 0 stories, sprint-status.yaml — Epic 0 done]

### Epic T Guidelines (from epics.md)

- Language: **English**
- Tone: technical but accessible, authentic, problem → solution → metric → open question
- **Never** mention past clients by name or share confidential information
- All content based **exclusively** on this repo's code, synthetic data, and metrics
- Frame professional experience as domain expertise
- Exit criteria: consistent posting cadence, active LinkedIn profile, Contra portfolio showcasing the project

[Source: epics.md — Epic T header]

### Series Narrative Arc (T.0–T.15)

The content series follows the development milestones:

| Phase | Stories | Theme |
|-------|---------|-------|
| Launch | T.1 | Prototype results announcement |
| Foundation (Epic 1) | T.2–T.4 | Stack decisions, dirty data, infrastructure recap |
| Email Pipeline (Epic 2) | T.5–T.7 | French jargon, edge cases, first real email |
| Search (Epic 3) | T.8–T.10 | Hybrid search, LLM reranking, search recap |
| Intelligence (Epic 4) | T.11–T.13 | Confidence tiers, memory architecture, reasoning recap |
| Full Loop (Epic 5) | T.14–T.15 | Human-AI collaboration, final retrospective |

The template and guidelines must support this full arc — each post stands alone but builds on previous ones.

### Project Structure Notes

- All Build in Public content lives in `_bmad-output/build-in-public/`
- This directory does **not** exist yet — create it as part of this story
- Post drafts from subsequent stories (T.1–T.15) will also be archived here
- No conflicts with existing project structure

### File Outputs

| File | Purpose |
|------|---------|
| `_bmad-output/build-in-public/template.md` | Reusable LinkedIn post template with placeholders |
| `_bmad-output/build-in-public/guidelines.md` | Content tone, rules, structure, cadence |
| `_bmad-output/build-in-public/linkedin-bio-draft.md` | Draft text for LinkedIn profile bio |
| `_bmad-output/build-in-public/contra-project-draft.md` | Draft content for Contra project page |

### References

- [Source: epics.md — Epic T: Build in Public, Story T.0]
- [Source: sprint-status.yaml — Epic 0 done, prototype metrics available]
- [Source: architecture.md — Stack: Python/LangGraph for production, Odoo Community ERP]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — content story, no debugging required.

### Completion Notes List

- Created `_bmad-output/build-in-public/` directory structure
- Created `template.md` — reusable LinkedIn post template with 5-section structure (hook, problem, solution, metric, open question), formatting checklist, and series continuity note
- Created `guidelines.md` — comprehensive content guidelines covering tone/voice, structure, confidentiality rules, posting cadence (1/week), series narrative arc (T.0–T.15), hashtag strategy, and quality checklist
- Created `linkedin-bio-draft.md` — headline + about section emphasizing AI engineering, B2B industrial domain expertise, and the ai-quote-agent project with prototype metrics
- Created `contra-project-draft.md` — project title, description, architecture overview (n8n → Python/LangGraph), prototype metrics (96.2% Hit@5, 2.9s latency, 3/3 scenarios, GO decision), and technology stack
- All metrics sourced from Epic 0 prototype results; no confidential information included
- All content in English per Epic T guidelines

### File List

- `_bmad-output/build-in-public/template.md` (new)
- `_bmad-output/build-in-public/guidelines.md` (new)
- `_bmad-output/build-in-public/linkedin-bio-draft.md` (new)
- `_bmad-output/build-in-public/contra-project-draft.md` (new)
- `_bmad-output/implementation-artifacts/t-0-content-pipeline-setup.md` (modified — tasks marked complete, status → review)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — t-0 status updated)

### Change Log

- 2026-03-17: Story T.0 implemented — content pipeline setup with template, guidelines, LinkedIn bio draft, and Contra project draft
- 2026-03-17: Code review — moved unbuilt features (confidence routing, export compliance, memory) from "What Makes It Interesting" to new "Roadmap Highlights" section in contra-project-draft.md; fixed stale sprint-status comment
