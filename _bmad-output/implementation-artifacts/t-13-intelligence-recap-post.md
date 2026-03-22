# Story T.13: Intelligence Recap Post

Status: done

## Story

As a **solo developer building in public**,
I want to publish a milestone recap of the adaptive reasoning phase,
so that I mark the transition from "matcher" to "reasoning agent."

## Acceptance Criteria

1. **AC-T.13.1:** LinkedIn post published — "From pattern matching to reasoning: how the agent got smarter"
2. **AC-T.13.2:** Contra project updated with intelligence layer architecture and metrics
3. **AC-T.13.3:** Post draft archived in `_bmad-output/build-in-public/t13-intelligence-recap-post.md`

## Tasks / Subtasks

- [x] Task 1: Draft LinkedIn post (AC: #1)
  - [x] Write hook about the transition from finding products to reasoning about them
  - [x] Recap Epic 4 journey: 11 stories, 3 foundation + 8 core, the full pipeline from classify to draft
  - [x] Highlight the key insight: the agent has 7 nodes, each with a fail-safe default (escalation, never approval)
  - [x] Include real metrics from Epic 4 retrospective (599 tests, 243 new, 0 regressions, 9 CLI commands)
  - [x] Mention the jargon dictionary removal as a data-driven decision (built it, benchmarked it, deleted it)
  - [x] End with a genuine non-technical question for B2B decision-makers
  - [x] Verify 150-250 words, 3-5 hashtags, no em dashes, no "it's X, not Y"
- [x] Task 2: Update Contra project (AC: #2)
  - [x] Add intelligence layer section to Contra project page
  - [x] Include pipeline architecture summary and key metrics
- [x] Task 3: Format and archive post draft (AC: #3)
  - [x] Create `_bmad-output/build-in-public/t13-intelligence-recap-post.md` using template from `_bmad-output/build-in-public/template.md`
  - [x] Fill metadata, formatting checklist, and series continuity note
- [x] Task 4: Quality review against guidelines
  - [x] Run quality checklist from `_bmad-output/build-in-public/guidelines.md`
  - [x] Verify tone rules (no em dashes, no "it's X not Y", vulgarize tech, non-technical question)
  - [x] Verify series continuity with T.11 and position as Intelligence phase closer

## Dev Notes

### CRITICAL: This Is the Intelligence Phase Closer (Epic 4 Recap)

T.11 opened the Intelligence phase with confidence tiers. T.13 closes the entire Epic 4. The core angle: the system went from "finding the right product" (Epic 3) to "deciding what to do about it" (Epic 4). The pipeline now reasons, scores, reviews itself, checks compliance, and creates draft quotes.

Note: T.12 (Memory Architecture Post) is still backlog and depends on Epic 6 stories. T.13 does NOT depend on T.12. T.13 recaps all of Epic 4 regardless.

### What Epic 4 Built — The Post's Core Material

Epic 4 delivered 11 stories (3 foundation, 8 core) with 243 new tests (599 total), 0 regressions.

**Foundation stories (4.0a-c) — 3 debts resolved before building:**
1. **CI/CD fixed** (4.0a) — broken since Epic 1, fixed after being flagged in 3 consecutive retrospectives. ML deps separated, 363 tests run in CI.
2. **CLI search command** (4.0b) — `uv run quote-agent search "tubes inox"`. Project Lead can now see the system work. Born from Epic 3 retro lesson.
3. **Jargon dictionary removed** (4.0c) — benchmark: 96% with dictionary, 96% without. Delta = 0. BGE-M3 handles industrial jargon natively. Dictionary deleted, zero-preprocessing vision restored.

**Core pipeline — 7 agent nodes orchestrated by LangGraph (Stories 4.1-4.8):**

| Node | Story | What it does | Fail-safe default |
|------|-------|-------------|-------------------|
| Classification | 4.1 | Categorizes request: simple/ambiguous/complex/out-of-scope | Fallback to "complex" |
| Confidence Scoring | 4.2 | Scores match quality: high >85%, medium 50-85%, low <50% | Fallback to tier="low" (escalation) |
| Adaptive Reasoning | 4.3 | Applies strategy based on complexity (direct/exploration/deep) | Falls back to deep analysis |
| Self-Review | 4.4 | Validates output: anti-hallucination, quantity plausibility, coherence | Fallback to approved=False (rejection) |
| Compliance | 4.5 | Export control + sanctioned entity detection | Fallback to is_compliant=False (block) |
| ERP Read | 4.6 | Reads product catalog + client order history from Odoo | Retry with exponential backoff |
| Draft Creation | 4.7 | Creates draft quote in Odoo (draft-only, never sent) | Buffer locally + retry |
| Orchestration | 4.8 | LangGraph pipeline wiring all nodes end-to-end | Error → escalation route |

**Key design principle: Fail-safe by default.** Every node, on error, triggers escalation or rejection. No node ever approves by default. The AI scores, simple rules route, humans validate.

### What to Vulgarize for the Post

| Technical reality | Post language |
|------------------|---------------|
| 7 LangGraph nodes with TypedDict state | "a 7-step pipeline" |
| Fail-safe defaults on all nodes | "if something goes wrong, it asks a human" |
| LLM structured output with Pydantic | "the AI follows a checklist before submitting" |
| asyncio pipeline with gpt-4o-mini | "a fast AI model processes each step" |
| 599 pytest tests, 0 regressions | "599 tests, zero broken" |
| 3 foundation stories from retro | "I fixed 3 debts before building anything new" |
| Jargon dictionary removed after benchmark | "I built a feature, measured it, and deleted it" (callback to T.10) |
| Export control + sanctions detection | "the agent checks compliance before generating a quote" |
| 9 CLI commands | "every step visible from the command line" |

### Concrete Examples for the Post

From Epic 4 stories and retrospective:
- **The pipeline**: email arrives → agent classifies complexity → searches products → scores confidence → reviews its own work → checks compliance → creates draft quote in ERP
- **Fail-safe in action**: if the AI can't classify, it assumes "complex" (more attention). If it can't score confidence, it assumes "low" (human handles it). If self-review fails, it rejects the draft. Zero silent failures.
- **Data-driven deletion**: jargon dictionary scored 96% with, 96% without. Built it, measured it, deleted it. (This callbacks to T.10's hook and reinforces the "data over instinct" narrative)
- **CI/CD resurrection**: broken since Epic 1, flagged 3 times, finally fixed. 363 tests now run automatically on every push.

### Metrics to Include

| Metric | Value | Source |
|--------|-------|--------|
| Stories completed | 11/11 (100%) | Epic 4 retrospective |
| Tests added | 243 new (363 → 599) | Epic 4 retrospective |
| Regressions | 0 | Epic 4 retrospective |
| Agent nodes | 7 | Stories 4.1-4.8 |
| CLI commands | 9 | Epic 4 retrospective |
| Confidence tiers | 3 (>85%, 50-85%, <50%) | Story 4.2 |
| Jargon benchmark delta | 0% (96% with, 96% without) | Story 4.0c |
| Test growth total | 68 → 188 → 363 → 599 | All retrospectives |

### Tone & Voice Rules (CRITICAL)

From `_bmad-output/build-in-public/guidelines.md` and feedback memory:

1. **NO em dashes** (use commas, periods, or parentheses instead)
2. **NO "it's X, not Y" constructions**
3. **Vulgarize tech**: say "7-step pipeline" not "LangGraph StateGraph with TypedDict". Say "the AI reviews its own work" not "self-review node with anti-hallucination validation via structured output"
4. **First person, conversational**, like explaining over coffee
5. **Authentic, not corporate**: no "leverage," "synergies," "drive value"
6. **Short sentences** preferred
7. **Problem-first approach**: lead with what changed (the system went from finding to deciding), not the tech
8. **Non-technical final question**: target audience includes B2B decision-makers and managers

### Post Structure (Non-Negotiable from guidelines.md)

1. **Hook** (1-2 sentences): Surprising result, counterintuitive finding, or question
2. **Problem** (2-3 sentences): Real B2B industrial challenge
3. **Solution/Insight** (3-5 sentences): What you built, technical but accessible
4. **Metric/Proof** (1-2 sentences): Concrete number(s)
5. **Open Question/CTA** (1-2 sentences): Genuine question, not a sales pitch
6. **Hashtags**: 3-5 max. Core: #BuildInPublic #AI. Rotate topic-specific.

### Series Continuity

- **Previous post (T.11):** Confidence tiers. Hook: "Most AI demos show you the perfect answer. Nobody talks about what happens when the AI isn't sure." Detailed the 3-tier routing (high/medium/low). Ended with: "When you use an AI tool at work, do you trust it more when it gives you a clear answer, or when it tells you it's not sure?" (213 words)
- **T.10 callback opportunity**: T.10 used "I built a feature, benchmarked it, and deleted it" for the jargon dictionary. T.13 can callback to this theme (data-driven deletion recurs in Epic 4 with the same jargon dictionary story 4.0c).
- **Narrative arc**: T.11 showed one capability (confidence tiers). T.13 zooms out to show the full picture: the system now has a complete reasoning pipeline with 7 nodes. The transition: "finding the right product was step one. Deciding what to do about it is step two."
- **Next post (T.14):** Human-AI collaboration (after Epic 5 stories 5.2-5.3). T.13 should hint that the pipeline creates drafts, but a human still validates. The next step is making that human loop seamless with notifications.
- All previous posts range 207-228 words. Target ~210-220 words.

### What NOT to Do

- Do NOT repeat T.11's confidence tiers angle in detail (already covered)
- Do NOT repeat T.10's jargon dictionary story as the main hook (already used, but can callback briefly)
- Do NOT frame as a tutorial ("here's how to build a reasoning agent")
- Do NOT get into LangGraph, Pydantic, asyncio, or framework details. The audience doesn't care.
- Do NOT mention past clients by name or share confidential information
- Do NOT use data from outside this repo (synthetic data and benchmarks only)
- Do NOT oversell. Be honest that this is synthetic data, not production yet.
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

- Post draft: `_bmad-output/build-in-public/t13-intelligence-recap-post.md`
- Contra update: inline in Contra project page
- Use template from: `_bmad-output/build-in-public/template.md`

### Project Structure Notes

- Build-in-public drafts go in `_bmad-output/build-in-public/`
- This is a content story, not a code story. No source code changes required.
- The story file itself lives in `_bmad-output/implementation-artifacts/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story T.13] — AC and story definition
- [Source: _bmad-output/implementation-artifacts/epic-4-retro-2026-03-22.md] — Epic 4 retrospective (delivery metrics, lessons, action items)
- [Source: _bmad-output/build-in-public/guidelines.md] — Tone, structure, quality checklist
- [Source: _bmad-output/build-in-public/template.md] — Post draft template
- [Source: _bmad-output/build-in-public/t11-confidence-tiers-post.md] — Previous Intelligence phase post (series continuity)
- [Source: _bmad-output/build-in-public/t10-search-recap-post.md] — Search phase closer (callback opportunity)
- [Source: _bmad-output/implementation-artifacts/t-11-confidence-tiers-post.md] — Previous story file (patterns, learnings)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] — Full Epic 4 stories and acceptance criteria
- [Source: docs/project-context.md] — Project patterns and conventions
- [Source: .claude/projects/-home-khalil-PycharmProjects-ai-quote-agent/memory/feedback_build_in_public_tone.md] — Tone feedback rules

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — content story, no code changes.

### Completion Notes List

- ✅ Task 1: LinkedIn post drafted (229 words). Hook: transition from finding to deciding. Includes 7-step pipeline description, fail-safe principle, jargon dictionary callback (T.10), metrics from Epic 4 retro (599 tests, 243 new, 0 regressions, 9 CLI, 11 stories). Non-technical closing question targeting B2B decision-makers.
- ✅ Task 2: Contra project update section included in archive file with pipeline architecture, quality metrics, safety posture, CLI commands, data-driven decisions, and compliance.
- ✅ Task 3: Archive file created at `_bmad-output/build-in-public/t13-intelligence-recap-post.md` using template structure (metadata, post, formatting checklist, series continuity, Contra update).
- ✅ Task 4: Quality review passed. No em dashes in post body, no "it's X, not Y", tech vulgarized, non-technical question, 229 words (target 150-250), 5 hashtags, series continuity verified (T.11 opener → T.13 closer, T.10 callback, T.14 hint).

### Change Log

- 2026-03-22: Story T.13 implemented — LinkedIn post drafted, Contra update prepared, archive created, quality review passed.
- 2026-03-22: Code review — 1 MEDIUM fixed (closing question overlapped T.11), 1 LOW fixed ("finding is not deciding" rephrased). Status → done.

### File List

- `_bmad-output/build-in-public/t13-intelligence-recap-post.md` (NEW) — Post draft with metadata, checklist, continuity note, and Contra update
- `_bmad-output/implementation-artifacts/t-13-intelligence-recap-post.md` (NEW) — Story file: tasks checked, Dev Agent Record filled, status → done
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED) — t-13 status: ready-for-dev → review
