# Story T.9: LLM Re-ranking Post

Status: done

## Story

As a **solo developer building in public**,
I want to publish a post about the search intelligence layers added on top of vector search (hybrid fusion, proposability filtering, jargon expansion),
so that I show the iterative improvement process and how production search differs from a prototype demo.

## Acceptance Criteria

1. **AC-T.9.1:** LinkedIn post published (~150-250 words) with hook inspired by: "When vector search isn't enough: adding an LLM judge"
2. **AC-T.9.2:** Post includes before/after comparison showing what changed from raw vector search to the full production search pipeline
3. **AC-T.9.3:** Post draft archived in `_bmad-output/build-in-public/t9-llm-reranking-post.md`

## Tasks / Subtasks

- [x] Task 1: Draft LinkedIn post (AC: #1, #2)
  - [x] Write hook that captures the gap between "vector search works in demo" and "production search needs more"
  - [x] Explain the problem: vector search alone misses things (jargon, non-proposable products, keyword-only matches)
  - [x] Present the 3 layers added on top of vector search: RRF hybrid fusion, proposability filtering, jargon expansion
  - [x] Include concrete metrics from Stories 3.3-3.6 (363 tests, 25 benchmark queries, sub-3s search, cache < 1s)
  - [x] End with genuine open question for the audience (non-technical friendly)
  - [x] Verify 150-250 words, 3-5 hashtags, no em dashes
- [x] Task 2: Format and archive post draft (AC: #3)
  - [x] Create `_bmad-output/build-in-public/t9-llm-reranking-post.md` using template from `_bmad-output/build-in-public/template.md`
  - [x] Fill metadata, formatting checklist, and series continuity note
- [x] Task 3: Quality review against guidelines
  - [x] Run quality checklist from `_bmad-output/build-in-public/guidelines.md`
  - [x] Verify tone rules (no em dashes, no corporate buzzwords, vulgarize tech, non-technical question)
  - [x] Verify series continuity with T.8 and position within Search phase (Epic 3)

## Dev Notes

### IMPORTANT: Actual Implementation vs. Epic Title

The epic title says "LLM Re-ranking" but **no LLM re-ranking was implemented in Stories 3.3-3.6**. The actual search improvements are:
- **Story 3.3:** RRF hybrid fusion (algorithmic, not LLM-based)
- **Story 3.4:** Proposability filter (SQL-level, config-driven rules)
- **Story 3.5:** Search result cache (PostgreSQL-backed TTL)
- **Story 3.6:** Jargon/abbreviation expansion (dictionary-based, not LLM)

The post should cover **what was actually built**, not the originally planned "LLM judge." The hook from the AC ("When vector search isn't enough: adding an LLM judge") should be adapted to reflect reality. Possible angles:
- "When vector search isn't enough: 3 layers that made it production-ready"
- "96.2% accuracy looked great in the demo. Then I pointed it at 50,000 real products."
- "Vector search found the right product. It also found 200 you can't actually sell."

### Content Source Material (from Stories 3.3-3.6)

**From Story 3.3 (Hybrid Search + RRF Fusion):**
- Reciprocal Rank Fusion combines semantic (vector) + keyword (tsvector) results
- RRF formula: `score = sum(1 / (k + rank_i))` with k=60
- French full-text search via PostgreSQL tsvector with `ts_rank_cd()` (cover density)
- Exact reference detection: regex pattern matches codes like "TUB-304L-025" and pins score=1.0
- GIN index on tsvector for keyword lookup
- 31 unit tests + 4 E2E tests, all 289 tests passing

**From Story 3.4 (Proposability Filter):**
- SQL-level WHERE clause filtering (not post-fetch Python)
- Excludes inactive + out-of-stock products BEFORE search results are returned
- Config-driven: `PROPOSABILITY__EXCLUDE_OUT_OF_STOCK=true` env vars
- Optional bypass with `is_proposable` flag on each result
- Test fixture distribution: 62 in_stock, 27 on_order, 11 out_of_stock, 3 inactive
- 27 unit tests + 3 E2E tests, 0 regressions

**From Story 3.5 (Search Cache):**
- PostgreSQL-only cache (no Redis), JSONB columns
- SHA-256 cache key from (query, limit, filter settings)
- Default TTL: 1 hour, max 10K entries
- Cache hit < 1 second (NFR-P6 target)
- Auto-invalidated on catalog re-sync
- 23 unit tests + 3 E2E tests, all 339 tests passing

**From Story 3.6 (Jargon Matching):**
- Config-driven abbreviation dictionary (10 default entries)
- Expands: inox→acier inoxydable stainless steel, Ø→diamètre diameter, DN→diamètre nominal, etc.
- Additive expansion (original query tokens preserved)
- Case-insensitive word-boundary matching, skips abbreviations inside reference codes
- 25-query benchmark across 6 categories: abbreviations, jargon, exact refs, cross-language, unit variations
- Benchmark pass rate threshold: ≥ 80% (MVP target)
- 23 unit tests + 5 E2E tests (4 functional + 1 benchmark), all 363 tests passing

### Metrics Available for the Post

| Metric | Value | Source |
|--------|-------|--------|
| Prototype accuracy | 96.2% Hit@5 on 680 products | Epic 0 |
| Production catalog scale | 50,000 products | Story 3.0c |
| Search latency | Sub-3 seconds on 50K products | NFR-P2 |
| Cache hit time | < 1 second | Story 3.5, NFR-P6 |
| Jargon benchmark | 25 queries, ≥80% pass rate | Story 3.6 |
| Default abbreviations | 10 expansion entries | Story 3.6 |
| Total unit tests | 363 passing | Story 3.6 completion |
| E2E tests | 15+ passing | Stories 3.3-3.6 |
| Infrastructure | Zero external services (all PostgreSQL) | Architecture decision |

### Before/After Comparison (AC-T.9.2)

**Before (raw vector search, Story 3.2 only):**
- Semantic search only (BGE-M3 embeddings + pgvector HNSW)
- No keyword fallback: "TUB-304L-025" found by meaning only, not by exact code
- No filtering: out-of-stock and inactive products returned in results
- No jargon handling: "inox DN100" not expanded to "acier inoxydable diamètre nominal 100"
- No caching: every identical query re-computed
- Search on 50K products, single signal

**After (full production search pipeline, Stories 3.3-3.6):**
- Hybrid search: vector + keyword + RRF fusion (3 signals)
- Exact reference detection with pinned score=1.0
- Proposability filter at SQL level (only sellable products)
- Jargon expansion with 10 abbreviation mappings
- PostgreSQL-backed cache with 1-hour TTL
- 363 unit tests + 15+ E2E tests

### Tone & Voice Rules (CRITICAL)

From `_bmad-output/build-in-public/guidelines.md` and feedback memory:

1. **NO em dashes** (use commas, periods, or parentheses instead)
2. **NO "it's X, not Y" constructions**
3. **Vulgarize tech**: say "50,000 products" not "50K references indexed in pgvector HNSW". Say "combining two search methods" not "Reciprocal Rank Fusion of semantic and keyword signals"
4. **First person, conversational**, like explaining over coffee
5. **Authentic, not corporate**: no "leverage," "synergies," "drive value"
6. **Short sentences** preferred
7. **Problem-first approach**: lead with the challenge, not the solution
8. **Non-technical final question**: target audience includes B2B decision-makers and managers, not just engineers

### Post Structure (Non-Negotiable from guidelines.md)

1. **Hook** (1-2 sentences): Surprising result, counterintuitive finding, or question
2. **Problem** (2-3 sentences): Real B2B industrial challenge
3. **Solution/Insight** (3-5 sentences): What you built, technical but accessible
4. **Metric/Proof** (1-2 sentences): Concrete number(s)
5. **Open Question/CTA** (1-2 sentences): Genuine question, not a sales pitch
6. **Hashtags**: 3-5 max. Core: #BuildInPublic #AI. Rotate topic-specific.

### Series Continuity

- **Previous post (T.8):** Search deep dive. Hook: "96.2% accuracy on 680 products. Will it hold on 50,000?" Covered the foundation: vector embeddings + pgvector + hybrid search plan. Ended with: "Have you tried vector search on messy, multilingual product data? What surprised you?"
- **T.8 set up the foundation**. T.9 should answer "and then what?" by showing the layers added on top of that foundation.
- **Next planned post (T.10):** Search Recap Post (after Epic 3 completion). T.10 will consolidate the entire search narrative. T.9 should focus on the "iterative improvement" angle, leaving the wrap-up for T.10.
- **Narrative arc**: T.8 = "Can it scale?" → T.9 = "Making it production-ready" → T.10 = "The full search story"
- All previous posts land between 207-228 words. Target ~210 words.

### What NOT to Do

- Do NOT repeat T.8's angle (hybrid search architecture overview already covered)
- Do NOT repeat T.5's angle (French jargon challenge already covered in depth)
- Do NOT repeat T.3's angle (dirty data problem already covered)
- Do NOT claim "LLM re-ranking" if it wasn't implemented. Be honest about what was built.
- Do NOT mention past clients by name or share confidential information
- Do NOT use data from outside this repo (synthetic data and benchmarks only)
- Do NOT frame as a tutorial. Frame as a build journal sharing real decisions.
- Do NOT oversell. Be honest about what the benchmark measures and its limitations.
- Do NOT use "LLM judge" framing if no LLM step exists in the search pipeline

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

### File Output Locations

- Post draft: `_bmad-output/build-in-public/t9-llm-reranking-post.md`
- Use template from: `_bmad-output/build-in-public/template.md`

### Project Structure Notes

- Build-in-public drafts go in `_bmad-output/build-in-public/`
- This is a content story, not a code story. No source code changes required.
- The story file itself lives in `_bmad-output/implementation-artifacts/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story T.9] — AC and story definition
- [Source: _bmad-output/build-in-public/guidelines.md] — Tone, structure, quality checklist
- [Source: _bmad-output/build-in-public/template.md] — Post draft template
- [Source: _bmad-output/build-in-public/t8-search-deep-dive.md] — Previous post (series continuity)
- [Source: _bmad-output/implementation-artifacts/3-3-recherche-hybride-semantique-mot-cle.md] — Hybrid search technical details
- [Source: _bmad-output/implementation-artifacts/3-4-filtre-de-proposabilite.md] — Proposability filter details
- [Source: _bmad-output/implementation-artifacts/3-5-cache-de-resultats-de-recherche.md] — Cache implementation details
- [Source: _bmad-output/implementation-artifacts/3-6-matching-terminologie-client-jargon.md] — Jargon matching details
- [Source: _bmad-output/planning-artifacts/architecture.md] — Search architecture decisions
- [Source: docs/project-context.md] — Project patterns and conventions
- [Source: .claude/projects/-home-khalil-PycharmProjects-ai-quote-agent/memory/feedback_build_in_public_tone.md] — Tone feedback rules

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — content story, no code debugging required.

### Completion Notes List

- Drafted LinkedIn post (214 words) with hook: "Vector search found the right product. It also found 200 you can't actually sell."
- Post covers the 3 layers added on top of vector search (hybrid fusion, proposability filter, jargon expansion) — all vulgarized for non-technical audience
- Before/after comparison implicit through narrative: from T.8's single vector search to 3-layer production pipeline
- Metrics included: 363 tests, sub-3s search on 50K products, <1s cache
- Honest framing: no LLM re-ranking claims, only what was actually built (algorithmic/config-driven layers)
- Non-technical closing question targets B2B decision-makers
- Series continuity: references T.8 ("last post"), sets up T.10 recap
- All tone rules verified: no em dashes, no corporate buzzwords, no "it's X not Y" constructions

### Change Log

- 2026-03-20: Created post draft `_bmad-output/build-in-public/t9-llm-reranking-post.md` (214 words, all ACs satisfied)

### File List

- `_bmad-output/build-in-public/t9-llm-reranking-post.md` (NEW) — LinkedIn post draft
- `_bmad-output/implementation-artifacts/t-9-llm-reranking-post.md` (NEW) — Story file with completion record
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED) — Status updated to review
