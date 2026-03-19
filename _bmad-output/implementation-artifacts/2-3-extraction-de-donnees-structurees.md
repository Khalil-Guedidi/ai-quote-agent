# Story 2.3: Extraction de Données Structurées

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to extract structured data from the email (client identity, requested products, quantities, specifications),
So that the request is machine-readable and ready for product matching.

## Acceptance Criteria

1. **AC-2.3.1**: LLM-based extraction produces structured output
   - Given a cleaned email containing a quote request
   - When the agent runs extraction via LLM
   - Then it produces a structured output with: client name/identifier, list of requested products (description, quantity, specifications)
   - And the extraction completes within 10 seconds (NFR-P3)

2. **AC-2.3.2**: Missing fields are flagged, not hallucinated
   - Given a request with partial information (e.g., no quantity specified)
   - When extraction runs
   - Then missing fields are flagged as absent (null/None, not hallucinated)
   - And the structured output clearly indicates which fields are missing

3. **AC-2.3.3**: Status updated and reasoning trace logged
   - Given extraction is complete
   - When the result is stored
   - Then the email tracking record is updated with status "extracted"
   - And the extracted data is stored as JSON in `extracted_data` column
   - And the full reasoning trace is logged (structured JSON)

## Tasks / Subtasks

- [x] Task 1: Create Pydantic extraction models in `src/quote_agent/services/extraction_models.py` (AC: 1, 2)
  - [x] 1.1: Create `QuoteLineItem` model — `description: str`, `quantity: float | None`, `unit: str | None`, `specifications: str | None`, `reference: str | None`
  - [x] 1.2: Create `ExtractedQuoteRequest` model — `client_name: str | None`, `client_identifier: str | None`, `client_email: str | None`, `line_items: list[QuoteLineItem]`, `urgency: str | None`, `delivery_address: str | None`, `notes: str | None`, `raw_text: str`
  - [x] 1.3: Create `ExtractionResult` wrapper — `request: ExtractedQuoteRequest`, `confidence: float`, `missing_fields: list[str]`, `extraction_duration_ms: int`

- [x] Task 2: Add `extracted_data` column to `EmailRequest` model + Alembic migration (AC: 3)
  - [x] 2.1: Add `extracted_data: Mapped[dict | None] = mapped_column(JSON, default=None)` to `EmailRequest` in `src/quote_agent/models/email_request.py`
  - [x] 2.2: Generate Alembic migration: `uv run alembic revision --autogenerate -m "add extracted_data to email_requests"`
  - [x] 2.3: Test migration up/down: `uv run alembic upgrade head` / `uv run alembic downgrade -1`

- [x] Task 3: Create `extract()` function in `src/quote_agent/services/email_extractor.py` (AC: 1, 2)
  - [x] 3.1: Build system prompt instructing the LLM to extract structured data from French B2B industrial quote request emails, flag missing fields as null (never hallucinate), and output in the Pydantic schema
  - [x] 3.2: Use `llm_adapter.get_model("simple").with_structured_output(ExtractedQuoteRequest)` for guaranteed schema-conformant output
  - [x] 3.3: Implement `extract(cleaned_content: str, sender: str, subject: str) -> ExtractionResult` — calls LLM, measures duration, computes `missing_fields` list, returns typed result
  - [x] 3.4: Add 10-second timeout via `asyncio.wait_for()` to enforce NFR-P3
  - [x] 3.5: Handle LLM errors (timeout → `LLMTimeoutError`, auth/connection → `AdapterError`) — do NOT swallow exceptions

- [x] Task 4: Integrate extraction into the pipeline (AC: 3)
  - [x] 4.1: Extraction integrated inline in `_persist_emails()` — calls `extract()`, stores `extracted_data` as JSON, updates `status = "extracted"` (simplified from separate function as per inline integration pattern from Story 2.2)
  - [x] 4.2: Call extraction after successful cleaning in `EmailPollerService._persist_emails()` — for each newly cleaned email, call the extractor
  - [x] 4.3: If extraction fails, set `status = "extraction_failed"` and `error_message` — do NOT block the pipeline for other emails
  - [x] 4.4: Log structured extraction trace: `component: "services.email_extractor"`, include `email_request_id`, `line_item_count`, `missing_fields`, `duration_ms`

- [x] Task 5: Write tests (AC: 1, 2, 3)
  - [x] 5.1: Unit tests for Pydantic models in `tests/unit/test_extraction_models.py` (5 tests)
    - Test: `QuoteLineItem` with all fields populated
    - Test: `QuoteLineItem` with only description (all optional fields None)
    - Test: `ExtractedQuoteRequest` with multiple line items
    - Test: `ExtractedQuoteRequest` with missing client info (None, not hallucinated)
    - Test: `ExtractionResult.missing_fields` correctly lists null fields
  - [x] 5.2: Unit tests for `extract()` in `tests/unit/test_email_extractor.py` (8 tests)
    - Test: simple French quote request extracts client name and line items correctly
    - Test: email with partial info (no quantity) returns None for quantity, not a guess
    - Test: email with multiple products extracts all line items
    - Test: email with product references (e.g., "REF-12345") captures reference field
    - Test: extraction timeout raises `LLMTimeoutError`
    - Test: LLM adapter error raises `AdapterError`
    - Test: extraction duration is measured and returned
    - Test: empty email content returns empty line_items list (not an error)
  - [x] 5.3: Integration tests covered via poller tests — successful extraction updates `extracted_data` (JSON) and `status = "extracted"`, extraction failure sets `status = "extraction_failed"` and `error_message`
  - [x] 5.4: Update `test_email_poller.py` to verify extraction is called after cleaning (3 new tests)

## Dev Notes

### Architecture Compliance

- **Service layer**: `src/quote_agent/services/email_extractor.py` — new service for LLM-based data extraction. Architecture specifies services for orchestration/business logic. [Source: architecture.md#Services-Layer, architecture.md#Complete-Project-Directory-Structure]
- **Pydantic DTOs**: Extraction output models in `src/quote_agent/services/extraction_models.py` — NOT in `models/` (which is reserved for SQLAlchemy ORM models). These are service-layer DTOs (data transfer objects) following the architecture pattern of typed Pydantic models at system boundaries. [Source: architecture.md#Enforcement-Guidelines rule 7]
- **Database model extension**: Add `extracted_data` JSON column to existing `email_requests` table — do NOT create a new table. Extracted data is stored as JSON on the same record for simplicity and audit traceability. A separate `quote_requests` table will come in Story 2.4 when sub-requests need independent tracking. [Source: epics.md#Story-2.4]
- **Status machine**: `cleaned` → `extracted` (or `extraction_failed`). Extends the existing status flow: `received` → `cleaned` → `extracted`. [Source: architecture.md#email_request.py]
- **LLM adapter reuse**: The `OpenAICompatAdapter` and `get_model()` already exist. Use `get_model("simple").with_structured_output(ExtractedQuoteRequest)` — this is the modern LangChain approach for guaranteed structured output using Pydantic models. Do NOT use raw `invoke()` + manual JSON parsing. [Source: langchain docs — with_structured_output]
- **Structured logging**: Log extraction results with `component: "services.email_extractor"` following the JSON logging format. Include `email_request_id`, `line_item_count`, `missing_fields`, `duration_ms`. Never log the actual email content (security). [Source: architecture.md#Structured-Logging-Format]

### Existing Code to Extend

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/models/email_request.py` | `EmailRequest` with `raw_content`, `cleaned_content`, `status`, `error_message` | Add `extracted_data` column (nullable JSON) |
| `src/quote_agent/services/email_poller.py` | `_persist_emails()` calls cleaning inline after persist | Add extraction call after successful cleaning |
| `src/quote_agent/adapters/llm/openai_compat.py` | `OpenAICompatAdapter` with `get_model(complexity)` returning `ChatOpenAI` | Use `get_model("simple")` for extraction — simple complexity, no chain-of-thought needed |
| `src/quote_agent/adapters/llm/__init__.py` | `get_llm_adapter()` factory | Import and use in extractor |
| `src/quote_agent/exceptions.py` | `LLMTimeoutError`, `AdapterError`, `ValidationError` | Reuse for extraction error handling. Add `ExtractionError(QuoteAgentError)` if needed for extraction-specific failures |
| `tests/unit/test_email_poller.py` | Poller tests including cleaner integration | Add test verifying extractor is called after cleaning |

### Technical Implementation Details

**LLM Extraction approach — `with_structured_output`:**

```python
from langchain_openai import ChatOpenAI
from quote_agent.adapters.llm import get_llm_adapter
from quote_agent.services.extraction_models import ExtractedQuoteRequest

adapter = get_llm_adapter()
model = adapter.get_model("simple")
structured_model = model.with_structured_output(ExtractedQuoteRequest)

# Returns a validated Pydantic instance directly — no JSON parsing needed
result: ExtractedQuoteRequest = await structured_model.ainvoke([system_msg, user_msg])
```

This uses OpenAI's function calling / tool use under the hood, guaranteeing the output matches the Pydantic schema. The LLM provider handles JSON schema enforcement.

**System prompt design (French B2B industrial context):**

```python
EXTRACTION_SYSTEM_PROMPT = """You are a data extraction assistant for a French B2B industrial quote processing system.

Your task: Extract structured data from a quote request email. The emails are in French (sometimes English).

Rules:
- Extract ALL requested products as separate line items
- For each product: description, quantity (number), unit (e.g., "pièces", "mètres", "kg"), specifications, reference code
- Extract client identification: name, company, email, any identifier
- If a field is not mentioned in the email, set it to null — NEVER guess or hallucinate
- Product references may be codes like "REF-12345", "Art. 4567", catalog numbers
- Quantities may be written as "10 pcs", "10 unités", "une dizaine", "x10"
- French industrial terminology: "devis" = quote, "tarif" = price, "délai" = lead time, "livraison" = delivery

The email sender and subject are provided as additional context."""
```

**Missing fields detection:**

```python
def _compute_missing_fields(request: ExtractedQuoteRequest) -> list[str]:
    missing = []
    if request.client_name is None:
        missing.append("client_name")
    if request.client_identifier is None:
        missing.append("client_identifier")
    for i, item in enumerate(request.line_items):
        if item.quantity is None:
            missing.append(f"line_items[{i}].quantity")
        if item.reference is None:
            missing.append(f"line_items[{i}].reference")
    return missing
```

**Timeout enforcement (NFR-P3: < 10 seconds):**

```python
import asyncio

try:
    result = await asyncio.wait_for(
        structured_model.ainvoke(messages),
        timeout=10.0,
    )
except asyncio.TimeoutError:
    raise LLMTimeoutError("Extraction timed out after 10s (NFR-P3)")
```

**Integration into poller (`_persist_emails`):**

```python
# After successful cleaning:
try:
    extraction_result = await extract(
        cleaned_content=record.cleaned_content,
        sender=record.sender,
        subject=record.subject,
    )
    record.extracted_data = extraction_result.request.model_dump()
    record.status = "extracted"
    logger.info(
        "Extraction complete",
        extra={
            "component": "services.email_extractor",
            "context": {
                "email_request_id": str(record.id),
                "line_item_count": len(extraction_result.request.line_items),
                "missing_fields": extraction_result.missing_fields,
                "duration_ms": extraction_result.extraction_duration_ms,
            },
        },
    )
except (LLMTimeoutError, AdapterError) as exc:
    record.status = "extraction_failed"
    record.error_message = str(exc)
    logger.warning("Extraction failed for %s: %s", record.message_id, exc)
```

**Note on async**: `with_structured_output()` returns a runnable that supports `.ainvoke()` — fully async, no need for `asyncio.to_thread()`.

**Note on model choice**: Use `get_model("simple")` for extraction. Simple quote request extraction doesn't need chain-of-thought reasoning — a lighter model reduces latency and cost. The `simple_model` is configured via `LLM__SIMPLE_MODEL` env var.

### Project Structure Notes

New files:
- `src/quote_agent/services/extraction_models.py` — Pydantic DTOs for extraction output
- `src/quote_agent/services/email_extractor.py` — extraction service
- `alembic/versions/{hash}_add_extracted_data_to_email_requests.py` — auto-generated migration
- `tests/unit/test_extraction_models.py` — model unit tests
- `tests/unit/test_email_extractor.py` — extractor unit tests

Modified files:
- `src/quote_agent/models/email_request.py` — add `extracted_data` column
- `src/quote_agent/services/email_poller.py` — integrate extraction after cleaning
- `tests/unit/test_email_poller.py` — verify extractor integration

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Use raw `invoke()` + manual JSON parsing for extraction | Use `with_structured_output(PydanticModel)` — guaranteed schema compliance |
| Hallucinate missing fields (guess quantities, invent references) | Set missing fields to `None` — the system prompt explicitly forbids hallucination |
| Create a separate table for extracted data | Add `extracted_data` JSON column to `email_requests` — same record, audit trail. Separate table comes in Story 2.4 |
| Put Pydantic DTOs in `models/` directory | Put in `services/extraction_models.py` — `models/` is for SQLAlchemy ORM only |
| Use `get_model("complex")` for extraction | Use `get_model("simple")` — extraction is structured, no chain-of-thought needed |
| Parse extraction output as free text then regex | `with_structured_output` returns validated Pydantic instance directly |
| Log email content in extraction traces | Log only metadata: `email_request_id`, `line_item_count`, `missing_fields`, `duration_ms` |
| Block the pipeline if one email extraction fails | Catch exceptions per-email, set `extraction_failed` status, continue with next |
| Use `json.loads()` on LLM output | `with_structured_output` handles parsing — you get a Pydantic model instance |
| Add langchain, langgraph, or new dependencies | Everything needed is already installed: `langchain-openai`, `langchain-core`, `pydantic` |
| Create agent graph nodes for extraction | This story is a service-layer function. Agent graph (LangGraph) comes in Epic 4. Extraction is a simple LLM call, not an agentic loop |

### Scope Boundaries

- **IN scope**: Pydantic extraction models, LLM-based structured extraction via `with_structured_output`, `extracted_data` JSON column, status `extracted`/`extraction_failed`, system prompt for French B2B industrial emails, 10s timeout, missing field detection, structured logging, unit + integration tests
- **OUT of scope**: Multi-request splitting (Story 2.4), prompt injection defense (Story 2.5), agent graph / LangGraph nodes (Epic 4), product matching / search (Epic 3), confidence scoring (Epic 4), few-shot examples from memory (Epic 6), structured extraction caching, extraction configuration via settings (hardcoded prompt sufficient for MVP)

### Previous Story Intelligence (Story 2.2)

- **Inline integration pattern**: Story 2.2 integrated cleaning inline in `_persist_emails()`. Continue this pattern for extraction — call after cleaning in the same flow. The extraction is an async LLM call (not pure CPU like cleaning), but it's still sequential per-email within the persist loop.
- **Safety valve**: Story 2.2 added a >90% stripping safety valve. For extraction, the equivalent safety check is: if `cleaned_content` is empty or very short (< 10 chars), skip extraction and set status to `extraction_failed` with message "Content too short for extraction".
- **Status machine continuity**: `received` → `cleaned` → `extracted`. If cleaning fails, extraction is skipped. Only attempt extraction on emails with `status = "cleaned"`.
- **Module-level compiled patterns**: Story 2.2 used module-level compiled regexes. For extraction, the system prompt is a module-level constant string (no compilation needed, but same pattern of constants at module top).
- **Error handling pattern**: Story 2.2 catches exceptions per-email and sets `cleaning_failed` without blocking pipeline. Apply same pattern: catch `LLMTimeoutError`/`AdapterError` per-email, set `extraction_failed`, continue.
- **`from __future__ import annotations`**: Continue using for forward references.
- **Test mocking approach**: For extractor tests, mock `get_llm_adapter()` to return a mock adapter whose `get_model("simple").with_structured_output().ainvoke()` returns a predefined `ExtractedQuoteRequest` instance. This avoids real LLM calls in unit tests.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Last commits:
- `6b5e29e` feat: add LinkedIn French industrial jargon post (Story T.5)
- `65fbbe1` feat: add email content cleaning with French/English pattern support (Story 2.2)
- `97ff86c` feat: add IMAP email reception pipeline with polling and persistence (Story 2.1)

110 tests passing, CI pipeline operational. Story 2.2 done and committed.

### References

- [Source: architecture.md#Email-Processing-Extraction] — FR1-4, inbound pipeline, cleaning → extraction
- [Source: architecture.md#Complete-Project-Directory-Structure] — services layer for business logic
- [Source: architecture.md#Naming-Patterns] — snake_case files, PascalCase classes
- [Source: architecture.md#Data-Architecture] — PostgreSQL, SQLAlchemy, Alembic, JSON columns
- [Source: architecture.md#Enforcement-Guidelines] — typed Pydantic DTOs, mypy strict, structured logging
- [Source: architecture.md#Agent-State-LangGraph] — `ParsedRequest` in agent state (future — Epic 4 will consume extraction output)
- [Source: architecture.md#Prompt-Injection-Defense] — extraction operates on cleaned content, prompt injection defense is Story 2.5
- [Source: architecture.md#Technical-Constraints] — French language first, LLM-agnostic
- [Source: epics.md#Story-2.3] — acceptance criteria, user story, NFR-P3
- [Source: epics.md#Story-2.4] — next story context (multi-request splitting operates on extracted data)
- [Source: 2-2-nettoyage-du-contenu-email.md] — previous story patterns, inline integration, error handling
- [Source: LangChain docs — with_structured_output] — recommended approach for Pydantic-based structured extraction

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Ruff auto-fix applied for import sorting (I001) and `asyncio.TimeoutError` → `TimeoutError` (UP041)
- Timeout test initially failed due to nested `asyncio.wait_for()` — fixed by patching `_EXTRACTION_TIMEOUT` to 0.05s instead of wrapping in outer wait_for

### Completion Notes List

- ✅ Task 1: Created 3 Pydantic models (`QuoteLineItem`, `ExtractedQuoteRequest`, `ExtractionResult`) in `services/extraction_models.py`
- ✅ Task 2: Added `extracted_data` JSON column to `EmailRequest` + Alembic migration (up/down verified)
- ✅ Task 3: Created `extract()` function with LLM structured output, 10s timeout, missing field detection, confidence scoring, short content safety valve
- ✅ Task 4: Integrated extraction into `_persist_emails()` inline after cleaning, with per-email error handling and structured logging
- ✅ Task 5: 16 new tests (5 model + 8 extractor + 3 poller integration), total 125 passing, 0 regressions

### Change Log

- 2026-03-19: Story 2.3 implementation complete — LLM-based structured extraction with `with_structured_output`, Pydantic DTOs, Alembic migration, pipeline integration, 16 new tests
- 2026-03-19: Code review passed — 3 fixes applied: renamed misleading `start_ms` → `start_s`, replaced in-place mutation with `model_copy()`, added comment on placeholder confidence heuristic

### File List

New files:
- `src/quote_agent/services/extraction_models.py`
- `src/quote_agent/services/email_extractor.py`
- `alembic/versions/20a676fe8a38_add_extracted_data_to_email_requests.py`
- `tests/unit/test_extraction_models.py`
- `tests/unit/test_email_extractor.py`

Modified files:
- `src/quote_agent/models/email_request.py`
- `src/quote_agent/services/email_poller.py`
- `tests/unit/test_email_poller.py`
