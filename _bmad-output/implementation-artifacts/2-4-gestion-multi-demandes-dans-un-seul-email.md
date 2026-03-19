# Story 2.4: Gestion Multi-Demandes dans un Seul Email

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to detect and handle multiple quote requests within a single email,
So that each product request is processed independently without losing any.

## Acceptance Criteria

1. **AC-2.4.1**: Multi-request detection and splitting
   - Given an email containing 3 distinct product requests
   - When the agent runs extraction
   - Then it identifies and separates each request into its own structured record
   - And each sub-request is tracked independently in the system

2. **AC-2.4.2**: Single-request emails are not falsely split
   - Given an email with a single request
   - When the agent runs extraction
   - Then it correctly identifies one request (no false splitting)

3. **AC-2.4.3**: Independent sub-request tracking with parent link
   - Given a multi-request email is processed
   - When all sub-requests are extracted
   - Then each sub-request can proceed independently through the pipeline
   - And the parent email tracks the status of all its sub-requests

## Tasks / Subtasks

- [x] Task 1: Create `QuoteRequest` SQLAlchemy model in `src/quote_agent/models/quote_request.py` (AC: 1, 3)
  - [x] 1.1: Create `QuoteRequest` model with columns: `id` (UUID PK), `email_request_id` (FK → email_requests.id), `request_index` (int — 0-based position among siblings), `line_items` (JSON — list of line item dicts), `client_name` (str|None), `client_identifier` (str|None), `client_email` (str|None), `urgency` (str|None), `delivery_address` (str|None), `notes` (str|None), `status` (str, default "pending"), `error_message` (Text|None), `confidence` (float|None)
  - [x] 1.2: Add `TimestampMixin` for `created_at`/`updated_at`
  - [x] 1.3: Add FK constraint and index on `email_request_id`
  - [x] 1.4: Add unique constraint on `(email_request_id, request_index)` to prevent duplicate sub-requests
  - [x] 1.5: Register model import in `src/quote_agent/models/__init__.py` so Alembic detects it

- [x] Task 2: Generate and verify Alembic migration (AC: 3)
  - [x] 2.1: `uv run alembic revision --autogenerate -m "add quote_requests table"`
  - [x] 2.2: Review migration — verify FK, indexes, unique constraint
  - [x] 2.3: Test migration up/down: `uv run alembic upgrade head` / `uv run alembic downgrade -1`

- [x] Task 3: Create multi-request splitting service in `src/quote_agent/services/request_splitter.py` (AC: 1, 2)
  - [x] 3.1: Create `SplitResult` Pydantic DTO in `src/quote_agent/services/extraction_models.py` — `requests: list[ExtractedQuoteRequest]`, `split_count: int`, `split_rationale: str`, `split_duration_ms: int`
  - [x] 3.2: Create `split_requests(extraction_result: ExtractionResult) -> SplitResult` function
  - [x] 3.3: Implement splitting logic — if extraction has only 1 logical request (all line items related), return it as-is in a single `ExtractedQuoteRequest`; if multiple distinct requests detected, split into separate `ExtractedQuoteRequest` instances
  - [x] 3.4: Use LLM (`get_model("simple")`) with `with_structured_output` to decide how to group line items into distinct requests. The LLM receives the extracted data (NOT the raw email) and determines grouping
  - [x] 3.5: Define Pydantic model `SplitDecision` for LLM output — `groups: list[RequestGroup]` where `RequestGroup` has `line_item_indices: list[int]` and `rationale: str`
  - [x] 3.6: Short-circuit: if `len(line_items) <= 1`, skip LLM call and return single request immediately (no splitting needed)
  - [x] 3.7: Apply 10-second timeout on LLM call (same NFR-P3 pattern)
  - [x] 3.8: On LLM error, fall back to treating all line items as a single request (graceful degradation, log warning)

- [x] Task 4: Integrate splitting into pipeline and persist `QuoteRequest` records (AC: 1, 3)
  - [x] 4.1: In `_persist_emails()`, after successful extraction (status="extracted"), call `split_requests()`
  - [x] 4.2: For each split result, create a `QuoteRequest` record with the appropriate subset of line items and shared fields (client info, urgency, etc.)
  - [x] 4.3: Update parent `EmailRequest.status` to "split" (new status in the state machine)
  - [x] 4.4: If splitting fails (LLM error), create a single `QuoteRequest` with all line items (graceful degradation) — parent status still becomes "split"
  - [x] 4.5: Log structured trace: `component: "services.request_splitter"`, include `email_request_id`, `split_count`, `split_rationale`, `duration_ms`

- [x] Task 5: Write tests (AC: 1, 2, 3)
  - [x] 5.1: Unit tests for `QuoteRequest` model in `tests/unit/test_quote_request_model.py` (3 tests)
    - Test: model creation with all fields
    - Test: FK relationship to email_request_id
    - Test: unique constraint on (email_request_id, request_index)
  - [x] 5.2: Unit tests for `split_requests()` in `tests/unit/test_request_splitter.py` (7 tests)
    - Test: single line item → single request, no LLM call
    - Test: empty line items → single request with empty items
    - Test: multiple related items → single request (LLM says one group)
    - Test: multiple distinct items → multiple requests (LLM splits)
    - Test: LLM timeout → graceful fallback to single request
    - Test: LLM error → graceful fallback to single request
    - Test: split duration is measured and returned
  - [x] 5.3: Update `tests/unit/test_email_poller.py` to verify splitting integration (3 tests)
    - Test: successful extraction + split creates QuoteRequest records
    - Test: single-request email creates exactly 1 QuoteRequest
    - Test: split failure still creates 1 QuoteRequest (graceful degradation)
  - [x] 5.4: Integration test for parent-child tracking — verify parent email_request links to child quote_requests

## Dev Notes

### Architecture Compliance

- **New `quote_requests` table**: This was explicitly planned in Story 2.3's dev notes: "A separate `quote_requests` table will come in Story 2.4 when sub-requests need independent tracking." [Source: 2-3-extraction-de-donnees-structurees.md#Critical-Anti-Patterns]
- **Service layer**: `src/quote_agent/services/request_splitter.py` — new service for multi-request splitting. Follows architecture pattern: services for business logic orchestration. [Source: architecture.md#Services-Layer]
- **Pydantic DTOs**: New splitting DTOs (`SplitResult`, `SplitDecision`, `RequestGroup`) go in `src/quote_agent/services/extraction_models.py` — extending the existing extraction DTOs file. NOT in `models/` (reserved for SQLAlchemy). [Source: architecture.md#Enforcement-Guidelines rule 7]
- **SQLAlchemy model**: `QuoteRequest` goes in `src/quote_agent/models/quote_request.py` — follows the one-model-per-file pattern. [Source: architecture.md#Complete-Project-Directory-Structure]
- **Status machine extension**: `received` → `cleaned` → `extracted` → `split`. The new `split` status indicates sub-requests have been created and are ready for downstream processing (Epic 3+). [Source: architecture.md#email_request.py]
- **LLM adapter reuse**: Use `get_model("simple").with_structured_output(SplitDecision)` — same pattern as Story 2.3's extraction. [Source: 2-3-extraction-de-donnees-structurees.md#Technical-Implementation-Details]
- **Structured logging**: Log with `component: "services.request_splitter"` following JSON format. [Source: architecture.md#Structured-Logging-Format]

### Existing Code to Extend

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/models/email_request.py` | `EmailRequest` with `extracted_data` (JSON), `status` field | No schema changes needed — add new status value "split" (status is a free string, not an enum) |
| `src/quote_agent/models/__init__.py` | May or may not import models | Ensure `QuoteRequest` is imported so Alembic detects it |
| `src/quote_agent/services/extraction_models.py` | `QuoteLineItem`, `ExtractedQuoteRequest`, `ExtractionResult` | Add `SplitDecision`, `RequestGroup`, `SplitResult` DTOs |
| `src/quote_agent/services/email_extractor.py` | `extract()` returning `ExtractionResult` with `request.line_items` | No changes — splitter consumes its output |
| `src/quote_agent/services/email_poller.py` | `_persist_emails()` calls extract → sets status "extracted" | Add splitting step after extraction |
| `src/quote_agent/exceptions.py` | `LLMTimeoutError`, `AdapterError` | Reuse for splitting errors — no new exceptions needed |

### Technical Implementation Details

**Splitting approach — LLM-based grouping:**

The splitter receives the already-extracted `ExtractedQuoteRequest` (from Story 2.3) and determines how to group `line_items` into distinct quote requests. This is NOT a re-extraction from raw email — it operates on structured data only.

```python
# Splitting DTO for LLM structured output
class RequestGroup(BaseModel):
    """A group of line items forming a single quote request."""
    line_item_indices: list[int]  # indices into the original line_items list
    rationale: str  # why these items belong together

class SplitDecision(BaseModel):
    """LLM decision on how to group line items into distinct requests."""
    groups: list[RequestGroup]
```

**Splitting system prompt:**

```python
SPLITTING_SYSTEM_PROMPT = """You are a request grouping assistant for a French B2B industrial quote processing system.

You receive a list of extracted product line items from a single email. Your task: determine if these items represent ONE quote request or MULTIPLE distinct quote requests.

Grouping rules:
- Items that would logically appear on the SAME quote belong together (same project, same delivery, related products)
- Items that are clearly for DIFFERENT purposes/projects/clients should be separate groups
- When in doubt, keep items together (prefer fewer groups over more)
- A single item is always one group
- Consider: delivery address differences, project references, product category coherence

Output the grouping as a list of groups, each containing the indices of line items that belong together.
If ALL items belong to one request, output a single group with all indices."""
```

**Short-circuit optimization:**

```python
async def split_requests(extraction_result: ExtractionResult) -> SplitResult:
    line_items = extraction_result.request.line_items

    # Short-circuit: 0 or 1 items → no splitting needed
    if len(line_items) <= 1:
        return SplitResult(
            requests=[extraction_result.request],
            split_count=1,
            split_rationale="Single or no line items — no splitting needed",
            split_duration_ms=0,
        )

    # LLM-based grouping for 2+ items
    ...
```

**Creating QuoteRequest records from split results:**

```python
for idx, sub_request in enumerate(split_result.requests):
    quote_req = QuoteRequest(
        email_request_id=record.id,
        request_index=idx,
        line_items=[item.model_dump() for item in sub_request.line_items],
        client_name=sub_request.client_name,
        client_identifier=sub_request.client_identifier,
        client_email=sub_request.client_email,
        urgency=sub_request.urgency,
        delivery_address=sub_request.delivery_address,
        notes=sub_request.notes,
        status="pending",
        confidence=extraction_result.confidence,
    )
    session.add(quote_req)
```

**Integration into poller (`_persist_emails`):**

```python
# After successful extraction (status == "extracted"):
try:
    split_result = await split_requests(extraction_result)
    for idx, sub_request in enumerate(split_result.requests):
        quote_req = QuoteRequest(
            email_request_id=record.id,
            request_index=idx,
            line_items=[item.model_dump() for item in sub_request.line_items],
            client_name=sub_request.client_name,
            # ... shared fields ...
            status="pending",
        )
        session.add(quote_req)
    record.status = "split"
    logger.info(
        "Request splitting complete",
        extra={
            "component": "services.request_splitter",
            "context": {
                "email_request_id": str(record.id),
                "split_count": split_result.split_count,
                "split_rationale": split_result.split_rationale,
                "duration_ms": split_result.split_duration_ms,
            },
        },
    )
except (LLMTimeoutError, AdapterError) as exc:
    # Graceful degradation: create single QuoteRequest with all items
    quote_req = QuoteRequest(
        email_request_id=record.id,
        request_index=0,
        line_items=[item.model_dump() for item in extraction_result.request.line_items],
        # ... all fields from extraction_result.request ...
        status="pending",
    )
    session.add(quote_req)
    record.status = "split"  # still mark as split — 1 sub-request created
    logger.warning("Splitting failed for %s, falling back to single request: %s", incoming.message_id, exc)
```

**QuoteRequest model:**

```python
class QuoteRequest(Base, TimestampMixin):
    """Individual quote request extracted from an email (1 email → N requests)."""

    __tablename__ = "quote_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_requests.id"),
    )
    request_index: Mapped[int] = mapped_column(default=0)
    line_items: Mapped[list[dict]] = mapped_column(JSON, default=list)
    client_name: Mapped[str | None] = mapped_column(default=None)
    client_identifier: Mapped[str | None] = mapped_column(default=None)
    client_email: Mapped[str | None] = mapped_column(default=None)
    urgency: Mapped[str | None] = mapped_column(default=None)
    delivery_address: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    confidence: Mapped[float | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint("email_request_id", "request_index", name="uq_quote_requests_email_request_id_request_index"),
        Index("ix_quote_requests_email_request_id", "email_request_id"),
        Index("ix_quote_requests_status", "status"),
    )
```

### Project Structure Notes

New files:
- `src/quote_agent/models/quote_request.py` — SQLAlchemy model for `quote_requests` table
- `src/quote_agent/services/request_splitter.py` — multi-request splitting service
- `alembic/versions/{hash}_add_quote_requests_table.py` — auto-generated migration
- `tests/unit/test_quote_request_model.py` — model tests
- `tests/unit/test_request_splitter.py` — splitter unit tests

Modified files:
- `src/quote_agent/models/__init__.py` — import `QuoteRequest` for Alembic discovery
- `src/quote_agent/services/extraction_models.py` — add `SplitDecision`, `RequestGroup`, `SplitResult` DTOs
- `src/quote_agent/services/email_poller.py` — integrate splitting after extraction
- `tests/unit/test_email_poller.py` — verify splitting integration

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Re-extract from raw email for splitting | Operate on the already-extracted `ExtractedQuoteRequest` from Story 2.3 |
| Call LLM for emails with 0 or 1 line items | Short-circuit: return single request immediately |
| Block pipeline if splitting LLM call fails | Graceful degradation: create single `QuoteRequest` with all items |
| Store sub-request data only in `email_requests.extracted_data` JSON | Create proper `QuoteRequest` rows in `quote_requests` table for independent tracking |
| Add SQLAlchemy relationship (lazy loading) on `EmailRequest` | Use explicit queries — relationships add complexity and potential N+1 issues |
| Create a new exception class for splitting errors | Reuse `LLMTimeoutError` and `AdapterError` — splitting uses the same LLM patterns |
| Put `SplitDecision`/`RequestGroup` in a new file | Add to existing `extraction_models.py` — they are part of the extraction domain |
| Use `get_model("complex")` for splitting | Use `get_model("simple")` — grouping structured data is simpler than extraction |
| Add langchain, langgraph, or new dependencies | Everything needed is already installed |
| Create agent graph nodes for splitting | Service-layer function. Agent graph (LangGraph) comes in Epic 4 |
| Modify the `extract()` function | Splitting is a separate step AFTER extraction — keep separation of concerns |

### Scope Boundaries

- **IN scope**: `QuoteRequest` SQLAlchemy model + Alembic migration, LLM-based line item grouping into sub-requests, `SplitResult`/`SplitDecision` Pydantic DTOs, pipeline integration (extract → split → persist sub-requests), parent email status "split", graceful degradation on LLM failure, short-circuit for single items, structured logging, unit + integration tests
- **OUT of scope**: Product matching/search on sub-requests (Epic 3), confidence scoring per sub-request (Epic 4 — placeholder value from extraction is sufficient), prompt injection defense (Story 2.5), UI for viewing sub-requests (Epic 7), sub-request status progression beyond "pending" (downstream stories), relationship/ORM navigation between EmailRequest and QuoteRequest (use explicit queries), batch splitting across emails

### Previous Story Intelligence (Story 2.3)

- **`with_structured_output` pattern**: Story 2.3 established the pattern for LLM structured output using Pydantic models. Apply identically for `SplitDecision`. Mock `get_llm_adapter()` → `get_model("simple").with_structured_output().ainvoke()` in tests.
- **Inline integration in `_persist_emails()`**: Story 2.3 integrated extraction inline after cleaning. Continue this pattern — add splitting after extraction in the same flow.
- **Per-email error handling**: Story 2.3 catches `LLMTimeoutError`/`AdapterError` per-email without blocking pipeline. Apply same pattern for splitting errors, but with graceful degradation (create single QuoteRequest).
- **Status machine**: `received` → `cleaned` → `extracted` → `split`. Only attempt splitting on emails with `status == "extracted"`.
- **Module-level constants**: System prompt as module-level constant string, timeout as module-level constant.
- **`from __future__ import annotations`**: Continue using.
- **Duration measurement**: Use `time.monotonic()` for timing, same as extraction.
- **Code review fixes from 2.3**: Use `model_copy()` instead of in-place mutation. Use clear variable naming (`start_s` not `start_ms`).

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Last commits:
- `cfdd33e` feat: add LLM-based structured data extraction from quote emails (Story 2.3)
- `6b5e29e` feat: add LinkedIn French industrial jargon post (Story T.5)
- `65fbbe1` feat: add email content cleaning with French/English pattern support (Story 2.2)

127 tests passing, CI pipeline operational. Story 2.3 done and committed.

### References

- [Source: architecture.md#Services-Layer] — services for business logic orchestration
- [Source: architecture.md#Complete-Project-Directory-Structure] — models/ for SQLAlchemy, services/ for logic
- [Source: architecture.md#Naming-Patterns] — snake_case files, PascalCase classes, snake_case tables plural
- [Source: architecture.md#Data-Architecture] — PostgreSQL, SQLAlchemy, Alembic, JSON columns
- [Source: architecture.md#Enforcement-Guidelines] — typed Pydantic DTOs, mypy strict, structured logging
- [Source: architecture.md#Agent-State-LangGraph] — `ParsedRequest` in agent state (Epic 4 will consume split sub-requests)
- [Source: epics.md#Story-2.4] — acceptance criteria, user story
- [Source: epics.md#Story-2.3] — previous story context (extraction that this story consumes)
- [Source: 2-3-extraction-de-donnees-structurees.md] — previous story patterns, inline integration, error handling, `with_structured_output` pattern
- [Source: 2-3-extraction-de-donnees-structurees.md#Critical-Anti-Patterns] — "A separate quote_requests table will come in Story 2.4"

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Migration up/down/up cycle verified successfully
- Full test suite: 139 passed, 2 skipped, 0 failures

### Completion Notes List

- Task 1: Created `QuoteRequest` SQLAlchemy model with all specified columns, FK constraint, unique constraint on (email_request_id, request_index), and indexes. Registered in `models/__init__.py` for Alembic discovery.
- Task 2: Generated Alembic migration `98e0cffdcc69_add_quote_requests_table.py`. Verified FK, indexes, unique constraint in generated code. Tested migration up/down/up cycle successfully.
- Task 3: Created `request_splitter.py` service with LLM-based line item grouping. Added `SplitResult`, `SplitDecision`, `RequestGroup` DTOs to `extraction_models.py`. Implements short-circuit for 0-1 items, 10s timeout, and proper error propagation.
- Task 4: Integrated splitting into `_persist_emails()` after extraction. Creates `QuoteRequest` records for each split sub-request. Graceful degradation on LLM failure (creates single QuoteRequest with all items). Parent email status transitions to "split". Structured logging with component and context.
- Task 5: Added 3 model tests, 7 splitter unit tests, 3 poller integration tests, and 1 parent-child tracking integration test. Updated existing poller tests to account for splitting step. Total: 14 new tests, all passing.

### Senior Developer Review (AI)

**Reviewer:** Claude Opus 4.6 (adversarial code review)
**Date:** 2026-03-19
**Outcome:** APPROVED

**AC Validation:**
- AC-2.4.1 (multi-request detection & splitting): IMPLEMENTED — `request_splitter.py` + `email_poller.py` integration + tests
- AC-2.4.2 (single-request not falsely split): IMPLEMENTED — short-circuit for 0-1 items + LLM single-group support + tests
- AC-2.4.3 (independent sub-request tracking with parent link): IMPLEMENTED — `QuoteRequest.email_request_id` FK + independent status/index + tests

**Task Audit:** All 5 tasks verified as genuinely complete. No false [x] claims.

**Code Quality:** Clean implementation following architecture patterns. Proper error handling with graceful degradation. Structured logging with correct component/context format. Good defensive coding (bounds check on LLM output indices). `model_copy()` for immutability.

**Test Quality:** 14 new tests with real assertions, no placeholders. Coverage: model introspection, LLM mock chain, short-circuit paths, error paths, pipeline integration, parent-child tracking.

**Security:** No injection risks — splitter operates on structured data, not raw email. SQLAlchemy parameterized queries.

**Issues Found:** 1 MEDIUM (sprint-status.yaml missing from File List) — fixed during review.

### Change Log

- 2026-03-19: Code review passed — 1 MEDIUM issue fixed (File List completeness), story status → done
- 2026-03-19: Story 2.4 implementation complete — multi-request splitting with LLM-based grouping, QuoteRequest model, Alembic migration, pipeline integration, 14 new tests

### File List

New files:
- `src/quote_agent/models/quote_request.py`
- `src/quote_agent/services/request_splitter.py`
- `alembic/versions/98e0cffdcc69_add_quote_requests_table.py`
- `tests/unit/test_quote_request_model.py`
- `tests/unit/test_request_splitter.py`

Modified files:
- `src/quote_agent/models/__init__.py`
- `src/quote_agent/services/extraction_models.py`
- `src/quote_agent/services/email_poller.py`
- `tests/unit/test_email_poller.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
