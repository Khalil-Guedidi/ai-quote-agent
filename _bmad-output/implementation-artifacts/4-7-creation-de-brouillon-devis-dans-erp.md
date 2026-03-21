# Story 4.7: Cr&eacute;ation de Brouillon Devis dans l'ERP

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **sales rep (Sophie)**,
I want the agent to create draft quotes in Odoo with the matched products and quantities,
So that I find ready-to-validate drafts in my ERP when I start my day.

## Acceptance Criteria

1. **AC-1: Draft quote creation in Odoo**
   Given a high-confidence match has passed self-review
   When the agent creates a draft quote
   Then a draft quotation (`sale.order` in "draft" state) is created in Odoo with: client (`partner_id`), product(s), quantities, unit prices
   And the draft uses draft-only access (never sent directly -- FR29, principle of least privilege)

2. **AC-2: Universal quote format (UniversalQuote DTO)**
   Given the agent produces a quote
   When it generates the ERP record
   Then the quote is first produced as a `UniversalQuote` Pydantic DTO (FR32)
   And the `OdooAdapter.create_draft_quote()` translates it to Odoo-specific `sale.order.create()` XML-RPC calls

3. **AC-3: Graceful degradation on ERP unavailability**
   Given the ERP is temporarily unavailable when the draft should be created
   When creation fails after retry
   Then the adapter retries with exponential backoff (reuse `_retry_with_backoff`)
   And if all retries fail, a structured error is returned with `retries_exhausted=True` for future queue/orchestration layer (NFR-R3)
   And a structured log is emitted for alerting

4. **AC-4: UniversalQuote and QuoteDraftResult DTOs**
   Given the ERP adapter models module exists
   When a draft quote is created
   Then it uses typed Pydantic DTOs (`UniversalQuote`, `UniversalQuoteLine`, `QuoteDraftResult`) -- never raw `dict`

5. **AC-5: ERPAdapter Protocol updated**
   Given the ERPAdapter Protocol class
   When the create method is added
   Then `create_draft_quote(self, quote: UniversalQuote) -> QuoteDraftResult` is defined in the Protocol

6. **AC-6: CLI command for draft creation**
   Given the CLI is available
   When the user runs `uv run quote-agent draft-create --client <id> --product <id> --quantity <n>`
   Then it creates a draft quote in Odoo and displays the draft ID and order reference
   And supports `--json` output flag
   And supports `--price <unit_price>` optional override (defaults to product's Odoo price)
   And supports `--description <text>` optional line description

7. **AC-7: Unit tests for all new methods**
   Given the new adapter methods and CLI command
   When tests are run
   Then all new public methods have unit tests with mocked XML-RPC calls
   And code passes `ruff check` and `mypy --strict`

8. **AC-8: Structured logging and audit**
   Given any draft creation operation
   When a draft is created (success or failure)
   Then structured logs are emitted with component="adapters.erp.odoo", context (partner_id, product_count, draft_id, duration_ms)
   And pricing data is auto-redacted via existing JSONLogFormatter

## Tasks / Subtasks

- [x] Task 1: Add UniversalQuote DTOs to `adapters/erp/models.py` (AC: #4)
  - [x] 1.1 Add `UniversalQuoteLine` Pydantic DTO (fields: product_id: int, product_ref: str | None, product_name: str, quantity: float, unit_price: float, description: str | None)
  - [x] 1.2 Add `UniversalQuote` Pydantic DTO (fields: client_id: str, client_name: str, lines: list[UniversalQuoteLine], delivery_date: str | None, notes: str | None)
  - [x] 1.3 Add `QuoteDraftResult` Pydantic DTO (fields: odoo_id: int, order_reference: str, state: str, line_count: int)

- [x] Task 2: Extend ERPAdapter Protocol (AC: #5)
  - [x] 2.1 Add `create_draft_quote(self, quote: UniversalQuote) -> QuoteDraftResult` to `protocol.py`

- [x] Task 3: Implement Odoo draft creation in `odoo.py` (AC: #1, #2, #3)
  - [x] 3.1 Add `_CREATE_DRAFT_TIMEOUT = 30.0` constant
  - [x] 3.2 Implement `_build_odoo_order_values(quote: UniversalQuote, partner_odoo_id: int) -> dict` helper that builds the Odoo `sale.order.create` values dict with `partner_id` and `order_line` tuples `[0, 0, {...}]`
  - [x] 3.3 Implement `create_draft_quote()` method:
    - Resolve client: use `get_client(quote.client_id)` to get `partner_odoo_id` (Odoo integer ID)
    - Build order values via helper
    - Call `sale.order.create([values])` via `asyncio.to_thread()` wrapped in `asyncio.wait_for()`
    - Read back the created order to get `name` (order reference like "SO042")
    - Return `QuoteDraftResult`
  - [x] 3.4 Wrap creation in `_retry_with_backoff()` for resilience
  - [x] 3.5 Add structured logging with component, context, duration_ms

- [x] Task 4: Add CLI `draft-create` command (AC: #6)
  - [x] 4.1 Create `src/quote_agent/cli/draft_create.py` with implementation
  - [x] 4.2 Register command in `cli/main.py` following existing pattern (lazy import)
  - [x] 4.3 Support `--client <id>`, `--product <id>`, `--quantity <n>` required flags
  - [x] 4.4 Support `--price <float>`, `--description <text>` optional flags
  - [x] 4.5 Support `--json` output flag
  - [x] 4.6 Build a `UniversalQuote` from CLI args, call `create_draft_quote()`, display result

- [x] Task 5: Add structured logging (AC: #8)
  - [x] 5.1 Log draft creation operations with component="adapters.erp.odoo", context={operation: "create_draft_quote", partner_id, product_count, draft_id, duration_ms}
  - [x] 5.2 Ensure prices auto-redacted by existing JSONLogFormatter

- [x] Task 6: Unit tests (AC: #7)
  - [x] 6.1 Test `UniversalQuote`, `UniversalQuoteLine`, `QuoteDraftResult` DTO construction and validation
  - [x] 6.2 Test `_build_odoo_order_values()` -- correct partner_id, order_line tuple format `[0, 0, {...}]`, optional delivery_date
  - [x] 6.3 Test `create_draft_quote()` -- success (mock XML-RPC create + read), client not found error, connection error, timeout
  - [x] 6.4 Test retry logic for create -- verify exponential backoff on transient failure
  - [x] 6.5 Test CLI `draft-create` -- success, JSON output, missing required flags, ERP error handling
  - [x] 6.6 Test Protocol compliance -- verify `OdooAdapter` satisfies updated `ERPAdapter` Protocol with `create_draft_quote`

## Dev Notes

### What Already Exists (DO NOT Recreate)

- **ERP adapter structure**: `src/quote_agent/adapters/erp/` with `protocol.py`, `models.py`, `odoo.py`, `__init__.py` -- extend these files, do NOT create new adapter modules
- **`OdooAdapter` class** in `odoo.py` (545 lines): already has `health_check()`, `get_products()`, `get_client()`, `get_client_orders()`, `get_product_by_id()`, `_ensure_uid()`, `_retry_with_backoff()`
- **Existing DTOs** in `models.py`: `Product`, `ProductFilter`, `IngestionResult`, `OdooVersionInfo`, `Client`, `ClientOrderHistory`, `ClientFilter`
- **XML-RPC pattern**: `asyncio.to_thread(proxy.execute_kw, ...)` wrapped in `asyncio.wait_for()` -- follow this exact pattern
- **`_odoo_str()` helper**: converts Odoo `False` to `None`
- **`_retry_with_backoff()`**: exponential backoff (3 retries, base=1s, max=8s) -- reuse for draft creation
- **Timeout constants**: `_HEALTH_CHECK_TIMEOUT = 5.0`, `_GET_PRODUCTS_TIMEOUT = 30.0`, `_GET_CLIENT_TIMEOUT = 30.0`, etc.
- **Structured logging pattern**: `logger.info("...", extra={"context": {...}})` with component, operation, duration_ms
- **Router** in `agent/nodes/router.py`: already emits `action="proceed_to_draft"` for high-confidence matches -- Story 4.8 will wire this to the draft creator
- **Exception hierarchy**: `ERPConnectionError(AdapterError)` in `exceptions.py`

### Odoo XML-RPC API Details for Draft Creation

**Creating a sale.order** -- Odoo model: `sale.order`
- Method: `create` (not `search_read`)
- Call: `execute_kw(db, uid, api_key, "sale.order", "create", [values_dict])`
- Returns: integer ID of the created `sale.order` record

**Values dict structure:**
```python
values = {
    "partner_id": partner_odoo_id,   # int -- Odoo res.partner ID
    "order_line": [                   # list of create tuples
        [0, 0, {                      # [0, 0, vals] = Odoo "create" notation
            "product_id": product_odoo_id,    # int -- Odoo product.product ID
            "product_uom_qty": quantity,      # float
            "price_unit": unit_price,         # float
            "name": description,              # str -- line description
        }],
        # ... more lines
    ],
}
# Optional: "commitment_date": "2026-04-01"  (delivery date, ISO format string)
```

**Reading back the created order** (to get reference):
- `execute_kw(db, uid, api_key, "sale.order", "read", [order_id], {"fields": ["name", "state", "order_line"]})`
- `name` = order reference like "SO042"
- `state` = "draft" (confirmed by default on create)
- `order_line` = list of line IDs

**Key Odoo behaviors:**
- `sale.order.create()` automatically sets `state = "draft"` -- no need to specify
- `partner_id` MUST be the integer Odoo ID (not the string ref) -- resolve via `get_client()` first
- `product_id` MUST be the integer Odoo product ID -- resolve from search results or `get_product_by_id()`
- If `price_unit` is 0 or omitted, Odoo uses the product's default price list
- The `[0, 0, {...}]` tuple is Odoo's ORM create notation (0 = create, vs 1 = update, 2 = delete)

### Prototype Reference

The prototype at `prototype/scripts/e2e-quote-pipeline.py` (lines 187-203) shows the full pattern:
```python
def odoo_create_draft_quote(session, uid, partner_id, order_lines, delivery_date=None):
    values = {
        "partner_id": partner_id,
        "order_line": [[0, 0, {
            "product_id": line["product_id"],
            "product_uom_qty": line["quantity"],
            "price_unit": line["price_unit"],
            "name": line["description"],
        }] for line in order_lines],
    }
    if delivery_date:
        values["commitment_date"] = delivery_date
    return odoo_execute_kw(session, uid, "sale.order", "create", [values])
```

### Client Resolution Pattern

The `create_draft_quote()` method receives a `UniversalQuote` with `client_id: str`. To create in Odoo, you need the integer `partner_odoo_id`. Resolution:
1. Call `self.get_client(quote.client_id)` (already exists from Story 4.6)
2. Use `client.odoo_id` (int) as `partner_id` in the `sale.order.create` call
3. If client not found, raise `ERPConnectionError` with descriptive message

### CLI Pattern

Follow the exact pattern from `erp_read.py`. In `cli/main.py`:
```python
@app.command()
def draft_create(
    client: str = typer.Option(..., "--client", "-c", help="Client ID or ref"),
    product: int = typer.Option(..., "--product", "-p", help="Product Odoo ID"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Quantity"),
    price: float | None = typer.Option(None, "--price", help="Unit price override"),
    description: str | None = typer.Option(None, "--description", "-d", help="Line description"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a draft quote in Odoo ERP."""
    from quote_agent.cli.draft_create import draft_create as _draft_create_impl
    _draft_create_impl(client=client, product=product, quantity=quantity, price=price, description=description, json_output=json_output)
```

Implementation in `cli/draft_create.py`:
1. Build a `UniversalQuote` with one `UniversalQuoteLine`
2. Call `asyncio.run(_create_draft(...))`
3. Display result (draft ID, order reference, state)

### Project Structure Notes

- All adapter code goes in EXISTING files under `src/quote_agent/adapters/erp/` -- the only new file is `src/quote_agent/cli/draft_create.py`
- Tests go in `tests/unit/test_erp_draft_create.py` (new) and `tests/unit/cli/test_cli_draft_create.py` (new)
- No new database models or migrations -- draft quotes live in Odoo, NOT in local PostgreSQL
- No new Alembic migration needed

### Architecture Compliance

- ERPAdapter Protocol must remain `@runtime_checkable` -- add `create_draft_quote` before implementation
- All methods `async`, return typed Pydantic DTOs
- `asyncio.to_thread()` for sync XML-RPC calls, `asyncio.wait_for()` for timeout
- Follow existing timeout constant pattern: `_CREATE_DRAFT_TIMEOUT = 30.0`
- Health check is NOT changed by this story
- Factory `get_erp_adapter()` in `__init__.py` unchanged

### What NOT to Do

- Do NOT create a SQLAlchemy model for quotes in local DB -- drafts live in Odoo
- Do NOT wire draft creation into the LangGraph agent graph -- that's Story 4.8 (orchestration)
- Do NOT touch `agent/nodes/router.py` or other existing nodes -- this story is adapter-level + CLI only
- Do NOT add Redis or external caching
- Do NOT implement multi-line quotes in CLI -- CLI is a single-line testing tool; multi-line comes via the agent pipeline in 4.8
- Do NOT implement notification after draft creation -- that's Epic 5
- Do NOT add a `quote_builder.py` node yet -- that's Story 4.8's responsibility to wire UniversalQuote construction from agent state
- Do NOT retroactively add `create_draft_quote` to existing `get_products()` or other read methods

### References

- [Source: _bmad-output/planning-artifacts/epics.md -- Epic 4, Story 4.7]
- [Source: _bmad-output/planning-artifacts/architecture.md -- ERPAdapter Protocol, UniversalQuote, API Boundaries]
- [Source: _bmad-output/planning-artifacts/prd.md -- FR29, FR32, NFR-R3, NFR-P1]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Draft-only workflow, invisible agent, ERP-native drafts]
- [Source: docs/project-context.md -- Adapter Pattern, Async Pattern, Known Pitfalls]
- [Source: src/quote_agent/adapters/erp/odoo.py -- existing implementation patterns, _retry_with_backoff]
- [Source: prototype/scripts/e2e-quote-pipeline.py -- lines 187-203, draft creation reference]

### Previous Story Intelligence (Story 4.6)

- Story 4.6 added `get_client()`, `get_client_orders()`, `get_product_by_id()` with retry and CLI `erp-read`
- Introduced `_retry_with_backoff()` helper -- reuse for draft creation (DO NOT duplicate)
- Introduced `Client`, `ClientOrderHistory`, `ClientFilter` DTOs -- `Client.odoo_id` is needed for `partner_id`
- 538 total unit tests passing after 4.6
- Code quality gates: `ruff check` + `mypy --strict` must pass
- Test file pattern: separate test file per feature (`test_erp_client_orders.py`, `test_cli_erp_read.py`)
- Review follow-up: `asyncio.run()` in CLI commands is a known project-wide pattern (9 commands), not a blocker

### Git Intelligence

Recent commits show consistent patterns:
- Commit messages: `feat: add {feature} with CLI command (Story X.Y)`
- Each story adds its own test file(s)
- All stories maintain backward compatibility (no breaking changes to existing tests)
- `ruff check` and `mypy --strict` enforced in CI

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- All 6 tasks completed: DTOs, Protocol, Odoo adapter, CLI, logging, tests
- 3 new Pydantic DTOs: `UniversalQuoteLine`, `UniversalQuote`, `QuoteDraftResult`
- `ERPAdapter` Protocol extended with `create_draft_quote()`
- `OdooAdapter.create_draft_quote()` with retry, timeout, structured logging
- `_build_odoo_order_values()` static helper for Odoo `[0, 0, {...}]` notation
- CLI `draft-create` command with --client, --product, --quantity, --price, --description, --json
- 29 new unit tests (19 adapter + 10 CLI), all passing
- Full regression: 567 tests passing, 0 failures
- `ruff check` and `mypy --strict` both pass clean

### Change Log

- 2026-03-21: Story 4.7 implementation complete — draft quote creation in Odoo (all 6 tasks, 29 tests)

### File List

- src/quote_agent/adapters/erp/models.py (modified — added UniversalQuoteLine, UniversalQuote, QuoteDraftResult DTOs)
- src/quote_agent/adapters/erp/protocol.py (modified — added create_draft_quote to ERPAdapter Protocol)
- src/quote_agent/adapters/erp/odoo.py (modified — added create_draft_quote, _build_odoo_order_values, _create_draft_quote_impl)
- src/quote_agent/cli/draft_create.py (new — CLI draft-create implementation)
- src/quote_agent/cli/main.py (modified — registered draft-create command)
- tests/unit/test_erp_draft_create.py (new — 19 tests: DTOs, adapter, retry, protocol)
- tests/unit/test_cli_draft_create.py (new — 10 tests: CLI success, errors, flags)
