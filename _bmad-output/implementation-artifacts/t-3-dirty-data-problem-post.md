# Story T.3: Dirty Data Problem Post

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **solo developer building in public**,
I want to publish a post about the real challenge of industrial product catalogs,
So that I highlight the core problem that makes this project technically interesting.

## Acceptance Criteria

1. **AC-T.3.1:** LinkedIn post published — "The ugly truth about industrial product catalogs"
2. **AC-T.3.2:** Post includes anonymized examples of catalog noise (from synthetic data only)
3. **AC-T.3.3:** Post draft archived in `_bmad-output/build-in-public/`

## Tasks / Subtasks

- [x] Task 1: Write LinkedIn post draft (AC: 1, 2, 3)
  - [x] 1.1 Follow template structure from `_bmad-output/build-in-public/template.md` (hook > problem > solution > metric > open question)
  - [x] 1.2 Hook must highlight the "dirty data" problem. The surprise angle: everyone talks about AI models, nobody talks about the data they have to work with
  - [x] 1.3 Include 2-3 concrete examples of catalog noise (synthetic only). Think: abbreviated product names, inconsistent units, missing descriptions, mixed languages, industrial shorthand
  - [x] 1.4 Cover the core insight: most AI tools require clean data, this project's bet is working with messy catalogs as-is ("zero preprocessing")
  - [x] 1.5 Include at least one concrete metric or comparison point from the prototype (96.2% accuracy on a raw, uncleaned 680-product catalog)
  - [x] 1.6 End with a genuine open question targeting non-technical audience (B2B managers, sales directors) about their catalog data quality
  - [x] 1.7 Run through formatting checklist from guidelines (150-250 words, English, no client names, etc.)
  - [x] 1.8 Apply tone rules: no em dashes, no "it's X, not Y" constructions, conversational/human tone, vulgarize tech for non-technical readers
  - [x] 1.9 Add series continuity note referencing T.2 (stack decision)
  - [x] 1.10 Add 3-5 hashtags per strategy: #BuildInPublic #AI + topic-specific (e.g., #B2B #Data #IndustrialTech)
  - [x] 1.11 Save as `_bmad-output/build-in-public/t3-dirty-data-problem-post.md`

## Dev Notes

### Context

This is a **content story**, not a code story. Output is a markdown file. No application code, tests, or infrastructure changes. The dev agent creates the file in the repo; the user manually publishes to LinkedIn.

This is post **#3** in the Build in Public series. It follows T.2 (stack decision) and is tied to the completion of Stories 1.5 (ERP + email adapters) and 1.6 (notification adapter). The narrative angle: now that the foundation is laid, let's talk about the real challenge. The hard part isn't the code. It's the data.

### The "Dirty Data" Problem: Key Talking Points

These are the specific pain points around industrial product catalogs. Use as source material. Pick the 2-3 most compelling for LinkedIn.

**What makes industrial catalogs "dirty":**

| Problem | Example (synthetic) | Why it matters |
|---------|-------------------|----------------|
| Abbreviated product names | "VIS CHC M8X40 INOX A2" instead of "Vis a tete cylindrique hexagonale creux M8x40 acier inoxydable A2" | Human sales reps decode these instantly, AI needs to learn the mapping |
| Mixed languages in same catalog | French labels, English specs, German brand names in one row | Standard NLP tools assume one language per document |
| Inconsistent units/formatting | "DN 25", "DN25", "1 pouce", "1\"", "25mm" all mean the same thing | Simple keyword search fails, need semantic understanding |
| Missing or useless descriptions | Description field: "-" or copy of the product name | Can't rely on description field for search context |
| Industrial jargon and shorthand | "Bride PN16 DN50" = flange, pressure nominal 16 bar, diameter nominal 50mm | Domain expertise required to parse |
| Obsolete/duplicate references | Same product with 3 different reference codes across catalog updates | Search returns duplicates, confuses confidence scoring |

**The core insight (from PRD and architecture):**

The #1 differentiator of this project is the "zero preprocessing" promise: the system works with raw, uncleaned product catalogs out of the box. Most competing solutions (CPQ tools, traditional search engines) require weeks or months of data cleanup, catalog structuring, and IT projects before delivering any value. This project's bet is that intelligent representation (vector embeddings + hybrid search) can adapt to the data instead of requiring the data to adapt to the tool.

**Prototype validation:**

The n8n prototype already validated this on a 680-product synthetic catalog with intentionally messy data:
- 96.2% accuracy on raw, uncleaned catalog data
- Hybrid search (dense vectors + sparse keyword matching) handles abbreviations and jargon
- No manual data cleanup was performed before testing

**v1 lesson (frame as domain expertise, never mention client names):**

"After working on B2B industrial quoting systems professionally, the #1 frustration was always the same: weeks spent manually cleaning product databases just to make search work." [Source: PRD executive summary]

### Tone Guidance

The post should convey genuine frustration with the "dirty data" problem that anyone in industrial B2B will recognize. This is the "I see you, I've been there" post. The technical angle (vector embeddings, hybrid search) is mentioned briefly as the solution, but the emphasis is on the problem and why it's harder than people think.

**Specific tone rules (from user feedback):**
- NO em dashes. Use periods, commas, or restructure sentences instead.
- NO "it's X, not Y" constructions. Too formulaic.
- Vulgarize technical details. Say "the AI understands what the product actually is, even when the label is gibberish" not "dense vector embeddings create semantic representations in high-dimensional space."
- The final question targets non-technical readers: sales directors, operations managers, B2B decision-makers.
- Write like you're explaining this to someone over coffee. First person, short sentences, conversational.

### Concrete Numbers to Use (Source of Truth)

| Fact | Source |
|------|--------|
| 96.2% accuracy on raw, uncleaned 680-product catalog | Prototype results (Epic 0) |
| System works with "zero preprocessing" on dirty catalogs | PRD USP, architecture decision |
| Hybrid search: vector embeddings + keyword matching | architecture.md |
| 680 synthetic products with intentionally messy data | Prototype test catalog |
| 5 adapter systems now wired up (DB, LLM, ERP, email, notification) | Stories 1.1-1.6 completion |

Pick 1-2 for the "metric/proof" section. The most compelling: 96.2% accuracy achieved on data that was intentionally left dirty.

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

### Previous Story Intelligence (T.2)

Story T.2 created the stack decision LinkedIn post. Key learnings:

- **T.2 draft was well-calibrated at 209 words.** The concise approach worked. Aim for similar length.
- **Post structure worked well:** hook > problem > solution > metric > question flow was natural.
- **T.1 initial draft was too long (376 words)** then T.2 got it right. Keep this discipline.
- **T.2 ended with:** "At what point do you decide to stop iterating on something that works 'well enough' and start fresh with the right foundations?" T.3 should NOT repeat a similar question. The dirty data angle opens different territory.
- **T.2 already covered the stack pivot (n8n to Python/LangGraph).** T.3 should NOT rehash the stack decision. Focus purely on the data problem.
- **T.2 mentioned "21 automated tests and a clean project structure."** T.3 can reference having the foundation in place, but the focus is on data, not infrastructure.
- **Code review lesson (T.0):** Never present planned/future features as existing capabilities. For T.3: the 96.2% accuracy is from the prototype on 680 products. Do NOT claim production accuracy or full catalog scale performance.

[Source: _bmad-output/implementation-artifacts/t-2-stack-decision-post.md]

### Git Intelligence

Recent commits confirm Stories 1.5 and 1.6 are complete:
- `c6c8ea1` feat: add Teams notification adapter with webhook health check (Story 1.6)
- `4a6b980` feat: add ERP and email adapter configuration with health checks (Story 1.5)

Earlier in Epic 1:
- `c3b1a5c` feat: add LLM provider adapter with OpenAI-compatible interface (Story 1.4)
- `98cc075` feat: add FastAPI server with health check and API v1 base endpoint (Story 1.3)

The foundation is now 6 stories deep. The ERP adapter (Odoo XML-RPC) and email adapter (IMAP) are wired up. This is relevant context: the system can now connect to the data source (ERP) where catalogs live. The next epics will actually ingest and search that catalog data. T.3 sets the stage for why that's hard.

### Project Structure Notes

- All Build in Public content lives in `_bmad-output/build-in-public/`
- Post drafts use naming convention: `t{N}-{slug}.md` (e.g., `t3-dirty-data-problem-post.md`)
- No conflicts with existing project structure

### Anti-Pattern Prevention

- **DO NOT** use em dashes in the LinkedIn post text
- **DO NOT** use "it's X, not Y" constructions
- **DO NOT** present future features as existing (96.2% is prototype accuracy on 680 products, not production performance)
- **DO NOT** mention any past client or employer by name. Frame as "After working on B2B quoting systems..."
- **DO NOT** explain vector embeddings or hybrid search in technical depth. Vulgarize: "the AI understands what the product actually is"
- **DO NOT** exceed 250 words on the LinkedIn post
- **DO NOT** rehash the stack decision (T.2 covered that)
- **DO NOT** use corporate buzzwords ("leverage", "synergy", "drive value", "unlock potential")
- **DO NOT** make the question too technical. Target: sales directors and operations managers
- **DO** include 2-3 concrete examples of catalog messiness (synthetic data only)
- **DO** reference the prototype accuracy as proof the approach works
- **DO** frame professional experience as domain expertise, not client work
- **DO** reference T.2 in the series continuity note
- **DO** keep it under 250 words. Start concise, T.2 proved this works.
- **DO** make the reader feel understood. This is a "I know your pain" post.

### References

- [Source: epics.md - Epic T: Build in Public, Story T.3]
- [Source: _bmad-output/build-in-public/template.md - Post template]
- [Source: _bmad-output/build-in-public/guidelines.md - Content guidelines]
- [Source: _bmad-output/build-in-public/t2-stack-decision-post.md - Previous post for continuity]
- [Source: _bmad-output/implementation-artifacts/t-2-stack-decision-post.md - Previous story context]
- [Source: _bmad-output/implementation-artifacts/1-5-configuration-connexions-erp-email.md - Story 1.5 (ERP/email adapters)]
- [Source: _bmad-output/implementation-artifacts/1-6-configuration-canal-de-notification.md - Story 1.6 (notification adapter)]
- [Source: prd.md - Executive Summary, "zero preprocessing" USP, FR5, FR9]
- [Source: architecture.md - Hybrid search, zero-preprocessing ingestion, vector embeddings]
- [Source: epics.md - Epic 3: Catalogue Produits & Recherche Intelligente]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — content story, no debugging required.

### Completion Notes List

- Post drafted at 206 words (within 150-250 target, calibrated to T.2's 207 words)
- Three concrete catalog noise examples used: abbreviated product names ("VIS CHC M8X40 INOX A2"), mixed languages (French/English/German in same catalog), inconsistent units ("DN 25"/"DN25"/"1 pouce"/"25mm")
- Core insight clearly stated: AI adapts to messy data vs. requiring data cleanup
- 96.2% prototype accuracy on 680-product dirty catalog cited as proof point
- Open question targets non-technical audience (product data quality + maintenance time)
- No em dashes, no "it's X, not Y", no client names, no corporate buzzwords
- Series continuity note connects T.2 (stack decision) to T.3 (data problem)
- All 3 ACs satisfied: post written (AC-T.3.1), includes anonymized catalog examples (AC-T.3.2), archived in build-in-public folder (AC-T.3.3)

### Change Log

- 2026-03-18: Created LinkedIn post draft `_bmad-output/build-in-public/t3-dirty-data-problem-post.md` (206 words)

### File List

- `_bmad-output/build-in-public/t3-dirty-data-problem-post.md` (new) — LinkedIn post draft
- `_bmad-output/implementation-artifacts/t-3-dirty-data-problem-post.md` (modified) — Story file updated
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) — Status updated to review
