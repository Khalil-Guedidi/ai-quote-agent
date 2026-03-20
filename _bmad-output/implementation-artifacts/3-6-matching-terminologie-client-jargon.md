# Story 3.6: Matching Terminologie Client & Jargon

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to match client-specific terminology, abbreviations, and industry jargon to catalog products,
So that it understands requests the way a human sales rep would — without needing manual synonym configuration.

## Acceptance Criteria

1. **AC-1: Industry abbreviations resolved through semantic understanding**
   - Given a search query uses abbreviations common in the industry (e.g., "inox" for "acier inoxydable", "Ø" for diameter, "lg" for longueur, "DN100" for nominal diameter)
   - When the search runs
   - Then the agent resolves these through semantic understanding and returns correct products
   - And results are returned within 3 seconds (NFR-P2)

2. **AC-2: Client nicknames matched semantically with confidence signal**
   - Given a client uses their own product nicknames or internal references
   - When the search runs
   - Then semantic matching attempts to resolve against catalog descriptions and metadata
   - And if uncertain, this is reflected in the confidence score (not silently guessed)
   - And `jargon_expanded` metadata in SearchResult indicates whether query expansion occurred

3. **AC-3: Cross-language matching (French/English mix)**
   - Given the system operates primarily in French
   - When requests mix French and technical English terms (e.g., "stainless steel DN100" or "butterfly valve inox")
   - Then the multilingual embedding model (BGE-M3) handles cross-language matching correctly
   - And results are equivalent to searching with the French-only equivalent

4. **AC-4: Query expansion for known industrial abbreviations**
   - Given a configurable abbreviation expansion dictionary (config-driven, not hardcoded)
   - When a search query contains known abbreviations (e.g., "inox", "Ø", "lg", "DN", "PN")
   - Then the query is expanded with the full form appended (e.g., "inox" → "inox acier inoxydable")
   - And the original query is preserved (expansion is additive, not replacement)
   - And expansion is logged with component `search.jargon`

5. **AC-5: Query expansion can be disabled via configuration**
   - Given `JargonSettings.expansion_enabled=False` (env: `JARGON__EXPANSION_ENABLED=false`)
   - When a search is executed
   - Then no query expansion occurs
   - And search behaves exactly as before this story

6. **AC-6: Jargon benchmark test suite passes**
   - Given a test suite of 20+ realistic product queries covering: abbreviations, jargon, typos, exact references, French/English mix, client nicknames
   - When run against the 50K catalog with embeddings
   - Then the expected product appears in the top-5 results for at least 80% of queries
   - And results are documented with pass/fail per query for future regression tracking

7. **AC-7: E2E test with real PostgreSQL and embedding model**
   - Given products are ingested and embedded from the 50K catalog sample
   - When search runs with jargon-heavy queries (e.g., "tubes inox 304L Ø25 lg 6m")
   - Then the correct product appears in results
   - And with expansion enabled, the expanded query improves or maintains result quality
   - And with expansion disabled, semantic search still handles common jargon

## Tasks / Subtasks

- [x] Task 1: Add `JargonSettings` to configuration (AC: 4, 5)
  - [x] 1.1: Add `JargonSettings` to `config.py`: `expansion_enabled` (bool, default `True`), `abbreviations` (dict[str, str], default industrial abbreviations)
  - [x] 1.2: Add `jargon: JargonSettings` field to `Settings`
  - [x] 1.3: Verify env var mapping: `JARGON__EXPANSION_ENABLED`
  - [x] 1.4: Default abbreviation dict — common French industrial abbreviations:
    ```python
    {
        "inox": "acier inoxydable stainless steel",
        "Ø": "diamètre diameter",
        "lg": "longueur length",
        "DN": "diamètre nominal nominal diameter",
        "PN": "pression nominale nominal pressure",
        "HM": "hexagonal mâle",
        "BLN": "boulon bolt",
        "RD": "rond round",
        "TB": "tube",
        "ml": "mètres linéaires linear meters",
    }
    ```

- [x] Task 2: Implement query expansion in `search/jargon.py` (AC: 1, 4, 5)
  - [x] 2.1: Create `src/quote_agent/search/jargon.py` with `expand_query(query: str, abbreviations: dict[str, str]) -> JargonExpansionResult`
  - [x] 2.2: `JargonExpansionResult` dataclass: `original_query: str`, `expanded_query: str`, `expansions_applied: list[str]`, `was_expanded: bool`
  - [x] 2.3: Expansion logic — case-insensitive word boundary matching: for each abbreviation found in the query, append the expansion to the end of the query. Original query tokens are never replaced or removed.
  - [x] 2.4: Handle edge cases: abbreviation inside a product reference (e.g., "REF-DN100") should NOT be expanded; "Ø" as a standalone Unicode character; "lg" should not match "lg" inside longer words like "belonging"
  - [x] 2.5: Structured logging: component `search.jargon`, log expansions applied with original and expanded query

- [x] Task 3: Add `jargon_expanded` metadata to SearchResult (AC: 2)
  - [x] 3.1: Add `jargon_expanded: bool = False` field to `SearchResult` in `models.py`
  - [x] 3.2: Add `expanded_query: str | None = None` field to `SearchResult` for debugging/transparency

- [x] Task 4: Integrate jargon expansion into SearchEngine (AC: 1, 2, 3, 4, 5)
  - [x] 4.1: In `SearchEngine.__init__`, read `get_settings().jargon` to get expansion config
  - [x] 4.2: In `search_hybrid()`: before embedding generation, apply `expand_query()` if enabled. Use expanded query for embedding AND keyword search. Keep original query for cache key computation (cache is query-specific, expansion is transparent).
  - [x] 4.3: Same pattern for `search_semantic_only()` and `search_keyword_only()`
  - [x] 4.4: Set `result.jargon_expanded` and `result.expanded_query` on the SearchResult
  - [x] 4.5: When `expansion_enabled=False`, skip expansion entirely (no function call, no metadata set)
  - [x] 4.6: IMPORTANT — cache key must use the ORIGINAL query (pre-expansion), not the expanded query. This ensures cache consistency: same user query = same cache key, regardless of expansion config changes.

- [x] Task 5: Create jargon benchmark test fixture (AC: 6)
  - [x] 5.1: Create `tests/e2e/fixtures/jargon_benchmark.json` — JSON array of test cases
  - [x] 5.2: Include 25 test cases covering: abbreviations (inox, Ø, lg, DN, PN, TB, RD), jargon (vannes papillon, raccords, clapets), exact references, French/English mix (stainless steel + DN100), unit variations
  - [x] 5.3: Expected match is validated by checking if ANY of the `expected_match_keywords` appear in the top-5 result product names/descriptions/references

- [x] Task 6: Unit tests (AC: 1, 2, 4, 5, 6)
  - [x] 6.1: Test `expand_query()` with known abbreviation → correct expansion appended
  - [x] 6.2: Test `expand_query()` preserves original query tokens (additive only)
  - [x] 6.3: Test `expand_query()` with no abbreviations found → returns original unchanged, `was_expanded=False`
  - [x] 6.4: Test `expand_query()` case-insensitive matching ("INOX" and "inox" both expand)
  - [x] 6.5: Test `expand_query()` does NOT expand abbreviations inside reference codes
  - [x] 6.6: Test `expand_query()` handles "Ø" Unicode character correctly
  - [x] 6.7: Test `expand_query()` word boundary: "lg" in "belonging" NOT expanded
  - [x] 6.8: Test `expand_query()` multiple abbreviations in single query
  - [x] 6.9: Test `JargonSettings` defaults and env overrides
  - [x] 6.10: Test SearchEngine integration: mock jargon expansion, verify expanded query sent to embedding and keyword
  - [x] 6.11: Test SearchEngine with `expansion_enabled=False`: verify no expansion occurs
  - [x] 6.12: Test `jargon_expanded` and `expanded_query` metadata set correctly on SearchResult
  - [x] 6.13: Test cache key uses ORIGINAL query, not expanded query
  - [x] 6.14: Test naming: `test_{behavior}_when_{condition}()`, docstrings: `"""AC-{#}: ..."""`

- [x] Task 7: E2E test with real PostgreSQL and embedding model (AC: 7)
  - [x] 7.1: Insert products from `catalog_50k_sample.jsonl`, generate embeddings
  - [x] 7.2: Search with jargon query (e.g., "tubes inox 304L Ø25 lg 6m") → verify relevant products returned
  - [x] 7.3: Search with expansion enabled → verify `jargon_expanded=True` and `expanded_query` set
  - [x] 7.4: Search with expansion disabled → verify `jargon_expanded=False` and semantic search still finds relevant products
  - [x] 7.5: Search with French/English mix → verify cross-language matching works
  - [x] 7.6: Mark with `@pytest.mark.e2e`, use `@requires_e2e` skip decorator
  - [x] 7.7: Cleanup: delete test products after tests

- [x] Task 8: Jargon benchmark E2E (AC: 6)
  - [x] 8.1: Load benchmark fixture, run each query, check top-5 results against expected keywords
  - [x] 8.2: Report pass/fail count and per-query results via structured logging
  - [x] 8.3: Assert >= 80% pass rate (threshold for MVP — will improve with future tuning)
  - [x] 8.4: Mark with `@pytest.mark.e2e` and `@pytest.mark.benchmark` (separate marker for long-running benchmarks)

## Dev Notes

### Critical: Architecture Compliance

**Jargon expansion is search-internal** — it lives in `search/jargon.py`, NOT as an adapter with Protocol/factory/@lru_cache pattern. Same rationale as cache, proposability filter (Stories 3.4, 3.5). Query expansion is an implementation detail of the search layer.

**No synonym database or external dictionary** — architecture decision: semantic understanding via BGE-M3 handles jargon natively. Query expansion is a lightweight enhancement layer, NOT a replacement for semantic search. The expansion just gives the embedding model more context.

**Expansion is additive, not replacement** — "inox 304L" becomes "inox 304L acier inoxydable stainless steel" — the original tokens are always preserved. This ensures keyword search still matches the original terms.

**Cache key uses ORIGINAL query** — this is critical. If expansion config changes (e.g., new abbreviation added), we don't want to invalidate the entire cache. The cache key is based on what the user typed, not what the system expanded.

### Technical Requirements

**JargonSettings configuration:**
```python
class JargonSettings(BaseModel):
    """Query expansion settings for industrial jargon."""
    expansion_enabled: bool = True
    abbreviations: dict[str, str] = {
        "inox": "acier inoxydable stainless steel",
        "Ø": "diamètre diameter",
        "lg": "longueur length",
        "DN": "diamètre nominal nominal diameter",
        "PN": "pression nominale nominal pressure",
        "HM": "hexagonal mâle",
        "BLN": "boulon bolt",
        "RD": "rond round",
        "TB": "tube",
        "ml": "mètres linéaires linear meters",
    }
```
- Env vars: `JARGON__EXPANSION_ENABLED=true`
- Abbreviations can be extended via config but default dict covers 80% of industrial French

**JargonExpansionResult DTO:**
```python
@dataclass(frozen=True)
class JargonExpansionResult:
    original_query: str
    expanded_query: str
    expansions_applied: list[str]  # e.g., ["inox → acier inoxydable stainless steel"]
    was_expanded: bool
```

**Query expansion logic:**
```python
import re

def expand_query(query: str, abbreviations: dict[str, str]) -> JargonExpansionResult:
    expansions = []
    extra_terms = []
    for abbrev, full_form in abbreviations.items():
        # Word boundary match, case-insensitive, NOT inside reference codes
        pattern = rf"(?<![A-Z0-9_-])\b{re.escape(abbrev)}\b(?![A-Z0-9_-])"
        if re.search(pattern, query, re.IGNORECASE):
            extra_terms.append(full_form)
            expansions.append(f"{abbrev} → {full_form}")

    if not expansions:
        return JargonExpansionResult(query, query, [], False)

    expanded = f"{query} {' '.join(extra_terms)}"
    return JargonExpansionResult(query, expanded, expansions, True)
```

**Integration in SearchEngine:**
```python
# In search_hybrid():
query = request.query.strip()
jargon_expanded = False
expanded_query = None

if self._jargon_enabled:
    expansion = expand_query(query, self._jargon_abbreviations)
    if expansion.was_expanded:
        query = expansion.expanded_query
        jargon_expanded = True
        expanded_query = expansion.expanded_query
        logger.info("Query expanded", extra={"context": {
            "original": expansion.original_query,
            "expanded": expansion.expanded_query,
            "expansions": expansion.expansions_applied,
        }})

# Cache key still uses request.query (original)
if self._cache_enabled:
    cache_key = compute_cache_key(request)  # Uses request.query, NOT expanded
    ...

# Embedding uses expanded query
embeddings = await self._embedding.embed_texts([query])
```

### Architecture Compliance

**File structure:**
```
src/quote_agent/search/
├── __init__.py         # No changes needed
├── engine.py           # Update: add jargon expansion before embedding/keyword
├── jargon.py           # NEW: expand_query(), JargonExpansionResult
├── models.py           # Update: add jargon_expanded, expanded_query to SearchResult
├── cache.py            # No changes
├── vector.py           # No changes
├── keyword.py          # No changes
└── proposability.py    # No changes

src/quote_agent/
├── config.py           # Update: add JargonSettings + field on Settings
└── ...

tests/unit/
├── test_search_jargon.py  # NEW: unit tests for query expansion
└── ...

tests/e2e/
├── test_search_jargon_e2e.py  # NEW: E2E tests
├── fixtures/
│   └── jargon_benchmark.json  # NEW: benchmark test cases
└── ...
```

**Naming conventions (PEP 8 strict):**
- File: `jargon.py`
- Functions: `expand_query()`
- Classes: `JargonSettings`, `JargonExpansionResult`
- Env prefix: `JARGON__`

**Imports:** Absolute only — `from quote_agent.search.jargon import expand_query`

**Type safety:** `from __future__ import annotations` in every file. All functions typed. `mypy --strict` must pass.

**Structured logging:**
```python
logger.info("Query expanded", extra={"context": {
    "original": "tubes inox 304L Ø25 lg 6m",
    "expanded": "tubes inox 304L Ø25 lg 6m acier inoxydable stainless steel diamètre diameter longueur length",
    "expansions_count": 3,
}})
```
Component: `search.jargon`. Never `print()`.

### Library & Framework Requirements

**No new dependencies.** `re` (stdlib), Pydantic, dataclasses all already available. BGE-M3 multilingual model already handles cross-language matching natively.

### File Structure Requirements

**New files:**
- `src/quote_agent/search/jargon.py` — query expansion logic
- `tests/unit/test_search_jargon.py` — unit tests
- `tests/e2e/test_search_jargon_e2e.py` — E2E tests
- `tests/e2e/fixtures/jargon_benchmark.json` — benchmark test fixture

**Modified files:**
- `src/quote_agent/config.py` — add `JargonSettings` class and `jargon` field on `Settings`
- `src/quote_agent/search/models.py` — add `jargon_expanded` and `expanded_query` to `SearchResult`
- `src/quote_agent/search/engine.py` — integrate jargon expansion before embedding/keyword search

### Testing Requirements

**Unit tests (no DB, no real model):**
- Test `expand_query()` expansion logic: determinism, case-insensitivity, word boundaries, Unicode (Ø), reference code protection
- Test `JargonSettings` defaults and env overrides
- Mock jargon expansion in SearchEngine integration tests
- Test `jargon_expanded` and `expanded_query` metadata correctness
- Test `expansion_enabled=False` skips all expansion
- Test cache key unaffected by expansion
- Test naming: `test_{behavior}_when_{condition}()` e.g., `test_expansion_applies_when_abbreviation_found()`
- Docstrings: `"""AC-{#}: ..."""`

**E2E tests (real PostgreSQL + real embedding model):**
- Mark with `@pytest.mark.e2e`
- Use `@requires_e2e` skip decorator
- Insert products from `catalog_50k_sample.jsonl`, embed with real BGE-M3
- Test jargon-heavy queries return relevant products
- Test expansion enabled vs disabled
- Test cross-language matching (French/English mix)
- Benchmark: 20+ queries, >= 80% pass rate for top-5 matching

### Previous Story Intelligence

**Story 3.5 (Cache — just completed):**
- Cache at SearchEngine level wraps complete search result
- `compute_cache_key()` uses SHA-256 of (query, limit, include_stale, apply_proposability_filter) — CRITICAL: jargon expansion must NOT change the cache key
- Cache integration in `__init__`: reads `get_settings().search_cache`
- All 339 unit tests passing. No regressions.

**Story 3.4 (Proposability Filter):**
- `apply_proposability_filter` is a SearchRequest field, part of cache key
- SQL-level filtering with config-driven rules

**Story 3.3 (Hybrid Search):**
- `SearchEngine` takes `(session, embedding_adapter)` in constructor
- Three search methods: `search_hybrid()`, `search_semantic_only()`, `search_keyword_only()`
- Keyword search uses `plainto_tsquery('french', query_text)` — expanded query benefits both semantic AND keyword search
- `is_reference_code()` regex: `r"^[A-Z]{2,6}[-_][A-Z0-9.²]+(?:[-_][A-Z0-9.²x]+)*$"` — if query IS a reference code, skip expansion entirely (fast path)
- RRF fusion with k=60

**Story 3.2 (Embeddings):**
- BGE-M3 model with 1024-dim embeddings, multilingual, handles French natively
- E2E pattern: insert from `catalog_50k_sample.jsonl`, use `e2e_db_session` fixture

### Git Intelligence

Recent commits:
- `2035ca6` feat: add search result cache with PostgreSQL-backed TTL and invalidation (Story 3.5)
- `6c0285d` feat: add proposability filter with config-driven rules and SQL-level filtering (Story 3.4)
- `6dec026` feat: add hybrid search with semantic + keyword + RRF fusion (Story 3.3)
- `08f9b54` feat: add embedding generation, HNSW vector index, and dimension validation (Story 3.2)

All 339 unit tests passing. Search module fully functional. No regressions.

### What NOT to Do

- Do NOT create a synonym database or external dictionary — semantic understanding via BGE-M3 is the primary jargon handler (architecture decision, FR7)
- Do NOT replace original query tokens during expansion — only append. Original tokens must remain for keyword search matching
- Do NOT expand abbreviations inside reference codes (e.g., "REF-DN100" should NOT trigger "DN" expansion)
- Do NOT change the cache key computation — cache key must use ORIGINAL query (pre-expansion). `compute_cache_key()` in `search/cache.py` is untouched
- Do NOT add a jargon/synonym table to the database — this is config-driven only for MVP
- Do NOT implement fuzzy matching or Levenshtein distance — out of scope, handled by semantic search
- Do NOT implement per-client jargon profiles — that's Epic 6 (memory, client preferences)
- Do NOT modify `vector.py`, `keyword.py`, `cache.py`, or `proposability.py` — expansion happens in engine.py before calling these
- Do NOT use relative imports anywhere
- Do NOT mock services in E2E tests — use ALL real services (PostgreSQL, embedding model)
- Do NOT add jargon expansion metrics to the health endpoint — that's Epic 7 (observability)
- Do NOT implement automatic jargon learning from corrections — that's Epic 6 (feedback loop, Story 6.4)
- Do NOT cache expanded queries separately — one cache entry per original query, expansion is transparent
- Do NOT add admin CLI for jargon management — that's Epic 8 scope

### Project Structure Notes

- New file `search/jargon.py` — consistent with search module structure (like `cache.py`, `proposability.py`)
- New benchmark fixture in `tests/e2e/fixtures/` — follows existing pattern (`catalog_50k_sample.jsonl`)
- No conflicts with existing structure detected

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.6] — acceptance criteria: abbreviations via semantic understanding, client nicknames with confidence, cross-language matching
- [Source: _bmad-output/planning-artifacts/prd.md#FR7] — "agent can match client-specific terminology, abbreviations, and jargon to catalog products"
- [Source: _bmad-output/planning-artifacts/prd.md#NFR-P2] — "search latency < 3 seconds"
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — "BGE-M3 multilingual model, semantic + keyword hybrid search"
- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure] — "No Redis — PostgreSQL only"
- [Source: _bmad-output/planning-artifacts/architecture.md#Embedding Strategy] — "Local multilingual model (BGE-M3), multilingual support from day one"
- [Source: docs/project-context.md] — naming conventions, test patterns, structured logging, settings pattern
- [Source: src/quote_agent/search/engine.py] — current SearchEngine with hybrid/semantic/keyword methods
- [Source: src/quote_agent/search/models.py] — current SearchRequest, ScoredProduct, SearchResult DTOs
- [Source: src/quote_agent/config.py] — Settings with SearchSettings, SearchCacheSettings pattern to follow
- [Source: src/quote_agent/search/cache.py] — compute_cache_key() that must NOT be modified
- [Source: prototype/data/emails/email_jargon.json] — real examples of industrial jargon in quote requests
- [Source: _bmad-output/implementation-artifacts/3-5-cache-de-resultats-de-recherche.md] — previous story: cache integration, test patterns
- [Source: _bmad-output/build-in-public/t5-french-industrial-jargon-post.md] — real-world jargon examples (DN100, PN16, inox 316L)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Unicode regex fix: `Ø` (U+00D8) is treated as `\w` by Python regex, requiring separate handling for non-ASCII abbreviations. ASCII word-char abbreviations use `\b` word boundary; non-ASCII uses `(?:^|(?<=\s))` pattern.

### Completion Notes List

- Implemented `JargonSettings` with 10 default French industrial abbreviations and `expansion_enabled` toggle (env: `JARGON__EXPANSION_ENABLED`)
- Created `search/jargon.py` with `expand_query()` — additive expansion that appends full forms while preserving original tokens
- Two regex strategies: ASCII abbreviations use word-boundary matching with reference-code protection; non-ASCII symbols (Ø) use whitespace/start-of-string matching
- Integrated jargon expansion into all 3 SearchEngine methods (`search_hybrid`, `search_semantic_only`, `search_keyword_only`)
- Cache key correctly uses original (pre-expansion) query — `compute_cache_key()` untouched
- Added `jargon_expanded` and `expanded_query` metadata fields to `SearchResult`
- 23 unit tests covering expansion logic, settings, engine integration, and cache key behavior
- 5 E2E tests (4 functional + 1 benchmark with 25 queries, >= 80% pass rate threshold)
- All 363 unit tests pass (24 new + 339 existing), 0 regressions
- Ruff and mypy (strict) pass with zero issues

### File List

**New files:**
- `src/quote_agent/search/jargon.py` — query expansion logic (`expand_query`, `JargonExpansionResult`)
- `tests/unit/test_search_jargon.py` — 23 unit tests
- `tests/e2e/test_search_jargon_e2e.py` — 5 E2E tests (jargon + benchmark)
- `tests/e2e/fixtures/jargon_benchmark.json` — 25 benchmark test cases

**Modified files:**
- `src/quote_agent/config.py` — added `JargonSettings` class and `jargon` field on `Settings`
- `src/quote_agent/search/models.py` — added `jargon_expanded`, `expanded_query` to `SearchResult`
- `src/quote_agent/search/engine.py` — integrated jargon expansion before embedding/keyword search in all 3 methods

### Change Log

- 2026-03-20: Story 3.6 implemented — jargon query expansion with config-driven abbreviation dictionary, SearchEngine integration, 23 unit tests + 5 E2E tests
- 2026-03-20: Code review — 2 fixes applied: (M1) E2E test replaced Pydantic instance mutation with `model_copy(update=...)` pattern; (L1) extracted `_apply_jargon_expansion()` private method in SearchEngine to eliminate 3x code duplication. All 363 tests pass, ruff + mypy clean.
