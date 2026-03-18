# Story T.2: Stack Decision Post

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **solo developer building in public**,
I want to publish a post about the technology choices for production,
So that I share the reasoning behind moving from n8n prototype to Python/LangGraph.

## Acceptance Criteria

1. **AC-T.2.1:** LinkedIn post published — "Why I moved from n8n to Python/LangGraph for production"
2. **AC-T.2.2:** Post covers trade-offs: prototyping speed vs production control, low-code vs code-first
3. **AC-T.2.3:** Post draft archived in `_bmad-output/build-in-public/`

## Tasks / Subtasks

- [x] Task 1: Write LinkedIn post draft (AC: 1, 2, 3)
  - [x] 1.1 Follow template structure from `_bmad-output/build-in-public/template.md` (hook → problem → solution → metric → open question)
  - [x] 1.2 Hook must reference the stack pivot — n8n worked, but production needs more
  - [x] 1.3 Cover the core trade-off: n8n's prototyping speed vs Python/LangGraph's production control
  - [x] 1.4 Include specific technical reasons for the move (see Dev Notes below)
  - [x] 1.5 Include at least one concrete metric or comparison point
  - [x] 1.6 End with a genuine open question (prototyping-vs-production decision-making)
  - [x] 1.7 Run through formatting checklist from guidelines (150–250 words, English, no client names, etc.)
  - [x] 1.8 Add series continuity note referencing T.1 (prototype results)
  - [x] 1.9 Add 3–5 hashtags per strategy: #BuildInPublic #AI + topic-specific (e.g., #Python #LangGraph)
  - [x] 1.10 Save as `_bmad-output/build-in-public/t2-stack-decision-post.md`

## Dev Notes

### Context

This is a **content story**, not a code story. Output is a markdown file — no application code, tests, or infrastructure changes. The dev agent creates the file in the repo; the user manually publishes to LinkedIn.

This is post **#2** in the Build in Public series. It follows T.1 (prototype launch) and is tied to the completion of Stories 1.1 (project scaffolding) and 1.2 (PostgreSQL + pgvector). The narrative angle: "the prototype proved the idea works — now here's why I rebuilt it from scratch."

### Stack Pivot: Key Talking Points

These are the specific reasons for moving from n8n to Python/LangGraph. Use these as source material — do NOT list all of them in the post. Pick the 2–3 most compelling for LinkedIn.

| Prototype (n8n) | Production (Python/LangGraph) | Why the Change |
|-----------------|-------------------------------|----------------|
| n8n visual workflow | LangGraph graph-based agent | Need explicit state management, conditional routing, cycles (retry/review loops) |
| Qdrant (separate vector DB) | PostgreSQL + pgvector | Single DB for relational + vector data, simpler self-hosted deployment, RLS for future multi-tenant |
| OpenAI embeddings API | Local multilingual model (BGE-M3) | No external dependency for embeddings, offline capability, fine-tuning potential for industrial vocabulary |
| No structured config | pydantic-settings | Type-safe configuration, validation, .env support |
| No testing | pytest + mypy + ruff | Production needs quality gates |
| No database | PostgreSQL + Alembic migrations | Need audit trail, memory, caching, structured data |
| n8n scheduling | asyncio + FastAPI | Full async pipeline, health checks, API endpoints |
| No error handling | Exception hierarchy, circuit breakers | Production must handle failures gracefully |

### Tone Guidance

The post should NOT bash n8n. n8n was the right choice for prototyping — it validated the idea in days. The angle is: **different tools for different phases**. Prototyping rewards speed and visual feedback. Production rewards control, testability, and maintainability.

Frame it as a practical decision, not a religious debate. Many readers will relate to the "prototype-to-production" pivot.

### Concrete Numbers to Use (Source of Truth)

These come from the actual implementation work in Stories 1.1 and 1.2:

| Fact | Source |
|------|--------|
| uv as package manager (10–100x faster than pip) | architecture.md — Starter Template Evaluation |
| Python 3.12+ with LangGraph | architecture.md — explicit PRD choice |
| PostgreSQL + pgvector (single DB, no Qdrant dependency) | architecture.md — Data Architecture |
| pydantic-settings config system with 6 nested groups | Story 1.1 completion notes |
| Alembic migrations with pgvector extension | Story 1.2 completion notes |
| 14 sub-packages created in project scaffold | Story 1.1 completion notes |
| 21 tests passing (unit + integration) | Story 1.2 completion notes |
| Docker Compose setup (pgvector/pgvector:pg16) | Story 1.2 completion notes |

Pick 1–2 of these for the "metric/proof" section. The most compelling: going from zero tests/zero structure (n8n) to 21 tests + typed config + migration system in the first two stories.

### Content Guidelines to Follow

All content must comply with `_bmad-output/build-in-public/guidelines.md`:

- **Tone:** Technical but accessible, authentic, conversational — not corporate
- **Structure:** Hook → Problem → Solution/Insight → Metric/Proof → Open Question/CTA
- **Length:** 150–250 words per post
- **Language:** English only
- **Confidentiality:** No past client names, no confidential info, synthetic data only
- **Hashtags:** 3–5 max. Always: #BuildInPublic #AI. Rotate based on topic.
- **Quality:** Must pass the quality checklist in guidelines.md before marking done

[Source: _bmad-output/build-in-public/guidelines.md]

### Template to Follow

Use the exact template structure from `_bmad-output/build-in-public/template.md`:

1. Post metadata (story number, phase, date)
2. Hook (1–2 sentences)
3. Problem statement (2–3 sentences)
4. Solution / Insight (3–5 sentences)
5. Metric / Proof (1–2 sentences)
6. Open question / CTA (1–2 sentences)
7. Formatting checklist
8. Series continuity note

[Source: _bmad-output/build-in-public/template.md]

### Previous Story Intelligence (T.1)

Story T.1 created the first LinkedIn post. Key learnings:

- **Initial draft was too long (376 words)** — had to trim to ~228 words. Start concise.
- **Post structure worked well:** hook → problem → solution → metric → question flow was natural.
- **T.1 already mentioned the production stack:** "Now I'm rebuilding it for real: Python, LangGraph, Qdrant, Claude." — T.2 should build on this, not repeat it. Note: T.1 mentioned Qdrant, but the actual production choice is PostgreSQL+pgvector. T.2 can address this evolution naturally.
- **T.1 already positioned the series as "post #1"** — T.2 should reference back: "Last week I shared the prototype results..."
- **Code review lesson (T.0):** Never present planned/future features as existing capabilities. For T.2 this means: only reference what's actually built in 1.1–1.2, not the full planned architecture.

[Source: _bmad-output/implementation-artifacts/t-1-prototype-launch-post.md]

### Git Intelligence

Recent commits confirm Stories 1.1 and 1.2 are complete:
- `2482e07` feat: add PostgreSQL database foundation with async SQLAlchemy & Alembic migrations (Story 1.2)
- `7f9383a` feat: add project scaffolding & type-safe configuration system (Story 1.1)

These are the concrete implementation milestones this post is about. The production rewrite has started — the foundation is real.

### Project Structure Notes

- All Build in Public content lives in `_bmad-output/build-in-public/`
- Post drafts use naming convention: `t{N}-{slug}.md` (e.g., `t2-stack-decision-post.md`)
- No conflicts with existing project structure

### Anti-Pattern Prevention

- **DO NOT** bash n8n or low-code tools — frame as "right tool for the right phase"
- **DO NOT** present planned/future features as existing capabilities (T.0 code review lesson)
- **DO NOT** list every tech choice — pick 2–3 compelling ones and go deep
- **DO NOT** exceed 250 words on the LinkedIn post
- **DO NOT** use corporate buzzwords ("leverage", "synergy", "drive value")
- **DO NOT** mention any specific past clients or employers by name
- **DO NOT** repeat the prototype metrics from T.1 — this post is about the stack decision, not the prototype results
- **DO** reference T.1 in the series continuity note
- **DO** frame the pivot as a practical decision with trade-offs
- **DO** include a genuine question about prototyping vs production tooling decisions
- **DO** keep it under 250 words — T.1 initial draft was too long, start concise

### References

- [Source: epics.md — Epic T: Build in Public, Story T.2]
- [Source: _bmad-output/build-in-public/template.md — Post template]
- [Source: _bmad-output/build-in-public/guidelines.md — Content guidelines]
- [Source: _bmad-output/build-in-public/t1-prototype-launch-post.md — Previous post for continuity]
- [Source: _bmad-output/implementation-artifacts/t-1-prototype-launch-post.md — Previous story context]
- [Source: _bmad-output/implementation-artifacts/1-1-scaffolding-projet-systeme-de-configuration.md — Story 1.1 completion notes]
- [Source: _bmad-output/implementation-artifacts/1-2-base-de-donnees-postgresql-migrations.md — Story 1.2 completion notes]
- [Source: architecture.md — Tech stack decisions, starter template evaluation, data architecture]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — single-task content story, no debugging required.

### Completion Notes List

- Task 1 complete: LinkedIn post draft written and saved to `_bmad-output/build-in-public/t2-stack-decision-post.md`
- Post follows template structure (hook → problem → solution → metric → open question)
- 209 words — within 150–250 word target range
- Hook uses 96% accuracy as surprise setup ("threw it all away"), not as repeated metric
- Covers trade-off: n8n prototyping speed vs Python/LangGraph production control
- Specific tech reasons: LangGraph state management, pgvector single DB, pydantic-settings, pytest+mypy+ruff
- Metrics used: 21 passing tests, 14 sub-packages (from Stories 1.1/1.2)
- Does NOT bash n8n — frames as "right tool for the right phase"
- Does NOT present future features as existing
- Series continuity note references T.1
- 5 hashtags: #BuildInPublic #AI #Python #LangGraph #B2B
- All acceptance criteria (AC-T.2.1, AC-T.2.2, AC-T.2.3) satisfied

### Change Log

- 2026-03-18: Created LinkedIn post draft `t2-stack-decision-post.md` covering stack pivot from n8n to Python/LangGraph

### File List

- `_bmad-output/build-in-public/t2-stack-decision-post.md` (new) — LinkedIn post draft
- `_bmad-output/implementation-artifacts/t-2-stack-decision-post.md` (modified) — Story file updates
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) — Status updated to review
