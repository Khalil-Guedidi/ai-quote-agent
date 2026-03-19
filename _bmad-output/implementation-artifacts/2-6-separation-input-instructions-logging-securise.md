# Story 2.6: Séparation Input/Instructions & Logging Sécurisé

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **IT operator (Laurent)**,
I want a strict boundary between untrusted email data and agent instructions with secure logging,
So that every email processing step is auditable without leaking sensitive data.

## Acceptance Criteria

1. **AC-2.6.1**: LLM input/instruction separation verified end-to-end
   - Given the agent processes an email through the pipeline
   - When any LLM call is made (extraction, splitting)
   - Then the system prompt and email content are in separate, clearly delimited sections
   - And no email content appears in the system instruction zone

2. **AC-2.6.2**: Confidential data redacted from logs
   - Given an email contains confidential information (client names, pricing references, email addresses)
   - When the processing is logged
   - Then structured JSON logs capture the decision process
   - And confidential data is redacted from logs (log_redactor active)

3. **AC-2.6.3**: Complete decision chain traceable
   - Given any email enters the pipeline
   - When processing completes (success or failure)
   - Then the complete decision chain is traceable: reception → cleaning → extraction → split
   - And the email tracking record reflects the final state

## Tasks / Subtasks

- [x] Task 1: Create `src/quote_agent/security/log_redactor.py` — confidential data redaction (AC: 2)
  - [x] 1.1: Create `RedactionResult` Pydantic DTO — `redacted_text: str`, `original_text: str`, `redactions_applied: list[RedactionMatch]`, `redaction_count: int`
  - [x] 1.2: Create `RedactionMatch` Pydantic DTO — `category: str`, `matched_text: str`, `replacement: str`, `position: int`
  - [x] 1.3: Define compiled regex patterns for confidential data detection:
    - **Email addresses**: standard email regex → replace with `[REDACTED_EMAIL]`
    - **Phone numbers**: French formats (01-06, +33) → replace with `[REDACTED_PHONE]`
    - **Pricing patterns**: amounts with currency symbols/indicators (`€`, `EUR`, `prix`, `tarif`, `remise`, digit sequences followed by `€` or `EUR`) → replace with `[REDACTED_PRICE]`
    - **IBAN/bank account**: FR/IBAN patterns → replace with `[REDACTED_IBAN]`
    - **Reference codes with client context**: client-specific identifiers if they contain names → only redact in log context, not in processing
  - [x] 1.4: Create `redact(text: str) -> RedactionResult` function — detects confidential patterns, replaces with category-labeled placeholders
  - [x] 1.5: Create `redact_context(context: dict) -> dict` function — recursively walks a dict (used for structured log `context` fields), redacting string values that match confidential patterns. Non-string values pass through unchanged.
  - [x] 1.6: Log redaction activity with structured logging: `component: "security.log_redactor"`, include `redaction_count`, `categories`

- [x] Task 2: Create `src/quote_agent/audit/logger.py` — structured JSON logging setup (AC: 2, 3)
  - [x] 2.1: Create `setup_logging(log_level: str) -> None` function that configures Python's root logger:
    - JSON formatter that outputs: `timestamp` (ISO 8601 UTC), `level`, `component` (from `extra["component"]` or logger name), `message`, `context` (from `extra["context"]` or empty dict)
    - Single `StreamHandler` to stdout
    - Remove any default handlers before adding ours
  - [x] 2.2: Create a custom `logging.Formatter` subclass `JSONLogFormatter` that:
    - Serializes each log record to single-line JSON matching architecture spec format
    - Extracts `component` and `context` from `extra` dict
    - Applies `redact_context()` to the `context` dict before serialization — this is where redaction happens automatically
    - Handles missing `component`/`context` gracefully (defaults to logger name / empty dict)
    - Serializes datetime as ISO 8601 UTC
  - [x] 2.3: Do NOT add structlog or any new dependency — use standard `logging` module with custom formatter (matches current codebase pattern)

- [x] Task 3: Integrate structured logging into application startup (AC: 2, 3)
  - [x] 3.1: Call `setup_logging(settings.app.log_level)` in `src/quote_agent/main.py` during `lifespan()` startup, before any other initialization
  - [x] 3.2: Verify that all existing `logger.info/warning/error` calls with `extra={"component": ..., "context": ...}` automatically get JSON-formatted with redaction — no changes needed to individual service files
  - [x] 3.3: Ensure log output is single-line JSON per record (no multiline, no Python default format)

- [x] Task 4: Add pipeline traceability logging to `email_poller.py` (AC: 3)
  - [x] 4.1: Add structured log at email reception: `logger.info("Email received", extra={"component": "services.email_poller", "context": {"email_request_id": str(record.id), "message_id": record.message_id, "sender": record.sender, "subject": record.subject, "status": "received"}})` — right after `session.flush()` (line ~157)
  - [x] 4.2: Add structured log at cleaning complete: `logger.info("Email cleaned", extra={"component": "services.email_cleaner", "context": {"email_request_id": str(record.id), "status": "cleaned", "raw_length": len(incoming.raw_content), "cleaned_length": len(record.cleaned_content)}})` — right after `record.status = "cleaned"` (line ~161)
  - [x] 4.3: Add structured log at cleaning failure with error context (already exists at line ~165 but needs component/context structure)
  - [x] 4.4: Existing extraction and splitting logs already have `component`/`context` structure — verify they are adequate, no changes needed
  - [x] 4.5: Add structured log at pipeline completion for each email: `logger.info("Email pipeline complete", extra={"component": "services.email_poller", "context": {"email_request_id": str(record.id), "message_id": record.message_id, "final_status": record.status}})` — right before `persisted += 1` (line ~256)

- [x] Task 5: Update `src/quote_agent/security/__init__.py` with new exports (AC: all)
  - [x] 5.1: Add exports: `redact`, `RedactionResult`, `RedactionMatch`, `redact_context`

- [x] Task 6: Update `src/quote_agent/audit/__init__.py` with public exports (AC: all)
  - [x] 6.1: Export `setup_logging`, `JSONLogFormatter`

- [x] Task 7: Write tests (AC: 1, 2, 3)
  - [x] 7.1: Unit tests for `log_redactor.py` in `tests/unit/test_log_redactor.py` (13 tests)
    - Test: clean text without confidential data passes through unchanged
    - Test: email address detected and replaced with `[REDACTED_EMAIL]`
    - Test: French phone number (06 xx xx xx xx) detected and replaced
    - Test: International phone (+33) detected and replaced
    - Test: Price with € symbol detected and replaced with `[REDACTED_PRICE]`
    - Test: Price with "EUR" detected and replaced
    - Test: French pricing terms (prix, tarif, remise + amount) detected
    - Test: IBAN pattern detected and replaced
    - Test: Multiple confidential items in single text — all redacted
    - Test: `redact_context()` recursively redacts string values in nested dict
    - Test: `redact_context()` preserves non-string values (int, float, bool, None)
    - Test: Empty string and None handled gracefully
    - Test: `redact_context()` handles list values with mixed types
  - [x] 7.2: Unit tests for `audit/logger.py` in `tests/unit/test_audit_logger.py` (9 tests)
    - Test: `setup_logging()` configures root logger with JSON formatter
    - Test: `JSONLogFormatter` outputs valid single-line JSON
    - Test: JSON output contains required fields: timestamp, level, component, message, context
    - Test: `component` extracted from `extra["component"]`
    - Test: `context` extracted from `extra["context"]`
    - Test: Missing `component`/`context` defaults to logger name / empty dict
    - Test: Context values are redacted (email addresses in context dict)
    - Test: Timestamp is ISO 8601 UTC format
  - [x] 7.3: Integration test verifying pipeline traceability (2 tests)
    - Test: Successful email processing produces structured logs for each stage (received → cleaned → extracted → split → complete)
    - Test: Failed processing (extraction failure) produces logs up to failure point with error context

## Dev Notes

### Architecture Compliance

- **Log Redactor**: `src/quote_agent/security/log_redactor.py` — matches architecture spec: "Confidential data (pricing, client info) stripped before logging" [Source: architecture.md#Authentication-Security, line 249]
- **Structured Logging**: `src/quote_agent/audit/logger.py` — matches architecture spec JSON format with `timestamp`, `level`, `component`, `message`, `context` [Source: architecture.md#Structured-Logging-Format, lines 380-396]
- **Audit Layer**: "`audit/` Calls: models/ (DB), security/log_redactor" [Source: architecture.md#Component-Boundaries, line 765] — the logger calls `redact_context()` from the security layer
- **Anti-Pattern**: "`Confidential data in logs` → Use log sanitizer systematically" [Source: architecture.md#Anti-Patterns-to-Avoid, line 493]
- **NFR**: "Confidential data (pricing, client info) never appears in external-facing logs or traces" [Source: prd.md#Security, line 462]

### Existing Code to Extend

| File | What Exists | What to Do |
|------|-------------|------------|
| `src/quote_agent/security/__init__.py` | Exports sanitize, isolate_input, etc. (18 lines) | Add log_redactor exports: `redact`, `RedactionResult`, `RedactionMatch`, `redact_context` |
| `src/quote_agent/audit/__init__.py` | Empty (just docstring, 1 line) | Add exports: `setup_logging`, `JSONLogFormatter` |
| `src/quote_agent/main.py` | `lifespan()` function handles startup/shutdown | Add `setup_logging()` call at top of startup sequence |
| `src/quote_agent/services/email_poller.py` | `_persist_emails()` with inline pipeline (266 lines) | Add structured traceability logs at reception, cleaning, and pipeline completion |
| `src/quote_agent/config.py` | `AppSettings.log_level = "INFO"` | No changes needed — logger reads this existing setting |

### Technical Implementation Details

**Log redactor approach — regex-based pattern detection with category-labeled replacement:**

```python
# Example: before and after redaction
"Client dupont@acme.fr requested 500€ of tubes"
→ "Client [REDACTED_EMAIL] requested [REDACTED_PRICE] of tubes"

# In context dicts:
{"sender": "dupont@acme.fr", "item_count": 3, "total": "1500€"}
→ {"sender": "[REDACTED_EMAIL]", "item_count": 3, "total": "[REDACTED_PRICE]"}
```

**Redaction categories:**

| Category | Pattern Examples | Replacement |
|----------|-----------------|-------------|
| Email | `user@domain.com` | `[REDACTED_EMAIL]` |
| Phone | `06 12 34 56 78`, `+33 1 23 45 67 89` | `[REDACTED_PHONE]` |
| Price | `500€`, `1500 EUR`, `prix: 250`, `remise 10%` | `[REDACTED_PRICE]` |
| IBAN | `FR76 3000 1007 ...` | `[REDACTED_IBAN]` |

**JSONLogFormatter — automatic redaction in the formatter layer:**

```python
class JSONLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = getattr(record, "context", {})
        component = getattr(record, "component", record.name)

        # Automatic redaction of context values
        redacted_context = redact_context(context) if context else {}

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": component,
            "message": record.getMessage(),
            "context": redacted_context,
        }
        return json.dumps(log_entry, default=str)
```

This approach means:
1. **Zero changes to existing logging calls** — all `logger.info(..., extra={"component": ..., "context": ...})` calls automatically get JSON + redaction
2. **Centralized redaction** — happens in the formatter, not at each call site
3. **No new dependencies** — standard `logging` module + `json.dumps`

**Traceability logging — complete pipeline audit trail:**

Each email produces a sequence of structured logs:
```json
{"timestamp": "...", "level": "INFO", "component": "services.email_poller", "message": "Email received", "context": {"email_request_id": "...", "message_id": "...", "status": "received"}}
{"timestamp": "...", "level": "INFO", "component": "services.email_cleaner", "message": "Email cleaned", "context": {"email_request_id": "...", "status": "cleaned", "raw_length": 1234, "cleaned_length": 567}}
{"timestamp": "...", "level": "INFO", "component": "services.email_extractor", "message": "Extraction complete", "context": {"email_request_id": "...", "line_item_count": 3, "missing_fields": [], "duration_ms": 2100}}
{"timestamp": "...", "level": "INFO", "component": "services.request_splitter", "message": "Request splitting complete", "context": {"email_request_id": "...", "split_count": 2, "duration_ms": 1800}}
{"timestamp": "...", "level": "INFO", "component": "services.email_poller", "message": "Email pipeline complete", "context": {"email_request_id": "...", "final_status": "split"}}
```

All filterable by `email_request_id` to reconstruct the full decision chain.

**AC-2.6.1 (input/instruction separation) — already implemented in Story 2.5:**

Story 2.5 delivered `input_isolation.py` with delimiter-based structural separation and `build_extraction_messages()` that enforces system/human message split. AC-2.6.1 is a verification criterion — verify with tests that:
- `build_extraction_messages()` produces SystemMessage with instructions only (no email content)
- `build_extraction_messages()` produces HumanMessage with delimited email content
- `SPLITTING_SYSTEM_PROMPT` contains isolation instructions
- No code path in extractor or splitter injects email content into system prompts

These verification tests belong in the existing `test_input_isolation.py` and `test_email_extractor.py` if not already present. Check existing tests before adding duplicates.

### Project Structure Notes

New files:
- `src/quote_agent/security/log_redactor.py` — confidential data redaction (security domain)
- `src/quote_agent/audit/logger.py` — JSON log formatter with automatic redaction
- `tests/unit/test_log_redactor.py` — redaction unit tests
- `tests/unit/test_audit_logger.py` — logging setup unit tests

Modified files:
- `src/quote_agent/security/__init__.py` — add log_redactor exports
- `src/quote_agent/audit/__init__.py` — add logger exports
- `src/quote_agent/main.py` — call `setup_logging()` at startup
- `src/quote_agent/services/email_poller.py` — add traceability logs

### Critical Anti-Patterns to Avoid

| Do NOT | Do Instead |
|--------|-----------|
| Add `structlog` or any new dependency | Use standard `logging` module with custom `JSONLogFormatter` — the codebase already uses `logging.getLogger(__name__)` everywhere |
| Redact data in individual service files | Redact centrally in `JSONLogFormatter` via `redact_context()` — one place, all logs covered |
| Change existing `logger.info/warning/error` calls | The new formatter intercepts all log records — existing calls automatically become JSON + redacted |
| Log the original (non-redacted) text alongside redacted | That defeats the purpose — only the redacted version appears in output |
| Redact data during processing (in the pipeline) | Redaction is for LOGGING only — the actual processing uses full unredacted data |
| Strip client names from processing context | Client names in `context` dicts (like `sender`) get redacted in logs, but the actual `email_request` DB record retains them |
| Create an audit log DB table in this story | Architecture places audit_logs table in Epic 7 (FR37-41). This story sets up the logging framework only |
| Modify `email_cleaner.py` or `email_extractor.py` core logic | Only add traceability logs to `email_poller.py` — the pipeline orchestrator |
| Use `print()` or `logging.info("string")` without structure | Always use `extra={"component": ..., "context": {...}}` for all new logs |
| Redact the `message` field of logs | Redact only the `context` dict — messages should be generic ("Email received", "Extraction complete") without confidential data |

### Scope Boundaries

- **IN scope**: `log_redactor.py` with regex-based confidential data detection and replacement, `audit/logger.py` with `JSONLogFormatter` and `setup_logging()`, automatic redaction in formatter, traceability logs in `email_poller.py` (received/cleaned/complete), verification of input/instruction separation (AC-2.6.1), unit tests for all new code
- **OUT of scope**: Audit log DB table (Epic 7), audit trail immutability (Story 7.2), alert system (Story 7.3), reasoning traces (Story 7.1), web UI log viewer (Story 7.7), structlog integration, new dependencies, modifying extraction/splitting logic, email_cleaner changes

### Previous Story Intelligence (Story 2.5)

- **Module-level functions, not classes**: Story 2.5 used `sanitize()` and `isolate_input()` as module-level functions with Pydantic DTOs. Follow the same pattern for `redact()` and `redact_context()`.
- **`from __future__ import annotations`**: Continue using in all new files.
- **Structured logging pattern**: `extra={"component": "...", "context": {...}}` — already established in sanitizer, extractor, splitter, and poller. The new logger framework formalizes this.
- **Existing test count**: 164 tests pass. Don't break them. The new JSON formatter will change log output format — ensure no tests assert on specific log format strings.
- **Duration measurement**: Use `time.monotonic()` if any timing is needed (consistent with previous stories).
- **Security module exports**: Follow the `__all__` pattern in `security/__init__.py`.
- **Code review feedback from Story 2.5**: (H1) Fixed severity_max bug with explicit if/elif/else. (M1) Moved `EXTRACTION_SYSTEM_PROMPT` to `input_isolation.py` to avoid circular dependency. Watch for similar module boundary issues with log_redactor imports.

### Git Intelligence

Recent commit pattern: `feat: add <description> (Story X.Y)`

Last commits:
- `bf6ab5b` feat: add prompt injection defense with input isolation and sanitization (Story 2.5)
- `cfdc066` feat: add LinkedIn error & edge cases post (Story T.6)
- `79db7b4` feat: add multi-request splitting with LLM-based line item grouping (Story 2.4)

164 tests passing, CI pipeline operational.

### References

- [Source: architecture.md#Authentication-Security] — "Confidential data (pricing, client info) stripped before logging"
- [Source: architecture.md#Structured-Logging-Format] — JSON format: timestamp, level, component, message, context
- [Source: architecture.md#Component-Boundaries] — "Audit Layer: Calls: models/ (DB), security/log_redactor"
- [Source: architecture.md#Anti-Patterns-to-Avoid] — "Confidential data in logs → Use log sanitizer systematically"
- [Source: architecture.md#Complete-Project-Directory-Structure] — `security/log_redactor.py`, `audit/logger.py`
- [Source: prd.md#Security, line 462] — "Confidential data (pricing, client info) never appears in external-facing logs"
- [Source: prd.md#Audit-Traceability, line 171] — "Every agent decision must be auditable — immutable logs"
- [Source: prd.md#FR37] — "log every agent decision with full reasoning trace (structured logs)"
- [Source: prd.md#FR39] — "trace the complete decision chain from email to draft quote"
- [Source: epics.md#Story-2.6] — acceptance criteria, user story
- [Source: 2-5-defense-contre-injection-de-prompt-couches-1-2.md] — previous story patterns, module-level functions, sanitization approach
- [Source: email_poller.py] — pipeline orchestration with inline processing, existing structured logs at lines 181-233

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- ✅ Task 1: Created `log_redactor.py` with `RedactionResult`/`RedactionMatch` DTOs, compiled regex patterns for email/phone/price/IBAN, `redact()` and `redact_context()` functions
- ✅ Task 2: Created `audit/logger.py` with `JSONLogFormatter` (auto-redaction via `redact_context()`) and `setup_logging()` — no new dependencies, standard `logging` module only
- ✅ Task 3: Integrated `setup_logging()` call at top of `lifespan()` in `main.py`, before any other initialization
- ✅ Task 4: Added 4 traceability logs to `email_poller.py`: "Email received", "Email cleaned", "Cleaning failed" (restructured), "Email pipeline complete". Verified existing extraction/splitting logs are adequate.
- ✅ Task 5: Updated `security/__init__.py` with `redact`, `RedactionResult`, `RedactionMatch`, `redact_context` exports
- ✅ Task 6: Updated `audit/__init__.py` with `setup_logging`, `JSONLogFormatter` exports
- ✅ Task 7: 24 tests total — 13 unit tests for log_redactor, 9 unit tests for audit logger, 2 integration tests for pipeline traceability
- All 188 tests pass (164 existing + 24 new), 0 regressions

### Change Log

- 2026-03-19: Story 2.6 implementation complete — log redactor, JSON structured logging, pipeline traceability, 24 tests
- 2026-03-19: Code review — fixed H1 (recursive logging noise from redact() during formatting) and M1 (price regex over-matching all percentages). 188 tests pass, 0 regressions.

### File List

New files:
- `src/quote_agent/security/log_redactor.py`
- `src/quote_agent/audit/logger.py`
- `tests/unit/test_log_redactor.py`
- `tests/unit/test_audit_logger.py`
- `tests/integration/test_pipeline_traceability.py`

Modified files:
- `src/quote_agent/security/__init__.py`
- `src/quote_agent/audit/__init__.py`
- `src/quote_agent/main.py`
- `src/quote_agent/services/email_poller.py`
