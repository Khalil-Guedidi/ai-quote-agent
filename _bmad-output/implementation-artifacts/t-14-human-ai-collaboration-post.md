# Story T.14: Human-AI Collaboration Post

Status: done

## Story

As a **solo developer building in public**,
I want to publish a post about designing the human-in-the-loop workflow,
so that I share why full automation is the wrong goal for high-stakes B2B decisions.

## Acceptance Criteria

1. **AC-T.14.1:** LinkedIn post published — "Why full automation is a trap: designing the human-in-the-loop"
2. **AC-T.14.2:** Post covers trust, oversight, and the notification/review workflow
3. **AC-T.14.3:** Post draft archived in `_bmad-output/build-in-public/t14-human-ai-collaboration-post.md`

## Tasks / Subtasks

- [x] Task 1: Draft LinkedIn post (AC: #1, #2)
  - [x] Write hook about the trap of full automation in high-stakes B2B contexts
  - [x] Explain the problem: in industrial quoting, a wrong quote costs real money, trust, or compliance violations
  - [x] Describe the human-in-the-loop design: 3 notification tiers (green/amber/red), the AI decides how much human attention each request needs
  - [x] Include the key insight: the agent never sends a quote directly, always creates a draft, always involves a human
  - [x] Include metric/proof from Epic 5 implementation (test counts, notification types, delivery time)
  - [x] End with a genuine non-technical question for B2B decision-makers about trust/automation balance
  - [x] Verify 150-250 words, 3-5 hashtags, no em dashes, no "it's X, not Y"
- [x] Task 2: Format and archive post draft (AC: #3)
  - [x] Create `_bmad-output/build-in-public/t14-human-ai-collaboration-post.md` using template from `_bmad-output/build-in-public/template.md`
  - [x] Fill metadata (Story T.14, Phase: Full Loop, date)
  - [x] Fill formatting checklist and series continuity note
- [x] Task 3: Quality review against guidelines
  - [x] Run quality checklist from `_bmad-output/build-in-public/guidelines.md`
  - [x] Verify tone rules (no em dashes, no "it's X not Y", vulgarize tech, non-technical question)
  - [x] Verify series continuity with T.13 and position as Full Loop phase opener

## Dev Notes

### CRITICAL: This Is the Full Loop Phase Opener (Epic 5 Mid-Point)

T.13 closed the Intelligence phase (Epic 4). T.14 opens the Full Loop phase (Epic 5). The narrative arc: T.13 ended with "The agent can now think. Next step: making sure the right human sees the result at the right time." T.14 picks up exactly there.

The core angle: full automation sounds tempting, but in B2B industrial quoting, the stakes are too high. The design choice is not "AI vs. human" but "how much human attention does each request need?" The AI triages, the human validates.

### What Epic 5 Built — The Post's Core Material

Epic 5 (Stories 5.0a-5.5, with 5.6 still backlog) delivered the notification and human workflow layer. Stories 5.2 and 5.3 are the primary triggers for this post.

**The 3 notification tiers (the heart of human-in-the-loop):**

| Tier | Confidence | Card Color | What the Human Sees | Story |
|------|-----------|------------|---------------------|-------|
| High (>85%) | Exact match found | Green | "Draft ready, validate it" + ERP link | 5.1 |
| Medium (50-85%) | Fuzzy match | Amber | 2-5 proposals, human picks the right one | 5.2 |
| Low (<50%) | Can't handle it | Red | What was understood, what's uncertain, next steps | 5.3 |

**Key design principles to highlight:**
1. **The agent never sends a quote.** It always creates a DRAFT. A human always validates.
2. **The AI decides how much attention, not whether attention.** Every request gets human eyes. High-confidence gets a quick validation. Low-confidence gets full context for manual handling.
3. **Fail-safe defaults from Epic 4 carry through:** if the notification fails, the draft still exists in the ERP. No silent failures.
4. **Tone matters:** notifications use casual French ("Salut !", "Pas sur a 100%", "Celui-la est complique..."), not corporate speak. Designed to feel like a helpful colleague, not an enterprise system.

**Additional Epic 5 context (background, don't make it central to post):**
- Story 5.4: Batch summaries (morning digest) + weekly manager reports
- Story 5.5: Throttling rules (no flood of notifications, max 1/min, batch if >5 in 10min)
- Story 5.0a: Teams webhook integration
- Story 5.0b: Fixed flaky E2E test (LLM splitting)

### Test Metrics from Epic 5 (Use Selectively)

| Milestone | Tests | Source |
|-----------|-------|--------|
| After Story 5.1 | 623 | Story 5.1 completion notes |
| After Story 5.2 | 636 (+13) | Story 5.2 completion notes |
| After Story 5.3 | 651 (+15) | Story 5.3 completion notes |
| After Story 5.5 | ~700+ (estimate from commits) | Latest commits |

Test growth across all epics: 68 -> 188 -> 363 -> 599 -> 700+

### What to Vulgarize for the Post

| Technical reality | Post language |
|------------------|---------------|
| Teams Adaptive Cards with accent bars | "color-coded notifications" or "a green card, an amber card, a red card" |
| Fire-and-forget notification pattern | "if the notification fails, the draft is still safe in the ERP" |
| 3 confidence tiers with threshold routing | "the AI sorts each request by how sure it is" |
| Tutoiement + casual French tone in cards | "the bot talks like a colleague, not a corporate system" |
| Notification throttle (max 1/min, batch >5) | "smart batching so you're not drowning in alerts" |
| Draft-only ERP write, never sent directly | "the agent never sends a quote, always a draft" |
| `notify_quote_ready`, `notify_multi_proposal`, `notify_escalation` | "3 types of notification, one for each level of certainty" |

### Concrete Examples for the Post

- **High-confidence in action:** Client asks for "tube inox 304L DN25". Agent finds exact match, scores 92% confidence, creates draft in Odoo, sends green notification: "Draft ready for [Client], validate it." Sales rep clicks one button.
- **Medium-confidence in action:** Client asks for "steel plates for boilermaking." Agent finds 3 possible matches. Amber notification with options: "Not 100% sure. Here are my 3 options." Sales rep picks the right one.
- **Low-confidence in action:** Client asks for something out of scope. Red notification: "This one is complicated. Here's what I understood, here's what's unclear, here's what to do next." Full context for manual handling.
- **The philosophical point:** The AI doesn't decide less when it's uncertain. It decides MORE (about what context the human needs). High-confidence = minimal context needed. Low-confidence = maximum context provided.

### Tone & Voice Rules (CRITICAL)

From `_bmad-output/build-in-public/guidelines.md` and feedback memory:

1. **NO em dashes** (use commas, periods, or parentheses instead)
2. **NO "it's X, not Y" constructions**
3. **Vulgarize tech**: say "color-coded notifications" not "Teams Adaptive Cards with accent bar styling". Say "the AI sorts by how sure it is" not "confidence tier routing via threshold-based classification"
4. **First person, conversational**, like explaining over coffee
5. **Authentic, not corporate**: no "leverage," "synergies," "drive value"
6. **Short sentences** preferred
7. **Problem-first approach**: lead with why full automation is dangerous, not the tech
8. **Non-technical final question**: target audience includes B2B decision-makers and managers

### Post Structure (Non-Negotiable from guidelines.md)

1. **Hook** (1-2 sentences): Surprising or counterintuitive claim about automation
2. **Problem** (2-3 sentences): Real B2B industrial challenge (wrong quotes = real cost)
3. **Solution/Insight** (3-5 sentences): The 3-tier human-in-the-loop design
4. **Metric/Proof** (1-2 sentences): Concrete number(s)
5. **Open Question/CTA** (1-2 sentences): Genuine question about trust/automation balance
6. **Hashtags**: 3-5 max. Core: #BuildInPublic #AI. Rotate topic-specific.

### Series Continuity

- **Previous post (T.13):** Intelligence Recap. Closed Epic 4 with "The agent can now think. Next step: making sure the right human sees the result at the right time." (218 words). Hook was about the transition from finding products to deciding what to do about them.
- **T.11 callback opportunity:** T.11 introduced the 3 confidence tiers. T.14 shows what those tiers LOOK LIKE to the sales rep (the notification experience). T.11 was the scoring system. T.14 is the human experience of that scoring system.
- **Narrative arc:** T.13 showed the agent can reason. T.14 shows why reasoning alone isn't enough. The system needs a human loop, and that loop needs to be well-designed (right person, right time, right context). The philosophical shift: from "can the AI do it?" to "how do we make AI and humans work together?"
- **Next post (T.15):** Full Loop Recap (after Epic 5). T.14 should set up the idea that the loop is now complete: email arrives, agent processes, human validates, quote goes out. T.15 will zoom out on the entire pipeline.
- All previous posts range 207-229 words. Target ~210-220 words.

### What NOT to Do

- Do NOT repeat T.11's confidence tiers explanation in detail (already covered). Reference them briefly, focus on what the HUMAN sees.
- Do NOT repeat T.13's 7-step pipeline description (already covered). Just reference that "the agent can now reason."
- Do NOT frame as a tutorial ("here's how to build notifications")
- Do NOT get into Teams APIs, Adaptive Cards schema, webhook configs. The audience doesn't care.
- Do NOT mention past clients by name or share confidential information
- Do NOT use data from outside this repo (synthetic data and benchmarks only)
- Do NOT oversell. Be honest that this is synthetic data, not production yet.
- Do NOT use em dashes, "it's X, not Y" constructions, or corporate buzzwords
- Do NOT make the question at the end too technical. Ask something a manager or business owner would relate to.
- Do NOT focus on the notification tech (Teams, webhooks). Focus on the PHILOSOPHY of human-in-the-loop.

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
| T.13 | ~218 |

### File Output Locations

- Post draft: `_bmad-output/build-in-public/t14-human-ai-collaboration-post.md`
- Use template from: `_bmad-output/build-in-public/template.md`

### Project Structure Notes

- Build-in-public drafts go in `_bmad-output/build-in-public/`
- This is a content story, not a code story. No source code changes required.
- The story file itself lives in `_bmad-output/implementation-artifacts/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story T.14] — AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5] — Full Epic 5 stories and acceptance criteria
- [Source: _bmad-output/build-in-public/guidelines.md] — Tone, structure, quality checklist
- [Source: _bmad-output/build-in-public/template.md] — Post draft template
- [Source: _bmad-output/build-in-public/t13-intelligence-recap-post.md] — Previous post (series continuity, T.13 closer)
- [Source: _bmad-output/build-in-public/t11-confidence-tiers-post.md] — T.11 confidence tiers post (callback opportunity)
- [Source: _bmad-output/implementation-artifacts/t-13-intelligence-recap-post.md] — Previous story file (patterns, learnings)
- [Source: _bmad-output/implementation-artifacts/5-1-notification-devis-pret-high-confidence.md] — Story 5.1 implementation (high-confidence notification)
- [Source: _bmad-output/implementation-artifacts/5-2-notification-multi-propositions-medium-confidence.md] — Story 5.2 implementation (multi-proposal notification)
- [Source: _bmad-output/implementation-artifacts/5-3-notification-escalade-low-confidence.md] — Story 5.3 implementation (escalation notification)
- [Source: _bmad-output/implementation-artifacts/5-5-regles-de-timing-batching-des-notifications.md] — Story 5.5 implementation (throttling/batching)
- [Source: .claude/projects/-home-khalil-PycharmProjects-ai-quote-agent/memory/feedback_build_in_public_tone.md] — Tone feedback rules
- [Source: docs/project-context.md] — Project patterns and conventions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None (content story, no code changes)

### Completion Notes List

- Post drafted at 219 words (target 210-220), within 150-250 range
- Hook: counterintuitive angle ("the more accurate, the less I want it acting alone")
- 3-tier notification design (green/amber/red) described in accessible language
- Key insight highlighted: agent never sends a quote, always a draft
- Metric: 700+ automated tests, casual French tone ("Salut !", "Pas sur a 100%")
- Question targets B2B decision-makers (trust/automation balance)
- All tone rules verified: no em dashes, no "it's X not Y", tech vulgarized
- Series continuity: picks up exactly where T.13 ended, callbacks to T.11 confidence tiers
- Quality checklist from guidelines.md fully satisfied

### Change Log

- 2026-03-22: Story T.14 implemented. Post drafted, formatted, quality-reviewed. All 3 tasks complete.
- 2026-03-22: Code review completed. 2 fixes applied:
  - [M1] Fixed grammar in hook: "gets accurate" → "The more accurate my AI quote agent gets"
  - [L1] Reworked "X, not Y" construction: replaced with "The bot sounds like a colleague. Casual French, on purpose."
  - Added proper French accents: "Pas sûr à 100%"
  - Status → done

### File List

- _bmad-output/build-in-public/t14-human-ai-collaboration-post.md (new)
