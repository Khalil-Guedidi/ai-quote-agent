# Story T.6: Error & Edge Cases Post

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **solo developer building in public**,
I want to publish a post about handling failure and edge cases in AI pipelines,
So that I show the engineering rigor behind the "happy path" demos.

## Acceptance Criteria

1. **AC-T.6.1:** LinkedIn post published — "What happens when the AI can't understand the email"
2. **AC-T.6.2:** Post covers graceful degradation, fallback strategies, and escalation design
3. **AC-T.6.3:** Post draft archived in `_bmad-output/build-in-public/`

## Tasks / Subtasks

- [x] Task 1: Write LinkedIn post draft (AC: 1, 2, 3)
  - [x] 1.1 Follow template structure from `_bmad-output/build-in-public/template.md` (hook > problem > solution > metric > open question)
  - [x] 1.2 Hook must open with the uncomfortable question: what happens when your AI pipeline fails? Angle: the boring engineering that makes AI reliable
  - [x] 1.3 Cover graceful degradation patterns actually implemented in the codebase (see Dev Notes below for source of truth)
  - [x] 1.4 Include concrete examples: 10s timeout protection, safety valve at 90% content removal, per-email error isolation, short-circuit optimization for single items, "never hallucinate" design (None over guesses)
  - [x] 1.5 Include a metric/proof element. Options: 166 total automated tests, 10s timeout ceiling per LLM call, pipeline processes next email even when one fails, confidence scoring drops 10% per missing field
  - [x] 1.6 End with a genuine open question about failure handling or reliability in AI systems (see Question Ideas below)
  - [x] 1.7 Run through formatting checklist from guidelines (150-250 words, English, no client names, etc.)
  - [x] 1.8 Apply tone rules: no em dashes, no "it's X, not Y" constructions, conversational/human tone, vulgarize tech for non-technical readers
  - [x] 1.9 Add series continuity note referencing T.5 (French industrial jargon)
  - [x] 1.10 Add 3-5 hashtags per strategy: #BuildInPublic #AI + topic-specific (e.g., #Engineering #Reliability #B2B)
  - [x] 1.11 Save as `_bmad-output/build-in-public/t6-error-edge-cases-post.md`

## Dev Notes

### Context

This is a **content story**, not a code story. Output is a markdown file. No application code, tests, or infrastructure changes. The dev agent creates files in the repo; the user manually publishes to LinkedIn.

This is post **#6** in the Build in Public series. It follows T.5 (French industrial jargon) and is the second post in the **Email Pipeline phase** (Epic 2). The narrative shifts from "parsing domain-specific language" to "what happens when things go wrong." This post showcases the engineering discipline behind reliable AI systems.

**Trigger:** Story 2.4 (multi-request splitting) is done. Stories 2.1-2.4 collectively built the email processing pipeline with comprehensive error handling.

### What Stories 2.1-2.4 Actually Built (Source of Truth)

| Story | What was built | Key error handling |
|-------|---------------|-------------------|
| 2.1 | IMAP email reception pipeline | Polling resilience, email persistence |
| 2.2 | Email content cleaning (4-stage pipeline) | Safety valve: if >90% stripped, return original |
| 2.3 | LLM-based structured data extraction | 10s timeout, per-email error isolation, empty content short-circuit, no-hallucination (None not guesses), confidence heuristic |
| 2.4 | Multi-request splitting with LLM grouping | 10s timeout, graceful degradation (fall back to single request on failure), short-circuit for 0-1 items, out-of-bounds index protection |

### Graceful Degradation Patterns (from the actual code)

These are the real patterns implemented across Stories 2.1-2.4. The post should draw from these:

1. **Per-email error isolation:** One email's extraction failure doesn't block the pipeline. Status is set to `extraction_failed`, error is logged, next email processes normally.

2. **Safety valve (cleaning):** If the 4-stage cleaning pipeline strips >90% of email content, it returns the original normalized text instead. Over-cleaning is worse than no cleaning.

3. **Short-circuit optimization:** When an email has 0 or 1 line items, the splitter skips the LLM call entirely. No API cost, no latency, no risk of error. Returns immediately.

4. **Timeout protection:** Every LLM call has a 10-second ceiling (`asyncio.wait_for`). If the model takes too long, a specific `LLMTimeoutError` is raised instead of hanging forever.

5. **Fallback on splitting failure:** If the splitting LLM call times out or fails, the system falls back to treating all line items as a single quote request. The pipeline continues.

6. **No hallucination design:** When extraction finds missing information (no quantity, no product reference), it sets those fields to `None` instead of guessing. The system prompt explicitly says "NEVER guess or hallucinate."

7. **Confidence heuristic:** Extraction confidence drops 10% per missing field and 30% if no line items were found. This signals downstream components about data quality.

8. **LLM provider error handling:** Authentication errors, connection failures, and rate limits are caught, converted to typed exceptions (`AdapterError`), and handled without crashing.

9. **Out-of-bounds index protection:** When the splitting LLM returns indices that don't match any line item, the system silently skips them instead of crashing.

10. **Prompt injection defense (2 layers):** Layer 1 isolates raw email content with delimiters + sanitization before extraction. Layer 2 sanitizes extracted data before splitting. 24 threat patterns detected and neutralized.

### Concrete Numbers to Use (Source of Truth)

| Fact | Source |
|------|--------|
| 166 total automated tests | Test suite as of Story 2.4 |
| 10s timeout ceiling per LLM call | email_extractor.py and request_splitter.py |
| 90% safety valve threshold | email_cleaner.py |
| -10% confidence per missing field | email_extractor.py heuristic |
| -30% confidence if no items extracted | email_extractor.py heuristic |
| 24 threat patterns for prompt injection | sanitizer.py |
| Per-email isolation: one failure, others continue | email_poller.py |
| Short-circuit: 0-1 items skip LLM entirely | request_splitter.py |

Pick 2-3 for the "metric/proof" section. Most compelling: 166 tests, the per-email isolation concept (one fails, others continue), or the 10s timeout ceiling.

### The "Error & Edge Cases" Narrative

The core tension: AI demos always show the happy path. But in production B2B email processing, things go wrong constantly. The LLM times out. The email is too short to parse. The sender writes gibberish. The model hallucinates a quantity that was never mentioned.

The post should frame this as: **the boring engineering that makes AI reliable.** Not the flashy LLM prompt, but the timeout protection, the fallback strategies, the confidence scoring, the "if everything fails, at least don't crash" philosophy.

Key insight for the post: The hardest part of building AI for production isn't getting it to work. It's deciding what happens when it doesn't work. Every failure mode needs a plan. Every edge case needs a graceful degradation path. The happy path demo is 10% of the code. The other 90% is making sure the system survives the real world.

### Tone Guidance

This is the second "Email Pipeline" phase post. The tone should be:
- **Honest about failure:** this is a post about things going wrong, not about everything being perfect
- **Engineering-focused:** show the discipline behind reliability
- **Relatable:** anyone building AI for production knows this pain
- **Slightly contrarian:** most AI content focuses on capabilities. This post focuses on limitations and how to handle them.

**Specific tone rules (from user feedback):**
- NO em dashes. Use periods, commas, or restructure sentences instead.
- NO "it's X, not Y" constructions. Too formulaic.
- Vulgarize technical details. Say "166 tests" not "166 pytest unit tests across 12 test modules covering extraction, splitting, model validation, and integration." Say "10-second timeout" not "asyncio.wait_for with a 10.0s timeout parameter."
- The final question targets people building AI systems for production, dealing with failure modes, or thinking about reliability.
- Write like you're explaining this to someone over coffee. First person, short sentences, conversational.

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

### Previous Story Intelligence (T.5)

Story T.5 created the French industrial jargon LinkedIn post. Key learnings:

- **T.5 draft was ~210 words.** Series is consistently hitting ~207-213 words. Keep this discipline.
- **Post structure continues to work well:** hook > problem > solution > metric > question flow.
- **T.5 ended with:** "What's the weirdest abbreviation your industry uses that outsiders would never understand?" T.6 should NOT repeat a similar question about domain jargon. The error/edge cases post opens different territory (reliability, failure modes, production AI).
- **T.5 focused on French industrial jargon and the cleaning pipeline.** T.6 should NOT rehash the cleaning pipeline or jargon examples. T.5 = what the data looks like. T.6 = what happens when processing fails.
- **T.4 asked about invisible work.** T.6 is adjacent (error handling is "invisible work") but the angle is different: T.4 = infrastructure nobody sees. T.6 = failure modes nobody thinks about until production. Avoid overlapping framing.
- **Code review lesson (T.0):** Never present planned/future features as existing capabilities. For T.6: the error handling patterns are real and working. Do NOT claim the system handles every possible failure (it handles the ones designed for). The confidence scoring is a placeholder heuristic, not ML-based (that's Epic 4).
- **T.5 code review fixes:** Added missing jargon examples (Ø, lg), fixed DN50-PN16 to DN50--PN16. Lesson: verify examples match actual codebase before publishing.

[Source: _bmad-output/implementation-artifacts/t-5-french-industrial-jargon-post.md]

### Question Ideas (Pick One)

These are potential open questions. Choose the one that feels most natural and non-repetitive with T.1-T.5:

1. "How do you decide which failures are worth handling gracefully and which ones should just crash loudly?" (targeting engineers building production systems)
2. "What's your ratio of 'happy path' code to 'everything went wrong' code in production?" (broad, relatable, invites engagement about engineering discipline)
3. "When you ship an AI feature, what's your plan for when the model just... doesn't work?" (targeting AI builders, honest about LLM unreliability)

Avoid: questions about domain jargon (T.5 covered that), questions about invisible work (T.4 covered that), questions about data quality (T.3 covered that), questions about stack decisions (T.2 covered that), questions about quoting speed (T.1 covered that).

### Project Structure Notes

- All Build in Public content lives in `_bmad-output/build-in-public/`
- Post drafts use naming convention: `t{N}-{slug}.md` (e.g., `t6-error-edge-cases-post.md`)
- No conflicts with existing project structure

### Anti-Pattern Prevention

- **DO NOT** use em dashes in the LinkedIn post text
- **DO NOT** use "it's X, not Y" constructions
- **DO NOT** claim the confidence scoring is ML-based or sophisticated. It's a placeholder heuristic (-10% per missing field). Proper scoring is Epic 4.
- **DO NOT** mention prompt injection defense in the post. Security is Story 2.5, not the focus here. Keep the angle on graceful degradation and failure handling.
- **DO NOT** mention any past client or employer by name
- **DO NOT** explain asyncio, Pydantic, or implementation details. Vulgarize: "a 10-second timeout" not "asyncio.wait_for with a 10.0s ceiling"
- **DO NOT** exceed 250 words on the LinkedIn post
- **DO NOT** rehash the cleaning pipeline details (T.5 covered that), the jargon problem (T.5), dirty data (T.3), stack decision (T.2), or foundation rebuild (T.4)
- **DO NOT** use corporate buzzwords ("leverage", "synergy", "drive value", "robust")
- **DO NOT** frame this as "our system is bulletproof." Frame it as "here's what I built to handle the inevitable failures." Honest, not boastful.
- **DO** include concrete failure patterns: timeout, empty email, missing data, LLM failure fallback
- **DO** frame the challenge as "happy path demos vs production reality"
- **DO** reference T.5 in the series continuity note
- **DO** keep it under 250 words. T.1-T.5 averaged ~207-213 words. Stay in range.
- **DO** make the reader think about their own failure handling in AI systems
- **DO** frame professional domain knowledge as: "After building an AI email processing pipeline..." (no client names)

### References

- [Source: epics.md - Epic T: Build in Public, Story T.6]
- [Source: src/quote_agent/services/email_extractor.py - Extraction with timeout, error isolation, no-hallucination design]
- [Source: src/quote_agent/services/request_splitter.py - Splitting with graceful degradation, short-circuit]
- [Source: src/quote_agent/services/email_cleaner.py - Safety valve at 90% content removal]
- [Source: src/quote_agent/services/email_poller.py - Per-email error isolation, pipeline continuity]
- [Source: _bmad-output/build-in-public/template.md - Post template]
- [Source: _bmad-output/build-in-public/guidelines.md - Content guidelines]
- [Source: _bmad-output/build-in-public/t5-french-industrial-jargon-post.md - Previous post for continuity]
- [Source: _bmad-output/implementation-artifacts/t-5-french-industrial-jargon-post.md - Previous story context]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — content story, no debugging required.

### Completion Notes List

- Wrote LinkedIn post draft (203 words) covering graceful degradation patterns from Stories 2.1-2.4
- Covered: 10s timeout, per-email error isolation, no-hallucination design (None over guesses), fallback on splitting failure, 166 automated tests
- Used question option #3 from dev notes: "When you ship an AI feature, what's your plan for when the model just... doesn't work?"
- Tone: conversational, no em dashes, no "it's X not Y", tech vulgarized for non-technical readers
- Series continuity note connects T.5 (jargon) to T.6 (failure handling)
- All 3 ACs satisfied: post drafted (AC-T.6.1), covers graceful degradation/fallback/escalation (AC-T.6.2), archived in build-in-public/ (AC-T.6.3)

### Change Log

- 2026-03-19: Created t6-error-edge-cases-post.md LinkedIn draft (Task 1 complete)

### File List

- _bmad-output/build-in-public/t6-error-edge-cases-post.md (new — post draft)
