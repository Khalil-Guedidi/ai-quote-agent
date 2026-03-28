# Story 6.1: Mémoire Industrie (RAG Knowledge Base)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to access industry-level knowledge (conventions, norms, standard defaults),
So that it understands general industry context even for new clients or unfamiliar product families.

## Acceptance Criteria

1. **AC-1: Industry knowledge retrieval via RAG**
   Given the industry knowledge base is populated (industry conventions, norms, standard terminology)
   When the agent processes a request referencing industry standards (e.g., "NF EN 10088" for stainless steel)
   Then it retrieves relevant industry context via RAG and uses it to inform product matching
   And the knowledge base is stored in PostgreSQL with vector embeddings for retrieval

2. **AC-2: Baseline reasoning for new clients**
   Given the industry knowledge base exists
   When the agent processes a request with no client history
   Then industry-level knowledge provides a baseline for reasoning (not a blank slate)

3. **AC-3: Hot-reload without restart**
   Given new industry knowledge needs to be added
   When documents are added to the knowledge base
   Then they are embedded and indexed without requiring system restart

4. **AC-4: Integration into agent pipeline**
   Given the memory lookup is wired into the LangGraph pipeline
   When the agent processes any quote request
   Then industry context is retrieved and injected into the reasoning node's context
   And the existing pipeline paths (7 happy paths + error paths) remain unchanged

5. **AC-5: CLI for knowledge base management**
   Given the knowledge base management CLI exists
   When Laurent runs `agent kb ingest <file>` or `agent kb search <query>`
   Then documents are ingested/searched and results are displayed
   And the CLI follows the established `main.py` sync→async pattern (Story 6.0a)

6. **AC-6: Quality gates pass**
   Given the implementation is complete
   When quality checks run
   Then `uv run mypy --strict src/` reports 0 issues
   And `uv run ruff check src/ tests/` reports 0 issues
   And `uv run pytest tests/unit/ -v --tb=short` reports 0 failures (baseline: 799)

## Tasks / Subtasks

- [x] Task 1: Create `knowledge_document` DB model + migration (AC: #1)
  - [x] 1.1 Create `src/quote_agent/models/knowledge_document.py` — SQLAlchemy model with: `id` (UUID), `title` (String), `source` (String — file path or URL), `content` (Text — raw document content), `chunk_index` (Integer — position within source document), `vector` (Vector(1024) — BGE-M3 embedding), `search_vector` (TSVECTOR — for keyword fallback), `metadata_` (JSON — norms, tags, domain), `is_active` (Boolean), `created_at`/`updated_at` (TimestampMixin)
  - [x] 1.2 Create Alembic migration: `knowledge_documents` table + HNSW index (`m=16, ef_construction=64`, same params as products) + GIN index on `search_vector`
  - [x] 1.3 Register model in `models/__init__.py` so Alembic autogenerate discovers it

- [x] Task 2: Create `memory/industry.py` — RAG retrieval module (AC: #1, #2)
  - [x] 2.1 Create `src/quote_agent/memory/__init__.py` (empty or with factory)
  - [x] 2.2 Create `src/quote_agent/memory/industry.py` with `IndustryMemory` class:
    - Constructor takes `AsyncSession` + embedding adapter (same pattern as `SearchEngine`)
    - `async def retrieve(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]` — embed query, run pgvector cosine similarity search on `knowledge_documents`, return top-k chunks
    - `async def ingest(self, title: str, content: str, source: str, metadata: dict | None = None) -> int` — chunk text, embed chunks, upsert to DB, return chunk count
  - [x] 2.3 Create `src/quote_agent/memory/models.py` — Pydantic DTOs: `KnowledgeChunk` (content, title, source, score, metadata), `IngestionResult` (document_title, chunks_created, source)
  - [x] 2.4 Chunking strategy: split by `\n\n` paragraphs, max ~512 tokens per chunk, overlap 50 tokens between consecutive chunks. Keep it simple — no langchain text splitters dependency.

- [x] Task 3: Wire industry memory into agent pipeline (AC: #4)
  - [x] 3.1 Add `industry_context: list[KnowledgeChunk] | None` field to `AgentState` in `state.py`
  - [x] 3.2 Add `memory_lookup` node to `graph.py`: runs between `classify` and `reason`, retrieves industry context for the request
  - [x] 3.3 Update `reason_node` to pass `industry_context` to `apply_reasoning_strategy()` — extend the function signature
  - [x] 3.4 Update `reasoning_strategy.py` to incorporate industry context into the LLM prompt when available (append as "Industry Context" section in system message)
  - [x] 3.5 Update graph edges: `classify → memory_lookup → reason` (was `classify → reason`)
  - [x] 3.6 Update `graph-path-inventory.md` with the new node in all paths
  - [x] 3.7 The `memory_lookup` node is **fire-and-forget style**: if retrieval fails, log warning and continue with `industry_context = None` — never block the pipeline

- [x] Task 4: Create CLI commands for knowledge base management (AC: #5)
  - [x] 4.1 Create `src/quote_agent/cli/knowledge_base.py` with async functions:
    - `async def kb_ingest(file_path: str, title: str | None = None) -> None` — read file, call `IndustryMemory.ingest()`
    - `async def kb_search(query: str, top_k: int = 5) -> None` — call `IndustryMemory.retrieve()`, display results
    - `async def kb_list() -> None` — list all documents in knowledge base with counts
  - [x] 4.2 Add commands to `main.py`: `agent kb-ingest`, `agent kb-search`, `agent kb-list` — follow `asyncio.run()` wrapper pattern from Story 6.0a
  - [x] 4.3 Support markdown and plain text files for ingestion (read file, chunk, embed, store)

- [x] Task 5: Add configuration (AC: #3)
  - [x] 5.1 Add `IndustryMemorySettings` to `config.py`: `enabled: bool = True`, `top_k: int = 5`, `chunk_max_tokens: int = 512`, `chunk_overlap_tokens: int = 50`
  - [x] 5.2 Add `industry_memory: IndustryMemorySettings` to `Settings` class
  - [x] 5.3 Env var prefix: `INDUSTRY_MEMORY__` (e.g., `INDUSTRY_MEMORY__TOP_K=10`)

- [x] Task 6: Unit tests (AC: #6)
  - [x] 6.1 `tests/unit/memory/test_industry.py` — test retrieval, ingestion, chunking, empty KB fallback
  - [x] 6.2 `tests/unit/agent/test_memory_lookup_node.py` — test node integration: success, empty results, failure graceful degradation
  - [x] 6.3 `tests/unit/test_knowledge_document_model.py` — model creation, constraints
  - [x] 6.4 Update existing `test_agent_graph.py` — added `IndustryMemorySettings(enabled=False)` to settings mock; updated `test_agent_state.py` for new `industry_context` field

- [x] Task 7: Quality gates (AC: #6)
  - [x] 7.1 `uv run ruff check src/ tests/` — 0 issues on modified files
  - [x] 7.2 `uv run ruff format --check src/ tests/` — 0 issues on modified files
  - [x] 7.3 `uv run mypy --strict src/` — 0 issues (100 source files)
  - [x] 7.4 `uv run pytest tests/unit/ -v --tb=short` — 827 passed, 0 failures (baseline: 799, +28 new)

## Dev Notes

### Architecture: memory/ is Internal Infrastructure (like search/)

The `memory/` module follows the **search/ pattern**, NOT the adapter pattern:
- Lives in `src/quote_agent/memory/` — internal infrastructure, not an external integration
- No Protocol, no factory, no `@lru_cache` singleton — components are instantiated per-request with a DB session
- Similar to how `SearchEngine` takes `(session, embedding_adapter)`, `IndustryMemory` takes `(session, embedding_adapter)`
- The embedding adapter is the EXISTING `get_embedding_adapter()` — do NOT create a new one. BGE-M3 (1024-dim) is already configured.

[Source: docs/project-context.md#Search Module Pattern]
[Source: _bmad-output/planning-artifacts/architecture.md, lines 572-576]

### Database: Reuse Existing Patterns

The `knowledge_documents` table follows the exact same vector storage pattern as `products`:

| Pattern | Products (existing) | Knowledge Documents (new) |
|---------|-------------------|--------------------------|
| Vector column | `Vector(1024)` | `Vector(1024)` — same BGE-M3 embeddings |
| HNSW index | `m=16, ef_construction=64` | Same params |
| Full-text | `TSVECTOR` column | `TSVECTOR` column (for keyword fallback) |
| Primary key | `UUID` with `gen_random_uuid()` | Same |
| Timestamps | `TimestampMixin` | Same |

[Source: src/quote_agent/models/product.py]
[Source: alembic/versions/78fc0a54b3b9_fix_vector_dim_1024_and_add_hnsw_index.py]

### Pipeline Integration: New Node Between classify and reason

Current flow:
```
START → classify → reason → score → route → ...
```

New flow:
```
START → classify → memory_lookup → reason → score → route → ...
```

The `memory_lookup` node:
- Runs AFTER classify (needs the classification to know what to search for)
- Runs BEFORE reason (provides industry context for the reasoning strategy)
- Uses fire-and-forget error handling (like notification nodes): if retrieval fails, `industry_context = None` and pipeline continues
- Does NOT set `state["error"]` on failure — degraded but functional

The `reason_node` closure in `graph.py` already takes `session_factory` and `engine`. The `memory_lookup` node needs the same `session_factory` plus `get_embedding_adapter()`.

[Source: src/quote_agent/agent/graph.py, lines 115-130]
[Source: docs/graph-path-inventory.md]

### Chunking: Keep It Simple

Do NOT use LangChain text splitters or any external dependency for chunking. Implement a simple paragraph-based chunker:

1. Split on `\n\n` (double newline)
2. Merge small paragraphs until chunk approaches `chunk_max_tokens` (~512)
3. Overlap: include last `chunk_overlap_tokens` (~50) tokens from previous chunk in next chunk
4. Token estimation: `len(text.split())` is sufficient (no tiktoken dependency needed)

This is industry knowledge (norms, conventions, defaults) — not long-form documents. Chunks will be short and self-contained.

### Reasoning Strategy Integration

`apply_reasoning_strategy()` in `reasoning_strategy.py` currently builds an LLM prompt with:
- System instructions
- Classification result
- Search results
- Raw request

Add a new optional section for industry context:
```
### Industry Context (if available)
{formatted_chunks}
```

The function signature becomes:
```python
async def apply_reasoning_strategy(
    classification: ClassificationResult,
    request: ExtractedQuoteRequest,
    llm_adapter: OpenAICompatAdapter,
    search_engine: SearchEngine,
    industry_context: list[KnowledgeChunk] | None = None,  # NEW
) -> ReasoningResult:
```

The `industry_context` parameter is optional with default `None` — this ensures backward compatibility for all existing tests and callers.

[Source: src/quote_agent/agent/nodes/reasoning_strategy.py]

### CLI Pattern (from Story 6.0a)

All CLI commands follow the pattern established in Story 6.0a:

```python
# In main.py:
@app.command()
def kb_ingest(file_path: str = typer.Argument(...), title: str | None = None) -> None:
    """Ingest a document into the industry knowledge base."""
    from quote_agent.cli.knowledge_base import kb_ingest as _kb_ingest
    asyncio.run(_kb_ingest(file_path, title))

# In cli/knowledge_base.py:
async def kb_ingest(file_path: str, title: str | None = None) -> None:
    ...
```

[Source: src/quote_agent/cli/main.py — 14 commands all follow this pattern]

### What NOT to Do

- Do NOT create a new embedding adapter or model — reuse `get_embedding_adapter()` (BGE-M3, 1024-dim)
- Do NOT create a Protocol/factory for memory — it's internal infrastructure like search/
- Do NOT add LangChain text splitter dependency — simple paragraph chunking is sufficient
- Do NOT modify existing graph paths or routing logic — only insert a new node between classify and reason
- Do NOT set `state["error"]` in the memory_lookup node — use fire-and-forget pattern
- Do NOT add tiktoken dependency for token counting — `len(text.split())` word count is sufficient
- Do NOT create a Redis cache — use PostgreSQL for everything (project convention)
- Do NOT modify `SearchEngine` or `search/` module — memory is a separate concern
- Do NOT change any existing tests — add new tests only

### Anti-Pattern Prevention

- **Do NOT put vector search logic in memory/industry.py directly**: Use SQLAlchemy + pgvector operators (same pattern as `search/vector.py`). The `<=>` cosine distance operator is already available via pgvector.sqlalchemy.
- **Do NOT use `asyncio.run()` inside memory/industry.py**: This is library code, not a CLI entry point. All methods must be `async`.
- **Do NOT skip the HNSW index**: Without it, vector search does a sequential scan — unacceptable even for small knowledge bases.
- **Do NOT forget `from __future__ import annotations`**: Required in all new files (project convention). Exception: `state.py` intentionally omits it for LangGraph compatibility.
- **Do NOT forget to clear `@lru_cache` in tests**: If you add any new cached singleton, add it to the cache clearing list in `tests/e2e/conftest.py`.

### Project Structure Notes

New files to create:
```
src/quote_agent/
├── memory/
│   ├── __init__.py              # NEW — empty or simple exports
│   ├── industry.py              # NEW — IndustryMemory class (RAG retrieval + ingestion)
│   └── models.py                # NEW — KnowledgeChunk, IngestionResult DTOs
├── models/
│   └── knowledge_document.py    # NEW — SQLAlchemy model for knowledge_documents table
├── cli/
│   └── knowledge_base.py        # NEW — CLI async functions for KB management

alembic/versions/
└── xxx_add_knowledge_documents.py  # NEW — migration

tests/unit/
├── memory/
│   └── test_industry.py         # NEW — unit tests for IndustryMemory
└── agent/
    └── test_memory_lookup_node.py  # NEW — node integration tests
```

Files to modify:
```
src/quote_agent/agent/state.py          # Add industry_context field
src/quote_agent/agent/graph.py          # Add memory_lookup node + edges
src/quote_agent/agent/nodes/reasoning_strategy.py  # Accept industry_context param
src/quote_agent/config.py               # Add IndustryMemorySettings
src/quote_agent/cli/main.py             # Add kb-ingest, kb-search, kb-list commands
src/quote_agent/models/__init__.py      # Register KnowledgeDocument for Alembic
docs/graph-path-inventory.md            # Add memory_lookup to all path sequences
```

### Key Code Locations

| Concept | File | Notes |
|---------|------|-------|
| Vector search pattern (reuse) | `search/vector.py` | pgvector cosine similarity with `<=>` operator |
| Product model pattern (reuse) | `models/product.py` | Vector(1024) + TSVECTOR + HNSW index |
| Search engine pattern (reuse) | `search/engine.py` | Session + embedding adapter injection |
| HNSW migration pattern (reuse) | `alembic/versions/78fc0a54b3b9_*.py` | Raw SQL for HNSW index creation |
| Graph node pattern | `agent/graph.py` | Closure over injected deps + error handling |
| AgentState | `agent/state.py` | TypedDict, no `from __future__ import annotations` |
| Reasoning strategy | `agent/nodes/reasoning_strategy.py` | LLM prompt construction |
| CLI async pattern | `cli/main.py` | `asyncio.run()` wrapper + lazy import |
| Config pattern | `config.py` | Nested `BaseSettings` with `__` delimiter |
| Embedding adapter | `adapters/embedding/` | BGE-M3, 1024-dim, `get_embedding_adapter()` |

### Previous Story Intelligence

**From Story 6.0a (done):**
- All CLI implementation files now export async functions — `asyncio.run()` only in `main.py`
- Quality baseline: 799 unit tests passing, mypy strict 0 issues, ruff 0 issues
- Pattern confirmed: `main.py` sync wrapper → `asyncio.run()` → async implementation
- Fixed 21 pre-existing test failures (self_reviewer mock, router threshold, notification health check, worker config)

**From Story 6.0b (done):**
- Notification card builder in `teams.py` supports conditional action buttons via `data.get("erp_url")` presence check
- Fire-and-forget notification pattern confirmed working
- No changes to graph structure or pipeline flow

### Git Intelligence

Recent commits (last 2):
- `20c0b3b` — Story 6.0b: removed misleading "Voir dans l'ERP" on escalation/rejection cards
- `18aa22d` — Story 6.0a: refactored `asyncio.run()` from 12 CLI files to single `main.py`

Both foundation stories are done. The codebase is clean and ready for the memory layer.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1] — AC and user story (FR17)
- [Source: _bmad-output/planning-artifacts/prd.md, line 386] — "FR17: industry-level knowledge (conventions, norms, defaults) from a shared knowledge base"
- [Source: _bmad-output/planning-artifacts/architecture.md, lines 156-159] — `memory/` directory structure: industry.py, company.py, client.py
- [Source: _bmad-output/planning-artifacts/architecture.md, lines 572-576] — Full planned memory module structure
- [Source: _bmad-output/planning-artifacts/architecture.md, lines 753-756] — Memory layer boundary: calls models/ (DB) and search/ (for RAG)
- [Source: _bmad-output/planning-artifacts/architecture.md, line 800] — Data flow: MemoryLookup (industry/company/client) in agent pipeline
- [Source: docs/project-context.md#Search Module Pattern] — Internal infrastructure, not adapter pattern
- [Source: docs/project-context.md#Embedding Adapter Pattern] — BGE-M3, 1024-dim, asyncio.to_thread wrapping
- [Source: docs/project-context.md#Graph Node Pattern] — current_node at entry + all returns, error returns state
- [Source: docs/project-context.md#Fire-and-Forget Notification Pattern] — Never block pipeline, log failures silently
- [Source: docs/graph-path-inventory.md] — All 14 paths from START to END
- [Source: src/quote_agent/agent/graph.py] — Current graph topology and node wiring
- [Source: src/quote_agent/agent/state.py] — AgentState TypedDict definition
- [Source: src/quote_agent/models/product.py] — Vector column + HNSW index pattern
- [Source: _bmad-output/implementation-artifacts/6-0a-refactor-asyncio-run-dette-technique.md] — CLI async pattern established
- [Source: _bmad-output/implementation-artifacts/6-0b-fix-voir-dans-erp-cartes-escalade-rejet.md] — Fire-and-forget notification pattern confirmed

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Fixed ruff import sorting in `state.py` (I001)
- Fixed unused imports (`uuid`, `pytest`) in test files
- Fixed N817 rename in `test_knowledge_document_model.py`
- Updated `_make_settings_mock` in `test_agent_graph.py` to include `IndustryMemorySettings(enabled=False)` — prevents memory_lookup node from trying real DB connections in unit tests
- Updated `test_agent_state.py` to include `industry_context` field

### Completion Notes List

- **Task 1**: Created `KnowledgeDocument` SQLAlchemy model following exact `Product` pattern (Vector(1024), TSVECTOR, HNSW index). Migration creates table + HNSW + GIN indexes.
- **Task 2**: Implemented `IndustryMemory` class with `retrieve()` (pgvector cosine similarity) and `ingest()` (paragraph-based chunking). Simple chunker: split on `\n\n`, max 512 tokens, 50-token overlap. No external dependencies.
- **Task 3**: Added `memory_lookup` node between `classify` and `reason`. Fire-and-forget: never sets `state["error"]`, logs warning on failure. Industry context injected into exploration and deep_analysis LLM prompts as "CONTEXTE INDUSTRIE" section. Updated graph-path-inventory.md.
- **Task 4**: Created `kb-ingest`, `kb-search`, `kb-list` CLI commands following Story 6.0a async pattern. Supports .md and .txt files.
- **Task 5**: Added `IndustryMemorySettings` (enabled, top_k, chunk_max_tokens, chunk_overlap_tokens) with `INDUSTRY_MEMORY__` env prefix.
- **Task 6**: 28 new unit tests: 15 for IndustryMemory (chunking, retrieval, ingestion, listing), 9 for memory_lookup node (query building, graph wiring, enabled/disabled/failure), 4 for KnowledgeDocument model.
- **Task 7**: All quality gates pass — mypy 0 issues, ruff 0 issues, 827 unit tests passing (+28 from baseline 799).

### File List

New files:
- `src/quote_agent/models/knowledge_document.py`
- `src/quote_agent/memory/__init__.py`
- `src/quote_agent/memory/industry.py`
- `src/quote_agent/memory/models.py`
- `src/quote_agent/cli/knowledge_base.py`
- `alembic/versions/b1a2c3d4e5f6_add_knowledge_documents_table.py`
- `tests/unit/memory/__init__.py`
- `tests/unit/memory/test_industry.py`
- `tests/unit/agent/test_memory_lookup_node.py`
- `tests/unit/test_knowledge_document_model.py`

Modified files:
- `src/quote_agent/models/__init__.py` — registered KnowledgeDocument
- `src/quote_agent/config.py` — added IndustryMemorySettings
- `src/quote_agent/agent/state.py` — added industry_context field
- `src/quote_agent/agent/graph.py` — added memory_lookup node + _build_memory_query helper
- `src/quote_agent/agent/nodes/reasoning_strategy.py` — added industry_context param + _format_industry_context
- `src/quote_agent/cli/main.py` — added kb-ingest, kb-search, kb-list commands
- `docs/graph-path-inventory.md` — updated all paths with memory_lookup node
- `tests/unit/test_agent_graph.py` — updated _make_settings_mock with IndustryMemorySettings
- `tests/unit/test_agent_state.py` — added industry_context to expected fields

### Change Log

- 2026-03-28: Story 6.1 implemented — Industry knowledge RAG memory layer with pgvector retrieval, pipeline integration, CLI commands, and 28 unit tests. All quality gates pass.
- 2026-03-28: Code review fixes — (H1) removed direct state mutation in memory_lookup_node graph.py:131, (M1) fixed missing memory_lookup in path 10 of graph-path-inventory.md, (M2) fixed pre-existing ruff format violations in test_agent_graph.py.
