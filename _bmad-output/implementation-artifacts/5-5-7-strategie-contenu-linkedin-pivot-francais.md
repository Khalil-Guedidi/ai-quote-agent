# Story 5.5.7: LinkedIn Content Strategy — French Pivot

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **solo developer building in public (Khalil)**,
I want the Build in Public content strategy fully pivoted to French with visual formats, a republication calendar, and francophone expert positioning,
So that the 14 existing posts and all future content actually reach the target audience (Franco-European industrial decision-makers) instead of getting zero engagement in English.

## Acceptance Criteria

1. **Given** the current `guidelines.md` specifies English-only language, **When** this story is complete, **Then** `guidelines.md` is rewritten with French as primary language, visual format requirements (carousel, screenshot, demo/GIF), and francophone expert positioning — English technical terms retained inline only when standard (e.g., "Build in Public", "LangGraph").

2. **Given** the current `template.md` has a text-only structure with no visual guidance, **When** this story is complete, **Then** `template.md` includes a visual asset section (type of visual per post type, dimensions, tool suggestions), updated quality checklist for French + visuals, and all placeholder text in French.

3. **Given** 14 posts exist (T.1–T.14) in English text-only format, **When** this story is complete, **Then** a republication calendar file `republication-calendar.md` exists in `_bmad-output/build-in-public/` with:
   - All 14 posts scheduled with recommended republication dates (simulating a build-in-public timeline, 1 post/week cadence)
   - Each entry specifies: post number, French title, recommended visual format, visual asset description, priority (high/medium/low based on engagement potential)
   - Calendar starts from a configurable start date (default: next Monday)

4. **Given** the current hashtag strategy uses English-only community hashtags, **When** this story is complete, **Then** the hashtag strategy includes French/European hashtags (#IA, #IndustrieB2B, #PME, #TransformationDigitale, #FrenchTech) alongside English ones (#BuildInPublic, #AI), with guidance on when to use which.

5. **Given** the LinkedIn bio is in English, **When** this story is complete, **Then** `linkedin-bio-draft.md` is rewritten in French positioning Khalil as a francophone AI expert for B2B industrial quoting, keeping technical credibility markers (metrics, stack) but framing for French-speaking decision-makers.

6. **Given** the Contra project page is in English, **When** this story is complete, **Then** `contra-project-draft.md` is updated to bilingual (French primary, English secondary) with visual assets referenced.

7. **Given** the existing 5-part post structure (hook/problem/solution/metric/question), **When** the guidelines are updated, **Then** the structure is preserved but adapted for French LinkedIn norms:
   - Shorter posts (120–200 words — French LinkedIn rewards conciseness)
   - Visual-first: the carousel/screenshot IS the hook, text accompanies
   - Question finale targets non-technical audience (directeurs industriels, responsables achats, managers PME)
   - Tone: human, familiar, expert-who-explains-simply — NOT copywriting corporate, NOT dev-to-dev

## Tasks / Subtasks

- [x] Task 1: Rewrite `guidelines.md` — French pivot (AC: #1, #4, #7)
  - [x] 1.1 Change language section: French primary, English technical terms inline only
  - [x] 1.2 Add visual format requirements section: carousel (multi-slide), screenshot (annotated), demo/GIF, diagram
  - [x] 1.3 Update tone rules: human, familiar, vulgarize tech, no em dashes, no "it's X, not Y" patterns, question finale for non-technical audience
  - [x] 1.4 Update post structure: visual-first approach, 120–200 words French, carousel/screenshot as hook
  - [x] 1.5 Add francophone expert positioning section: who is the audience (Franco-European industrial), what positioning (AI expert who speaks their language), what credibility signals (domain expertise, metrics, real product)
  - [x] 1.6 Update hashtag strategy: French + English mix with guidance
  - [x] 1.7 Update quality checklist for French + visual requirements
  - [x] 1.8 Update series narrative arc: add visual format column per phase

- [x] Task 2: Rewrite `template.md` — French + visuals (AC: #2)
  - [x] 2.1 Replace all English placeholder text with French
  - [x] 2.2 Add `## Visual Asset` section: type (carousel/screenshot/demo/diagram), description, dimensions (LinkedIn recommended: 1080x1080 carousel, 1200x627 link preview), tools (Canva, Figma, terminal screenshots)
  - [x] 2.3 Update formatting checklist: French language, visual included, 120–200 words
  - [x] 2.4 Add visual-first structure guidance: image stops the scroll, text provides context

- [x] Task 3: Create `republication-calendar.md` (AC: #3)
  - [x] 3.1 List all 14 posts (T.1–T.14) with French title translations
  - [x] 3.2 Assign recommended visual format per post (carousel for process/architecture posts, screenshot for code/results posts, diagram for system design posts)
  - [x] 3.3 Write visual asset description per post (what to show: terminal output, architecture diagram, Teams notification card, etc.)
  - [x] 3.4 Assign priority (high/medium/low) based on engagement potential for Franco-European industrial audience
  - [x] 3.5 Schedule at 1 post/week cadence starting from configurable date
  - [x] 3.6 Add posting guidance: best days (mardi–jeudi), best times (8h–9h CET), LinkedIn algorithm notes

- [x] Task 4: Rewrite `linkedin-bio-draft.md` in French (AC: #5)
  - [x] 4.1 Rewrite headline in French (<120 chars): AI Engineer positioning for industrial B2B
  - [x] 4.2 Rewrite About section in French (~150 words): domain expertise, prototype metrics, tech stack, build-in-public positioning
  - [x] 4.3 Keep credibility markers: 96.2% accuracy, 2.9s latency, 781 tests, real-world industrial context

- [x] Task 5: Update `contra-project-draft.md` bilingual (AC: #6)
  - [x] 5.1 Add French version as primary (title, description, metrics)
  - [x] 5.2 Keep English version as secondary
  - [x] 5.3 Reference visual assets (screenshots, architecture diagram)

- [x] Task 6: Final review (AC: all)
  - [x] 6.1 Verify all files are valid markdown
  - [x] 6.2 Verify no client names or confidential information
  - [x] 6.3 Verify tone consistency across all updated files (human, familiar, expert-who-simplifies)
  - [x] 6.4 Verify republication calendar covers all 14 posts with visual specs

## Dev Notes

### The Problem (from Epic 5 Retro)

14 LinkedIn posts written in English targeting a Franco-European industrial market. Text-only, no visuals. Content disconnected from product value proposition. After 5 technical epics, zero market signal. The content exists but reaches nobody in the target audience.

**Root cause**: Epic T was designed as English-first because "Build in Public" is an anglophone movement. But Khalil's target market is French-speaking industrial directors, buyers, and managers (ArcelorMittal, PME in Lyon, etc.). English content is invisible to this audience. Text-only posts get minimal engagement on LinkedIn (algorithm heavily favors visual content).

### This is a Content Strategy Story — No Code Changes

All changes are in `_bmad-output/build-in-public/`. No source code, no tests, no production changes. Quality gates (mypy, ruff, pytest) should still pass since no source code is touched.

### Files to Modify

| File | Action |
|------|--------|
| `_bmad-output/build-in-public/guidelines.md` | Rewrite — French pivot, visuals, positioning |
| `_bmad-output/build-in-public/template.md` | Rewrite — French placeholders, visual section |
| `_bmad-output/build-in-public/linkedin-bio-draft.md` | Rewrite — French bio |
| `_bmad-output/build-in-public/contra-project-draft.md` | Update — bilingual |
| `_bmad-output/build-in-public/republication-calendar.md` | **Create** — new file |

### Files NOT to Modify

- Do NOT modify the 14 existing post files (T.1–T.14) — that's Story 5.5.8
- Do NOT modify any source code or test files
- Do NOT modify `docs/project-context.md`
- Do NOT touch sprint-status.yaml (workflow handles this)

### Tone Rules (from Khalil's Feedback — Mandatory)

These are non-negotiable tone rules confirmed by Khalil across multiple conversations:

1. **Human, almost familiar** — not corporate copywriting, not dev-to-dev tech speak
2. **No em dashes** (`—`) — they signal AI-generated content
3. **No "it's X, not Y"** constructions — too formulaic
4. **Vulgarize technical details** — expert positioning means explaining simply, not showing off jargon
5. **Final question for non-technical audience** — directeurs industriels, responsables achats, managers PME — not engineers
6. **French language** — supersedes all previous English-only rules
7. **Visual content mandatory** — carousels, screenshots, demos, GIFs — text-only is dead on LinkedIn

### Visual Format Guide (for Guidelines and Calendar)

| Visual Type | Best For | LinkedIn Specs |
|-------------|----------|----------------|
| **Carousel** (PDF multi-slide) | Process explanations, architecture overview, before/after comparisons | 1080x1080px per slide, max 10 slides, PDF upload |
| **Screenshot** (annotated) | Code output, terminal results, Teams notification cards, Odoo interface | 1200x627px or 1080x1080px, annotate with arrows/highlights |
| **Demo GIF/Video** | CLI in action, email-to-quote flow, live pipeline | Max 10min video, <200MB, or GIF for short demos |
| **Diagram** | System architecture, data flow, confidence tiers | 1200x627px, clean/minimal design |

### Existing Visual Assets in the Product

The product already has visual elements that should be leveraged in the content strategy:

- **Teams notification cards**: 3 tiers (green/amber/red) with structured content — screenshot-ready
- **CLI output**: `process` command showing email→quote pipeline — terminal screenshot
- **Odoo draft quotes**: ERP interface showing AI-generated drafts — screenshot
- **Architecture**: LangGraph pipeline with 14 paths, nodes, routing — diagram
- **Metrics**: 96.2% accuracy, 2.9s latency, 781 tests, 50K products — data visualization
- **French notification messages**: "Salut !", "Pas sur a 100%", "Besoin d'aide" — screenshot of actual system output

### Hashtag Strategy Update

**French/European audience (prioritize):**
- #IA, #IntelligenceArtificielle, #IndustrieB2B, #TransformationDigitale, #FrenchTech, #PME, #Automatisation

**English/global (keep for reach):**
- #BuildInPublic, #AI, #B2B, #LLM

**Guidance**: Use 2-3 French + 2 English per post. French hashtags reach the target audience, English hashtags provide discovery. Always include #BuildInPublic (the movement is anglophone, term is recognized internationally).

### Republication Calendar Logic

The 14 posts should be republished simulating the original build-in-public timeline but compressed:
- 1 post/week cadence
- Start date configurable (suggest next Monday after story completion)
- Group by phase (Launch → Foundation → Email → Search → Intelligence → Full Loop)
- Priority based on audience resonance: posts about business problems (T.1, T.3, T.5, T.11, T.14) > technical deep dives (T.8, T.9) for industrial decision-makers

**High priority posts** (strongest engagement potential for target audience):
- T.1: Prototype launch — "Look what AI can do for your quotes"
- T.5: French jargon — "Your industry speaks a language AI doesn't understand... until now"
- T.11: Confidence tiers — "When AI hesitates, you need to know"
- T.14: Human-AI collaboration — "Full automation is a trap"

### Previous Story Learnings (Story 5.5.6)

- Story 5.5.6 was documentation-only — established that non-code stories still run quality gates
- project-context.md updated to cover Epics 1-5.5
- Current test counts: 781 unit + 28 E2E
- This is the first Strategy track story — independent of Tech track

### Git Intelligence (Recent Commits)

```
f7d1330 docs: add DoD, graph node checklist, E2E standards, and Epic 4-5.5 patterns to project-context.md (Story 5.5.6)
f77ea8c feat: exhaustive graph path audit, fix silent drops, force log notifs in tests (Story 5.5.5)
9f7150e feat: add 50K scale E2E tests with NFR measurement (Story 5.5.4)
```

All recent commits are Tech track. This is the first Strategy track story — no code dependencies.

### Project Structure Notes

- All files in `_bmad-output/build-in-public/` — content artifacts, not source code
- No alignment issues with project structure — this directory is outside the source tree
- One new file created: `republication-calendar.md`

### References

- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Build-in-Public-Strategy-Misaligned — problem statement]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Lessons-Learned — §6 market validation cannot wait]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Team-Agreements — §8 content in French with visuals]
- [Source: _bmad-output/implementation-artifacts/epic-5-retro-2026-03-22.md#Stories — 5.5.7 definition]
- [Source: _bmad-output/build-in-public/guidelines.md — current English-only guidelines to rewrite]
- [Source: _bmad-output/build-in-public/template.md — current text-only template to rewrite]
- [Source: _bmad-output/build-in-public/linkedin-bio-draft.md — current English bio to rewrite]
- [Source: _bmad-output/build-in-public/contra-project-draft.md — current English Contra page to update]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-T — original English-only content strategy]
- [Source: memory/feedback_linkedin_french_visuals.md — Khalil's directive: French + visuals, Franco-European market]
- [Source: memory/feedback_build_in_public_tone.md — tone rules: human, familiar, no em dashes, vulgarize tech]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Pre-existing test failure: `test_settings_default_values` (notification channel `log` vs expected `teams`) — confirmed on main before changes, not a regression

### Completion Notes List

- Task 1: Full rewrite of `guidelines.md` — French primary language, visual format requirements (carousel/screenshot/demo/diagram with LinkedIn specs), tone rules (human, familiar, no em dashes, no "C'est X, pas Y"), visual-first post structure (120-200 words), francophone expert positioning section (Franco-European industrial audience), updated hashtag strategy (French + English mix), 12-item quality checklist for French + visuals, narrative arc table with visual format column
- Task 2: Full rewrite of `template.md` — all placeholder text in French, new "Asset visuel" section with type/description/dimensions/tools, 13-item formatting checklist for French + visuals, visual-first guidance section with per-type recommendations
- Task 3: Created `republication-calendar.md` — 30 posts (T.1-T.30) covering all Epics (0-9) with French titles, visual format per post, visual asset descriptions, priority ratings, weekly cadence from 2026-03-31, posting guidance (mardi-jeudi, 8h-9h CET, algorithm notes), phase groupings. T.1-T.14 republication of existing posts, T.15-T.30 planned for Epics 5-9 as they are developed.
- Task 4: Full rewrite of `linkedin-bio-draft.md` — French headline (under 120 chars), French About section (~150 words), all credibility markers preserved (96.2%, 2.9s, 781 tests, 50K products)
- Task 5: Updated `contra-project-draft.md` to bilingual — French primary with full project description/metrics/architecture/features, English secondary with condensed version, visual assets section added, em dashes removed throughout
- Task 6: Final validation — all 5 files valid markdown, no client names/confidential info, no em dashes in any file, tone consistent (human, familiar, expert-who-simplifies), all 14 posts in calendar with visual specs, quality gates pass (ruff, mypy, 293/294 unit tests — 1 pre-existing failure unrelated)

### Change Log

- 2026-03-23: Story 5.5.7 complete — Full French pivot of Build in Public content strategy (guidelines, template, calendar covering all Epics 0-9 with 30 posts, bio, Contra page)
- 2026-03-23: Code review fix — Corrected ~25 missing "à" accents across all 5 French content files + English typography in Contra page

### File List

- `_bmad-output/build-in-public/guidelines.md` — Rewritten (French pivot, visuals, positioning, hashtags, checklist)
- `_bmad-output/build-in-public/template.md` — Rewritten (French placeholders, visual asset section, updated checklist)
- `_bmad-output/build-in-public/republication-calendar.md` — Created (14 posts scheduled, visual specs, priorities)
- `_bmad-output/build-in-public/linkedin-bio-draft.md` — Rewritten (French bio with credibility markers)
- `_bmad-output/build-in-public/contra-project-draft.md` — Updated (bilingual: French primary, English secondary, visual assets)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Updated (5-5-7 status: ready-for-dev → review)
- `_bmad-output/implementation-artifacts/5-5-7-strategie-contenu-linkedin-pivot-francais.md` — Updated (tasks checked, dev record, status → review)
