# Story T.11: Confidence Tiers Post

Status: review

## Story

As a **solo developer building in public**,
I want to publish a post about the confidence-based routing system,
so that I show how the agent handles uncertainty instead of guessing.

## Acceptance Criteria

1. **AC-T.11.1:** LinkedIn post published — "When your AI isn't sure: 3 levels of certainty in quote generation"
2. **AC-T.11.2:** Post explains high/medium/low confidence routing with concrete examples
3. **AC-T.11.3:** Post draft archived in `_bmad-output/build-in-public/t11-confidence-tiers-post.md`

## Tasks / Subtasks

- [x] Task 1: Draft LinkedIn post (AC: #1, #2)
  - [x] Write hook about AI systems that guess vs. admit uncertainty
  - [x] Explain the 3-tier routing system with concrete industrial examples (high: exact match on a steel plate reference, medium: "something like inox tubing" with 3 proposals, low: vague request escalated to human)
  - [x] Include real metrics from Stories 4.1 and 4.2 (414 tests, thresholds: >85% high, 50-85% medium, <50% low)
  - [x] End with a genuine non-technical question for the audience
  - [x] Verify 150-250 words, 3-5 hashtags, no em dashes
- [x] Task 2: Format and archive post draft (AC: #3)
  - [x] Create `_bmad-output/build-in-public/t11-confidence-tiers-post.md` using template from `_bmad-output/build-in-public/template.md`
  - [x] Fill metadata, formatting checklist, and series continuity note
- [x] Task 3: Quality review against guidelines
  - [x] Run quality checklist from `_bmad-output/build-in-public/guidelines.md`
  - [x] Verify tone rules (no em dashes, no corporate buzzwords, vulgarize tech, non-technical question)
  - [x] Verify series continuity with T.10 and position within Intelligence phase (Epic 4)

## Dev Notes

### CRITICAL: This Is an Intelligence Phase Post, Not a Search Post

T.10 closed the Search phase. T.11 opens the **Intelligence phase** (Epic 4). The core angle is: the agent no longer just finds products. It now decides how certain it is, and what to do about uncertainty.

### The Confidence Routing System — The Post's Core Angle

Stories 4.1 and 4.2 built a two-step decision pipeline:

**Step 1 — Complexity Classification (Story 4.1):**
The agent classifies each request into 4 tiers:
- **simple**: Clear product reference + quantity ("200m de tube inox 304L DN25")
- **ambiguous**: Vague description or missing info ("comme la derniere fois mais plus long")
- **complex**: Multiple products, special conditions, certifications
- **out_of_scope**: Services, non-catalog requests

**Step 2 — Confidence Scoring + Routing (Story 4.2):**
After classification + product search, the LLM scores how well each search result matches the original request. Then a deterministic router decides the action:

| Confidence | Tier | What happens |
|-----------|------|--------------|
| >85% | High | Draft quote created automatically, sales rep just validates |
| 50-85% | Medium | Agent generates 2-5 proposals, sales rep picks the best match |
| <50% | Low | Agent escalates to sales rep with context: "here's what I understood, here's what I'm unsure about, here are suggested next steps" |
| Out-of-scope | — | Sales rep notified with explanation |

**Why this matters for the post:** Most AI demos show the happy path. This post shows what happens when the AI isn't sure. The 3-tier system is relatable to any B2B audience that has dealt with automation that either guesses wrong or just fails silently.

### Key Technical Details (for vulgarization in the post)

- Classifier uses `gpt-4o-mini` (lightweight, fast, <5s)
- Scorer also uses `gpt-4o-mini` with structured output (Pydantic models)
- Router is a **pure function** (no LLM call, just threshold comparison). This is important: the routing decision is deterministic, not AI-powered. The AI scores, the rules route.
- Thresholds are configurable per deployment (env vars `CONFIDENCE_SCORING__HIGH_THRESHOLD`, `CONFIDENCE_SCORING__LOW_THRESHOLD`)
- Fallback on LLM failure: always defaults to "low" tier (safe default, triggers human escalation rather than wrong quote)
- Input isolation: untrusted user content wrapped in security delimiters even at this stage (defense-in-depth)

### What to Vulgarize for the Post

| Technical reality | Post language |
|------------------|---------------|
| LLM structured output with Pydantic models | "the AI assigns a confidence score to each match" |
| Deterministic threshold-based router | "simple rules decide what happens next" |
| `gpt-4o-mini` via LangChain adapter | "a fast AI model" |
| `ConfidenceScoringSettings.high_threshold = 0.85` | "above 85% confidence" |
| `EscalationContext` with understood/uncertain/next_steps | "the AI explains what it understood and what it's not sure about" |
| Fallback to tier="low" on LLM error | "if something goes wrong, it asks a human instead of guessing" |

### Concrete Examples to Use in the Post

From the actual classification prompt and test scenarios:
- **High confidence**: "200m tube inox 304L DN25" — exact reference, clear quantity, one product. AI matches with 92% confidence, draft created.
- **Medium confidence**: "des plaques acier pour chaudronnerie" — no exact reference, multiple possible products. AI finds 4 matches (60-78% confidence), presents options.
- **Low confidence**: "comme la commande de janvier mais en plus grand" — no product info, relies on context the system doesn't have yet. AI escalates with explanation.

### Metrics to Include

| Metric | Value | Source |
|--------|-------|--------|
| Unit tests | 414 passing | Story 4.2 completion notes |
| Confidence tiers | 3 (high >85%, medium 50-85%, low <50%) | ConfidenceScoringSettings |
| Classification tiers | 4 (simple, ambiguous, complex, out-of-scope) | Story 4.1 |
| New tests added (4.1 + 4.2) | 61 (22 + 39) | Story completion notes |
| Classification time | <5 seconds | NFR-P4 |

### Tone & Voice Rules (CRITICAL)

From `_bmad-output/build-in-public/guidelines.md` and feedback memory:

1. **NO em dashes** (use commas, periods, or parentheses instead)
2. **NO "it's X, not Y" constructions**
3. **Vulgarize tech**: say "confidence score" not "ConfidenceResult.overall_confidence float computed via LLM structured output". Say "the AI explains what went wrong" not "EscalationContext model with understood/uncertain/suggested_next_steps fields"
4. **First person, conversational**, like explaining over coffee
5. **Authentic, not corporate**: no "leverage," "synergies," "drive value"
6. **Short sentences** preferred
7. **Problem-first approach**: lead with the challenge (AI that guesses wrong), not the solution
8. **Non-technical final question**: target audience includes B2B decision-makers and managers

### Post Structure (Non-Negotiable from guidelines.md)

1. **Hook** (1-2 sentences): Surprising result, counterintuitive finding, or question
2. **Problem** (2-3 sentences): Real B2B industrial challenge
3. **Solution/Insight** (3-5 sentences): What you built, technical but accessible
4. **Metric/Proof** (1-2 sentences): Concrete number(s)
5. **Open Question/CTA** (1-2 sentences): Genuine question, not a sales pitch
6. **Hashtags**: 3-5 max. Core: #BuildInPublic #AI. Rotate topic-specific.

### Series Continuity

- **Previous post (T.10):** Search recap. Hook: "I built a feature, benchmarked it, and then deleted the entire thing." Jargon dictionary story arc. Ended with: "Have you ever caught yourself solving a problem out of habit, only to realize it didn't exist anymore?" (228 words)
- **Narrative arc**: T.10 closed the Search phase. T.11 opens the Intelligence phase. The transition: "the system can find products. Now it needs to know how sure it is."
- **Next post (T.12):** Memory architecture (after Epic 4 later stories or Epic 6). T.11 should mention that confidence is just the first step, the system will also learn from past decisions.
- All previous posts range 207-228 words. Target ~210-220 words.

### What NOT to Do

- Do NOT repeat T.10's angle (jargon dictionary, search recap already covered)
- Do NOT repeat T.8 or T.9's angle (search deep dives already covered)
- Do NOT frame as a tutorial ("here's how to build confidence scoring")
- Do NOT get into LangGraph or Pydantic details. The audience doesn't care about the framework.
- Do NOT mention past clients by name or share confidential information
- Do NOT use data from outside this repo (synthetic data and benchmarks only)
- Do NOT oversell. Be honest that this is running on synthetic data, not production yet.
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

### File Output Locations

- Post draft: `_bmad-output/build-in-public/t11-confidence-tiers-post.md`
- Use template from: `_bmad-output/build-in-public/template.md`

### Project Structure Notes

- Build-in-public drafts go in `_bmad-output/build-in-public/`
- This is a content story, not a code story. No source code changes required.
- The story file itself lives in `_bmad-output/implementation-artifacts/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story T.11] — AC and story definition
- [Source: _bmad-output/build-in-public/guidelines.md] — Tone, structure, quality checklist
- [Source: _bmad-output/build-in-public/template.md] — Post draft template
- [Source: _bmad-output/build-in-public/t10-search-recap-post.md] — Previous post (series continuity)
- [Source: _bmad-output/implementation-artifacts/4-1-classification-de-complexite-des-demandes.md] — Story 4.1 (complexity classifier, 4 tiers, 22 tests)
- [Source: _bmad-output/implementation-artifacts/4-2-scoring-de-confiance-routage-par-tiers.md] — Story 4.2 (confidence scoring, 3 tiers, router, 39 tests)
- [Source: _bmad-output/implementation-artifacts/t-10-search-recap-post.md] — Previous story (learnings, patterns, word count)
- [Source: _bmad-output/build-in-public/guidelines.md] — Quality checklist
- [Source: docs/project-context.md] — Project patterns and conventions
- [Source: .claude/projects/-home-khalil-PycharmProjects-ai-quote-agent/memory/feedback_build_in_public_tone.md] — Tone feedback rules

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None (content story, no code changes)

### Completion Notes List

- Drafted LinkedIn post (~222 words) for the Intelligence phase opening (Epic 4)
- Post covers the 3-tier confidence routing system with concrete industrial examples
- Hook: "Most AI demos show you the perfect answer. Nobody talks about what happens when the AI isn't sure."
- Includes real metrics: 85%/50% thresholds, 414 tests, 61 new tests from stories 4.1/4.2
- Non-technical closing question targeting B2B decision-makers
- Quality review passed: no em dashes, no "it's X not Y", tech vulgarized, tone conversational
- Series continuity verified: follows T.10 (search recap), opens Intelligence phase, doesn't repeat search angles

### File List

- `_bmad-output/build-in-public/t11-confidence-tiers-post.md` (new) — LinkedIn post draft with metadata, formatting checklist, and series continuity note
- `_bmad-output/implementation-artifacts/t-11-confidence-tiers-post.md` (modified) — Story file: tasks checked, status → review, dev agent record filled
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) — Story status: ready-for-dev → review

### Change Log

- 2026-03-20: Story T.11 implemented. LinkedIn post drafted, formatted, quality-reviewed. All 3 tasks complete, all ACs satisfied.
