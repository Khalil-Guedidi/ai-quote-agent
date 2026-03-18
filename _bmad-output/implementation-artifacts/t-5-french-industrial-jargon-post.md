# Story T.5: French Industrial Jargon Post

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **solo developer building in public**,
I want to publish a post about the NLP challenges of French industrial emails,
So that I showcase the domain-specific complexity that generic AI tools miss.

## Acceptance Criteria

1. **AC-T.5.1:** LinkedIn post published — "Teaching an AI to read DN, Ø, lg and French industrial shorthand"
2. **AC-T.5.2:** Post includes real examples of jargon extraction (from synthetic test fixtures only)
3. **AC-T.5.3:** Post draft archived in `_bmad-output/build-in-public/`

## Tasks / Subtasks

- [x] Task 1: Write LinkedIn post draft (AC: 1, 2, 3)
  - [x] 1.1 Follow template structure from `_bmad-output/build-in-public/template.md` (hook > problem > solution > metric > open question)
  - [x] 1.2 Hook must capture the absurdity/challenge of French industrial shorthand. Angle: these abbreviations are the most important data in an email, but they look like noise to generic AI
  - [x] 1.3 Include concrete examples of French industrial jargon from the codebase's synthetic test fixtures: DN100 (Diametre Nominal), PN16 (Pression Nominale), inox 316L (stainless steel alloy), vannes papillon (butterfly valves), raccords inox (stainless fittings), boulons M12 (metric bolts)
  - [x] 1.4 Explain the core problem: an email cleaning pipeline must strip noise (signatures, disclaimers, reply threads) WITHOUT destroying the technical shorthand that carries the actual product request
  - [x] 1.5 Include a metric/proof element. Options: 18 unit tests for the cleaner, 4-stage cleaning pipeline, safety valve that preserves content if >90% would be removed, 110 total tests passing
  - [x] 1.6 End with a genuine open question about domain-specific language challenges in AI/NLP (targeting builders, engineers, people working with non-English or specialized data)
  - [x] 1.7 Run through formatting checklist from guidelines (150-250 words, English, no client names, etc.)
  - [x] 1.8 Apply tone rules: no em dashes, no "it's X, not Y" constructions, conversational/human tone, vulgarize tech for non-technical readers
  - [x] 1.9 Add series continuity note referencing T.4 (foundation recap)
  - [x] 1.10 Add 3-5 hashtags per strategy: #BuildInPublic #AI + topic-specific (e.g., #NLP #B2B #IndustrialTech)
  - [x] 1.11 Save as `_bmad-output/build-in-public/t5-french-industrial-jargon-post.md`

## Dev Notes

### Context

This is a **content story**, not a code story. Output is a markdown file. No application code, tests, or infrastructure changes. The dev agent creates files in the repo; the user manually publishes to LinkedIn.

This is post **#5** in the Build in Public series. It follows T.4 (foundation recap) and is the first post in the **Email Pipeline phase** (Epic 2). The narrative shifts from "building the foundation" to "tackling the real challenge: processing French industrial emails." This post showcases why the domain is hard and why generic AI tools aren't enough.

**Trigger:** Stories 2.1 (IMAP email reception) and 2.2 (email content cleaning) are both done.

### What Stories 2.1-2.2 Actually Built (Source of Truth)

| Story | What was built | Key tech |
|-------|---------------|----------|
| 2.1 | IMAP email reception pipeline with polling and persistence | imaplib, async polling, email record persistence |
| 2.2 | Email content cleaning with French/English pattern support | Regex-based 4-stage cleaning pipeline |

The email cleaner (`src/quote_agent/services/email_cleaner.py`) implements a **4-stage pipeline**:
1. Strip reply threads (quoted lines, reply/forward headers)
2. Strip signatures (French and English sign-offs)
3. Strip legal disclaimers
4. Normalize whitespace

**Critical design decision:** The cleaner preserves French industrial terminology (DN100, PN16, inox 316L, vannes papillon) while removing noise. The `-- ` signature delimiter (RFC 3676) is distinguished from product specs like `DN50--PN16`.

**Safety valve:** If cleaning removes >90% of content, it returns the original (normalized) to prevent over-stripping.

### French Industrial Jargon Examples (from test fixtures — SYNTHETIC DATA ONLY)

These are the actual examples from `tests/unit/test_email_cleaner.py`:

| Jargon | Meaning | Example in test |
|--------|---------|-----------------|
| DN100, DN80, DN50 | Diametre Nominal (pipe sizing) | "50 vannes papillon DN100" |
| PN16 | Pression Nominale (pressure rating) | "DN50--PN16 en acier" |
| inox 316L | Stainless steel alloy designation | "30 raccords inox 316L" |
| vannes papillon | Butterfly valves | "50 vannes papillon DN100" |
| raccords inox | Stainless steel fittings | "30 raccords inox 316L" |
| boulons M12 | Metric bolt designation | Referenced in architecture |

**The hook from AC-T.5.1 also mentions:** DN (covered), Ø (diameter symbol used in French specs), lg (longueur = length). Note: Ø and lg are mentioned in the acceptance criteria title but may not be in current test fixtures. The post can reference these as common industry shorthand without claiming they are in the code. Frame as domain knowledge: "After working on B2B industrial quoting systems..."

### Concrete Numbers to Use (Source of Truth)

| Fact | Source |
|------|--------|
| 4-stage cleaning pipeline | email_cleaner.py implementation |
| 18 unit tests for the cleaner alone | tests/unit/test_email_cleaner.py |
| 110 total automated tests | Test suite as of Story 2.2 |
| Safety valve at 90% content removal threshold | email_cleaner.py logic |
| French + English patterns supported | Bilingual regex patterns in cleaner |
| <1ms cleaning overhead per email | Inline in email_poller.py |

Pick 1-2 for the "metric/proof" section. Most compelling: 18 tests specifically for the cleaning pipeline, or the safety valve concept (if you strip too much, keep the original).

### The "French Industrial Jargon" Narrative

The core tension: generic AI/NLP tools treat industrial abbreviations as noise. But in a B2B quote request email, "50 vannes papillon DN100 en inox 316L" IS the entire request. Every abbreviation carries critical product information. Strip them and you have nothing. Miss one and you quote the wrong product.

The cleaning pipeline has to be smart about what's noise and what's signal:
- "Cordialement, Sophie Lefevre" = noise (signature) → strip it
- "DN50--PN16 en acier" = signal (product spec) → preserve it
- "Ce courriel est confidentiel" = noise (disclaimer) → strip it
- "50 vannes papillon DN100" = signal (the actual request) → preserve it

This is the kind of problem that looks simple but requires deep domain understanding. A generic email parser would destroy the data that matters most.

**Key insight for the post:** The hardest part of building an AI for a specific domain isn't the AI. It's teaching it which data matters and which doesn't. In French industrial B2B, the most important information looks like gibberish to anyone outside the industry.

### Tone Guidance

This is the first "Email Pipeline" phase post. The tone should be:
- **Curiosity-driven**: this is a fascinating domain problem
- **Example-heavy**: show the jargon, let the reader see why it's hard
- **Relatable**: anyone working with specialized domains knows this pain
- **Slightly playful**: the absurdity of "DN50--PN16 en acier" being the most important line in an email

**Specific tone rules (from user feedback):**
- NO em dashes. Use periods, commas, or restructure sentences instead.
- NO "it's X, not Y" constructions. Too formulaic.
- Vulgarize technical details. Say "18 tests just for the cleaning step" not "18 pytest unit tests across 6 test classes covering signature stripping, reply thread removal, and disclaimer detection."
- The final question targets people working with non-English data, specialized domains, or industry jargon.
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

### Previous Story Intelligence (T.4)

Story T.4 created the foundation recap LinkedIn post. Key learnings:

- **T.4 draft was 213 words.** Series is consistently hitting ~207-213 words. Keep this discipline.
- **Post structure continues to work well:** hook > problem > solution > metric > question flow.
- **T.4 ended with:** "How much of your project is the invisible work that nobody ever sees?" T.5 should NOT repeat a similar question about invisible work. The jargon post opens different territory (domain-specific language, non-English NLP challenges).
- **T.4 focused on the foundation rebuild.** T.5 should NOT rehash infrastructure or "boring work." Focus on the fascinating domain problem of French industrial shorthand.
- **T.3 already covered the dirty data problem (catalogs).** T.5 is adjacent but different: T.3 was about messy product catalogs, T.5 is about messy email content with French abbreviations. Avoid overlapping angles. T.3 = catalog data quality. T.5 = email parsing + French jargon.
- **T.2 covered stack decisions (n8n to Python/LangGraph).** Don't re-explain the tech stack.
- **Code review lesson (T.0):** Never present planned/future features as existing capabilities. For T.5: the email cleaner is real and working with 18 tests. Do NOT claim the AI understands or translates jargon yet (that's Story 2.3: structured data extraction). The cleaner preserves jargon, it doesn't interpret it.

[Source: _bmad-output/implementation-artifacts/t-4-foundation-recap-post.md]

### Git Intelligence

Recent commits confirm Stories 2.1-2.2 are complete:
- `65fbbe1` feat: add email content cleaning with French/English pattern support (Story 2.2)
- `97ff86c` feat: add IMAP email reception pipeline with polling and persistence (Story 2.1)
- `fcd7aec` docs: add Epic 1 retrospective and update sprint status
- `46d08d5` feat: add CI/CD pipeline with GitHub Actions (Story 1.8)
- `57e67a4` feat: add LinkedIn foundation recap post and Contra update (Story T.4)

Commit pattern: `feat: add <description> (Story X.Y)`

### Question Ideas (Pick One)

These are potential open questions. Choose the one that feels most natural and non-repetitive with T.1-T.4:

1. "What's the weirdest abbreviation your industry uses that outsiders would never understand?" (broad, relatable, invites engagement)
2. "If you're building AI for a specialized domain, how much time goes into teaching it the vocabulary before it can do anything useful?" (targeting AI builders)
3. "How do you handle domain-specific language in your AI pipelines? Do you build custom parsers or hope the LLM figures it out?" (targeting engineers)

Avoid: questions about invisible work (T.4 covered that), questions about data quality (T.3 covered that), questions about stack decisions (T.2 covered that), questions about quoting speed (T.1 covered that).

### Project Structure Notes

- All Build in Public content lives in `_bmad-output/build-in-public/`
- Post drafts use naming convention: `t{N}-{slug}.md` (e.g., `t5-french-industrial-jargon-post.md`)
- No conflicts with existing project structure

### Anti-Pattern Prevention

- **DO NOT** use em dashes in the LinkedIn post text
- **DO NOT** use "it's X, not Y" constructions
- **DO NOT** claim the AI "understands" or "translates" jargon. The cleaner PRESERVES it, it doesn't interpret it. Interpretation is Story 2.3.
- **DO NOT** mention any past client or employer by name
- **DO NOT** explain the regex implementation details. Vulgarize: "a cleaning pipeline that knows the difference between a signature and a product specification" not "compiled regex patterns with RFC 3676 signature detection"
- **DO NOT** exceed 250 words on the LinkedIn post
- **DO NOT** rehash the dirty data problem (T.3 covered catalog data), the stack decision (T.2), or the foundation rebuild (T.4)
- **DO NOT** use corporate buzzwords ("leverage", "synergy", "drive value")
- **DO NOT** overlap with T.3's angle. T.3 = messy catalogs. T.5 = messy emails with French abbreviations. Different problem, different angle.
- **DO** include concrete jargon examples: DN100, PN16, inox 316L, vannes papillon
- **DO** frame the challenge as "signal vs noise" in domain-specific emails
- **DO** reference T.4 in the series continuity note
- **DO** keep it under 250 words. T.1-T.4 averaged ~207-213 words. Stay in range.
- **DO** make the reader think about their own domain's jargon/abbreviations
- **DO** frame professional domain knowledge as: "After working on B2B industrial quoting systems..." (no client names)

### References

- [Source: epics.md - Epic T: Build in Public, Story T.5]
- [Source: src/quote_agent/services/email_cleaner.py - Email cleaning implementation]
- [Source: tests/unit/test_email_cleaner.py - Test fixtures with French industrial jargon examples]
- [Source: _bmad-output/build-in-public/template.md - Post template]
- [Source: _bmad-output/build-in-public/guidelines.md - Content guidelines]
- [Source: _bmad-output/build-in-public/t4-foundation-recap-post.md - Previous post for continuity]
- [Source: _bmad-output/implementation-artifacts/t-4-foundation-recap-post.md - Previous story context]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None required (content story, no code debugging).

### Completion Notes List

- Created LinkedIn post draft (210 words) following template structure: hook > problem > solution > metric > open question
- Hook opens with a real French industrial quote request ("50 vannes papillon DN100 en inox 316L") to immediately show the domain challenge
- Included concrete jargon examples: DN100, PN16, inox 316L, vannes papillon with brief explanations
- Core narrative: signal vs noise in domain-specific emails. The most important data looks like gibberish to generic parsers.
- Metrics used: 4-stage cleaning pipeline, 90% safety valve threshold, 18 tests for the cleaning step
- Open question: "What's the weirdest abbreviation your industry uses?" (broad, relatable, invites engagement from non-technical audience)
- Applied all tone rules: no em dashes in post text, no "it's X, not Y" constructions, conversational/vulgarized tech
- Series continuity note references T.4 and the transition into Email Pipeline phase
- Hashtags: #BuildInPublic #AI #NLP #B2B #IndustrialTech

### Change Log

- 2026-03-19: Created LinkedIn post draft for T.5 (French Industrial Jargon Post). Saved to `_bmad-output/build-in-public/t5-french-industrial-jargon-post.md`.
- 2026-03-19: Code review fixes — added Ø and lg jargon examples to match AC-T.5.1 scope, fixed DN50-PN16 to DN50--PN16 (double dash matches codebase test fixtures).

### File List

- `_bmad-output/build-in-public/t5-french-industrial-jargon-post.md` (NEW) — LinkedIn post draft
- `_bmad-output/implementation-artifacts/t-5-french-industrial-jargon-post.md` (MODIFIED) — Story file updated with task completion
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED) — Status updated to review
