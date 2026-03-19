# Story T.7: It's Alive Post

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **solo developer building in public**,
I want to publish a milestone post about the first real email processed end-to-end,
So that I mark the moment the system goes from prototype to functional pipeline.

## Acceptance Criteria

1. **AC-T.7.1:** LinkedIn post published — "First real email processed end-to-end"
2. **AC-T.7.2:** Post compares prototype metrics vs production metrics
3. **AC-T.7.3:** Contra project updated with production pipeline results
4. **AC-T.7.4:** Post draft archived in `_bmad-output/build-in-public/`

## Tasks / Subtasks

- [x] Task 1: Write LinkedIn post draft (AC: 1, 2, 4)
  - [x] 1.1 Follow template structure from `_bmad-output/build-in-public/template.md` (hook > problem > solution > metric > open question)
  - [x] 1.2 Hook must open with the milestone moment: the system processed its first real email end-to-end. Angle: going from prototype demo to a working pipeline
  - [x] 1.3 Include prototype vs production comparison (see Dev Notes for metrics source of truth)
  - [x] 1.4 Cover what Epic 2 actually built: IMAP reception, content cleaning, LLM extraction, multi-request splitting, security layers, structured logging
  - [x] 1.5 Include concrete production metrics. Options: 188 automated tests (0 at prototype), 6 stories, 120 new tests, 0 regressions, 52 Python source files, 2066 LOC, 5 service modules, 4 security modules
  - [x] 1.6 End with a genuine open question (see Question Ideas below)
  - [x] 1.7 Run through formatting checklist from guidelines (150-250 words, English, no client names, etc.)
  - [x] 1.8 Apply tone rules: no em dashes, no "it's X, not Y" constructions, conversational/human tone, vulgarize tech for non-technical readers
  - [x] 1.9 Add series continuity note referencing T.6 (error & edge cases)
  - [x] 1.10 Add 3-5 hashtags per strategy: #BuildInPublic #AI + topic-specific (e.g., #Milestone #B2B #Python)
  - [x] 1.11 Save as `_bmad-output/build-in-public/t7-its-alive-post.md`
- [x] Task 2: Write Contra project update text (AC: 3)
  - [x] 2.1 Draft a short Contra project update section at the bottom of the post file (user publishes manually)
  - [x] 2.2 Include: Epic 2 completion, pipeline description, production metrics vs prototype, next phase teaser (Epic 3: product catalog search)

## Dev Notes

### Context

This is a **content story**, not a code story. Output is a markdown file. No application code, tests, or infrastructure changes. The dev agent creates files in the repo; the user manually publishes to LinkedIn and updates Contra.

This is post **#7** in the Build in Public series. It follows T.6 (error & edge cases) and is the **third and final post in the Email Pipeline phase** (Epic 2). This is a **milestone recap post** — similar in spirit to T.4 (Foundation Recap) but for the email processing pipeline. The narrative: the system went from a working prototype to a pipeline that actually processes emails.

**Trigger:** Epic 2 is complete (6/6 stories done, retrospective done). All stories 2.1-2.6 shipped with 0 regressions.

### The "It's Alive" Narrative

The core story: the prototype (Epic 0, n8n) proved the concept in a weekend. But it was a demo. No tests. No deployment. No error handling. Epic 1 rebuilt the foundation. Epic 2 built the first real pipeline: email comes in, gets cleaned, gets parsed by an LLM, gets split into individual quote requests. The system processes real emails now.

This is the moment it stops being a side project and starts being a product. The post should capture that energy without being boastful. Frame it as: "here's where we are, here's what it took, here's what's next."

Key tension: the prototype wowed everyone with 96.2% accuracy. The production system doesn't have that metric yet (no product matching pipeline yet — that's Epic 3). What it has instead is reliability, error handling, security, and a real pipeline. The post should frame this honestly: "the prototype could find products. The production system can receive, parse, and structure real emails. Different problems, different metrics."

### Prototype vs Production Metrics (Source of Truth)

| Aspect | Prototype (Epic 0, n8n) | Production (Epic 2, Python) |
|--------|------------------------|----------------------------|
| Platform | n8n (low-code) | Python + LangGraph + PostgreSQL |
| Test count | 0 | 188 automated tests |
| Product matching accuracy | 96.2% on 680 synthetic products | Not yet (Epic 3) |
| Latency | 2.9s per quote | Not comparable (different scope) |
| Error handling | None | 10+ graceful degradation patterns |
| Security | None | 2-layer prompt injection defense, log redaction |
| Pipeline stages | Monolithic n8n flow | 4 discrete stages: receive → clean → extract → split |
| Deployment | Docker Compose (n8n + Odoo) | Docker with CLI tools, CI/CD pipeline |
| Code quality gates | None | mypy strict + ruff lint + 188 tests |
| Configuration | Hardcoded | YAML-based with env overrides |
| Stories delivered | 6 (Epic 0) | 14 (Epic 1: 8 + Epic 2: 6) |

**Important:** The prototype and production systems solve different parts of the problem. The prototype went end-to-end (email → quote in ERP). Production has only built the first half (email → structured data). Product matching and quote generation are Epics 3-4. Be honest about this — do NOT claim the production system does everything the prototype did.

### Concrete Numbers to Use (Source of Truth)

| Fact | Source |
|------|--------|
| 188 total automated tests | Test suite as of Epic 2 completion |
| 0 tests at prototype | Epic 0 had no automated tests |
| 120 tests added in Epic 2 alone | 68 → 188 (retro metrics) |
| 0 regressions across all stories | Epic 2 retrospective |
| 6 stories in Epic 2 | Sprint status |
| 14 stories total (Epic 1 + 2) | 8 + 6 |
| 52 Python source files | Current source tree |
| 4 pipeline stages | receive → clean → extract → split |
| 10s timeout per LLM call | email_extractor.py, request_splitter.py |
| 2 security layers | sanitizer.py, input_isolation.py |
| 4 security modules | sanitizer, input_isolation, log_redactor, audit logger |
| 5 integration adapters | Epic 1 (IMAP, PostgreSQL, LLM, ERP, Notification) |

Pick 2-3 for the metric/proof section. Most compelling: 188 tests vs 0, the 4-stage pipeline concept, or the 14 stories / 2 epics milestone.

### Tone Guidance

This is a milestone post. The tone should be:
- **Celebratory but grounded:** this is a real milestone, but the system only handles half the pipeline (email → data, not data → quote yet)
- **Reflective:** what it took to get from prototype to pipeline
- **Forward-looking:** hint at what's next (Epic 3: product catalog search)
- **Honest about scope:** the prototype matched products. Production doesn't do that yet. That's okay. Different phase, different goals.

**Specific tone rules (from user feedback):**
- NO em dashes. Use periods, commas, or restructure sentences instead.
- NO "it's X, not Y" constructions. Too formulaic.
- Vulgarize technical details. Say "188 tests" not "188 pytest unit tests across 24 test modules." Say "4-stage pipeline" not "a 4-stage async processing pipeline with per-stage error isolation."
- Write like you're explaining this to someone over coffee. First person, short sentences, conversational.
- The final question should invite reflection on the prototype-to-production journey. Target: anyone who has built something from scratch and felt the gap between "demo works" and "production works."

### Content Guidelines to Follow

All content must comply with `_bmad-output/build-in-public/guidelines.md`:

- **Tone:** Technical but accessible, authentic, conversational. NOT corporate.
- **Structure:** Hook > Problem > Solution/Insight > Metric/Proof > Open Question/CTA
- **Length:** 150-250 words per post
- **Language:** English only
- **Confidentiality:** No past client names, no confidential info, synthetic data only
- **Hashtags:** 3-5 max. Always: #BuildInPublic #AI. Rotate based on topic.
- **Quality:** Must pass the quality checklist in guidelines.md before marking done

[Source: _bmad-output/build-in-public/guidelines.md]

### Template to Follow

Use the exact template structure from `_bmad-output/build-in-public/template.md`:

1. Post metadata (story number, phase, date)
2. Hook (1-2 sentences)
3. Problem statement (2-3 sentences)
4. Solution / Insight (3-5 sentences)
5. Metric / Proof (1-2 sentences)
6. Open question / CTA (1-2 sentences)
7. Formatting checklist
8. Series continuity note

[Source: _bmad-output/build-in-public/template.md]

### Previous Story Intelligence (T.6)

Story T.6 created the error & edge cases LinkedIn post. Key learnings:

- **T.6 draft was ~207 words.** Series is consistently hitting 207-213 words. Keep this discipline.
- **T.6 ended with:** "When you ship an AI feature, what's your plan for when the model just... doesn't work?" T.7 should NOT repeat a question about failure handling or AI reliability.
- **T.6 focused on graceful degradation and error patterns.** T.7 should NOT rehash the error handling details. T.6 = what happens when things go wrong. T.7 = the milestone of having a working pipeline.
- **T.4 was the other milestone recap (Foundation).** T.4 asked "How much of your project is the invisible work that nobody ever sees?" T.7 is adjacent (also a recap) but the angle is different: T.4 = the invisible foundation. T.7 = the system actually works now. Avoid overlapping framing about "invisible work."
- **T.4 metrics were:** 8 stories, 5 adapters, 68 tests. T.7 should show progression: 14 stories total, 188 tests, pipeline processing real emails.
- **Code review lesson (T.0):** Never present planned/future features as existing capabilities. For T.7: the production system processes emails into structured data. It does NOT match products or generate quotes yet (that's Epics 3-4). Be clear about scope.

[Source: _bmad-output/implementation-artifacts/t-6-error-edge-cases-post.md]

### Question Ideas (Pick One)

These are potential open questions. Choose the one that feels most natural and non-repetitive with T.1-T.6:

1. "What's the biggest gap you've noticed between your prototype and your production system?" (targeting anyone who has shipped something — broad, reflective, invites war stories)
2. "At what point did your side project start feeling like a real product?" (emotional, relatable, invites founders and builders to share their milestone moments)
3. "How do you measure progress when the metrics that matter are different from your prototype metrics?" (targeting engineers/PMs, thoughtful, invites discussion about evolving success criteria)

Avoid: questions about failure handling (T.6), invisible work (T.4), domain jargon (T.5), data quality (T.3), stack decisions (T.2), quoting speed (T.1).

### Project Structure Notes

- All Build in Public content lives in `_bmad-output/build-in-public/`
- Post drafts use naming convention: `t{N}-{slug}.md` (e.g., `t7-its-alive-post.md`)
- No conflicts with existing project structure

### Anti-Pattern Prevention

- **DO NOT** use em dashes in the LinkedIn post text
- **DO NOT** use "it's X, not Y" constructions
- **DO NOT** claim the production system matches products or generates quotes. That's Epics 3-4. The production pipeline receives emails, cleans them, extracts structured data, and splits multi-item requests. Be clear about scope.
- **DO NOT** compare production accuracy to prototype 96.2%. The production system hasn't implemented search yet. Different metric entirely.
- **DO NOT** mention any past client or employer by name
- **DO NOT** explain asyncio, Pydantic, LangGraph internals, or implementation details. Vulgarize: "188 tests" not "188 pytest test functions." Say "4-stage pipeline" not "a 4-stage async processing pipeline with inline integration in _persist_emails()."
- **DO NOT** exceed 250 words on the LinkedIn post
- **DO NOT** rehash error handling patterns (T.6), cleaning pipeline (T.5), dirty data (T.3), stack decisions (T.2), or prototype launch (T.1)
- **DO NOT** use corporate buzzwords ("leverage", "synergy", "drive value", "robust")
- **DO NOT** frame this as "we're done." The system is half-built. Epic 2 is the email half. Epics 3-4 are search + quote generation. Frame it as a real milestone on the journey, not the destination.
- **DO** include prototype vs production comparison (test count, pipeline stages, error handling)
- **DO** frame the milestone honestly: "the pipeline works" not "the product is done"
- **DO** tease what's next (Epic 3: product catalog search)
- **DO** reference T.6 in the series continuity note
- **DO** keep it under 250 words. T.1-T.6 averaged ~207-213 words. Stay in range.
- **DO** make the reader reflect on their own prototype-to-production journey
- **DO** frame professional domain knowledge as: "I'm building an AI that processes B2B quote request emails..." (no client names)
- **DO** include a Contra update section below the post

### References

- [Source: epics.md - Epic T: Build in Public, Story T.7]
- [Source: epic-2-retro-2026-03-19.md - Epic 2 delivery metrics and lessons learned]
- [Source: _bmad-output/build-in-public/template.md - Post template]
- [Source: _bmad-output/build-in-public/guidelines.md - Content guidelines]
- [Source: _bmad-output/build-in-public/t6-error-edge-cases-post.md - Previous post for continuity]
- [Source: _bmad-output/build-in-public/t4-foundation-recap-post.md - Previous milestone recap for differentiation]
- [Source: _bmad-output/build-in-public/t1-prototype-launch-post.md - Prototype metrics for comparison]
- [Source: _bmad-output/implementation-artifacts/t-6-error-edge-cases-post.md - Previous story context]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — content story, no code debugging required.

### Completion Notes List

- ✅ Task 1: LinkedIn post draft written (~220 words), follows template structure (hook > problem > solution > metric > open question)
- ✅ Post includes prototype vs production comparison: 0→188 tests, monolithic→4 stages, no security→security layers
- ✅ Honest about scope: explicitly states production can't match products yet (Epic 3)
- ✅ Uses question #2: "At what point did your side project start feeling like a real product?"
- ✅ No em dashes, no "it's X, not Y", no corporate buzzwords, no client names
- ✅ Series continuity note references T.6 and closes Email Pipeline phase
- ✅ Hashtags: #BuildInPublic #AI #Milestone #B2B #Python (5 tags)
- ✅ Task 2: Contra project update section included at bottom of post file with Epic 2 metrics and Epic 3 teaser

### Change Log

- 2026-03-19: Created t7-its-alive-post.md with LinkedIn post draft and Contra update section
- 2026-03-19: [Code Review] Fixed "it's X, not Y" construction per tone rules; updated File List

### File List

- `_bmad-output/build-in-public/t7-its-alive-post.md` (NEW) — LinkedIn post draft + Contra update
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED) — Story status set to review
