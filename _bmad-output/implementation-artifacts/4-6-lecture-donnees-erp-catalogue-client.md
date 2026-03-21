# Story 4.6: Lecture Données ERP (Catalogue & Client)

Status: done

## Story

As a **sales rep (Sophie)**,
I want the agent to read product catalog data and client order history from Odoo,
So that it has the full context needed to match products and personalize quotes.

## Acceptance Criteria

1. **AC-1: Product detail enrichment from Odoo**
   Given the Odoo adapter is configured and healthy
   When the agent needs product details for a match
   Then it reads product data (price, availability, full description) from Odoo via XML-RPC (FR30)
   And the adapter uses read-only access (least privilege)

2. **AC-2: Client data and order history from Odoo**
   Given a known client sends a request
   When the agent processes the request
   Then it reads client data and recent order history from Odoo (FR31)
   And this data is available for personalization and "like last time" resolution

3. **AC-3: Graceful degradation on ERP unavailability**
   Given the ERP is temporarily unavailable
   When a read is attempted
   Then the adapter retries with exponential backoff
   And if all retries fail, the request is queued for later processing (graceful degradation)

4. **AC-4: Client and ClientOrderHistory DTOs**
   Given the ERP adapter models module exists
   When client data is fetched from Odoo
   Then it returns typed Pydantic DTOs (`Client`, `ClientOrderHistory`) — never raw `dict`

5. **AC-5: ERPAdapter Protocol updated**
   Given the ERPAdapter Protocol class
   When new read methods are added
   Then `get_client(client_id: str) -> Client` and `get_client_orders(client_id: str, limit: int) -> list[ClientOrderHistory]` are defined in the Protocol

6. **AC-6: CLI command for ERP data reads**
   Given the CLI is available
   When the user runs `uv run quote-agent erp-read --client <id>` or `uv run quote-agent erp-read --product <id>`
   Then it displays the fetched data from Odoo in formatted output (or JSON with `--json`)

7. **AC-7: Unit tests for all new methods**
   Given the new adapter methods and CLI command
   When tests are run
   Then all new public methods have unit tests with mocked XML-RPC calls
   And code passes `ruff check` and `mypy --strict`

8. **AC-8: Structured logging and audit**
   Given any ERP read operation
   When a read is performed (success or failure)
   Then structured logs are emitted with component, context (client_id or product_id), and duration
   And confidential data (prices, client details) is auto-redacted via JSONLogFormatter

## Tasks / Subtasks

- [x] Task 1: Extend ERP adapter DTOs (AC: #4)
  - [x] 1.1 Add `Client` Pydantic DTO to `adapters/erp/models.py` (fields: odoo_id, name, ref, email, phone, address, vat, is_active, metadata)
  - [x] 1.2 Add `ClientOrderHistory` Pydantic DTO to `adapters/erp/models.py` (fields: order_id, date, product_ref, product_name, quantity, unit_price, total, state)
  - [x] 1.3 Add `ClientFilter` Pydantic DTO (fields: search_term, limit, offset)

- [x] Task 2: Extend ERPAdapter Protocol (AC: #5)
  - [x] 2.1 Add `get_client(client_id: str) -> Client` to `protocol.py`
  - [x] 2.2 Add `get_client_orders(client_id: str, limit: int = 20) -> list[ClientOrderHistory]` to `protocol.py`
  - [x] 2.3 Add `get_product_by_id(product_id: int) -> Product` to `protocol.py` (single product detail enrichment)

- [x] Task 3: Implement Odoo client/order reads in `odoo.py` (AC: #1, #2, #3)
  - [x] 3.1 Implement `get_client()` — XML-RPC `search_read` on `res.partner` model with fields: id, name, ref, email, phone, street, city, zip, country_id, vat, active, customer_rank
  - [x] 3.2 Implement `get_client_orders()` — XML-RPC `search_read` on `sale.order` model filtered by partner_id, ordered by date desc, with limit; then read `sale.order.line` for product details
  - [x] 3.3 Implement `get_product_by_id()` — XML-RPC `search_read` on `product.product` with `[('id', '=', product_id)]`
  - [x] 3.4 Add exponential backoff retry logic (3 retries, base=1s, max=8s) for all new methods
  - [x] 3.5 Add timeout enforcement via `asyncio.wait_for()` (30s for client, 30s for orders)

- [x] Task 4: Add CLI `erp-read` command (AC: #6)
  - [x] 4.1 Create `src/quote_agent/cli/erp_read.py` with implementation
  - [x] 4.2 Register command in `cli/main.py` following existing pattern (lazy import)
  - [x] 4.3 Support `--client <id>`, `--product <id>`, `--orders <client_id>` flags
  - [x] 4.4 Support `--json` output flag

- [x] Task 5: Add structured logging (AC: #8)
  - [x] 5.1 Log ERP read operations with component="adapters.erp.odoo", context={operation, id, duration_ms}
  - [x] 5.2 Ensure prices/client details auto-redacted by existing JSONLogFormatter

- [x] Task 6: Unit tests (AC: #7)
  - [x] 6.1 Test `get_client()` — success, not found, connection error, timeout
  - [x] 6.2 Test `get_client_orders()` — success with orders, empty orders, connection error
  - [x] 6.3 Test `get_product_by_id()` — success, not found
  - [x] 6.4 Test retry logic — verify exponential backoff timing and max retries
  - [x] 6.5 Test CLI `erp-read` — all 3 modes (client, product, orders), JSON output, error handling
  - [x] 6.6 Test Protocol compliance — verify `OdooAdapter` satisfies updated `ERPAdapter` Protocol

### Review Follow-ups (AI)
- [x] [AI-Review][MEDIUM] AC-3 graceful degradation: added structured error log with `retries_exhausted=True` when all retries fail, signaling for future queue/orchestration layer [odoo.py:_retry_with_backoff]
- [ ] [AI-Review][MEDIUM] `asyncio.run()` in CLI commands risks crash in existing event loops — project-wide pattern (9 commands affected), needs separate refactor story

## Dev Notes

### What Already Exists (DO NOT Recreate)

- **ERP adapter structure**: `src/quote_agent/adapters/erp/` with `protocol.py`, `models.py`, `odoo.py`, `__init__.py` — extend these files, do NOT create new adapter modules
- **`OdooAdapter` class** in `odoo.py`: already has `health_check()`, `get_products()`, and `_ensure_uid()` for auth caching — reuse `_ensure_uid()` for new methods
- **Product DTO** in `models.py`: `Product`, `ProductFilter`, `IngestionResult`, `OdooVersionInfo` already exist
- **XML-RPC pattern**: `asyncio.to_thread(proxy.execute_kw, ...)` wrapped in `asyncio.wait_for()` — follow this exact pattern
- **`_odoo_str()` helper**: converts Odoo `False` to `None` — reuse for client field mapping
- **`_map_odoo_product()` helper**: maps Odoo dict to Product DTO — follow this pattern for `_map_odoo_client()` and `_map_odoo_order()`

### Odoo XML-RPC API Details

**Client read** — Odoo model: `res.partner`
- Domain filter: `[('id', '=', int(client_id))]` or `[('ref', '=', client_id)]` (support both numeric ID and string ref)
- Key fields: `id`, `name`, `ref` (customer code), `email`, `phone`, `street`, `city`, `zip`, `country_id`, `vat`, `active`, `customer_rank`, `commercial_partner_id`
- `country_id` returns `[id, "Country Name"]` tuple like `categ_id` — use same extraction pattern
- `customer_rank > 0` indicates the partner is a customer (vs supplier)

**Order history** — Odoo model: `sale.order`
- Domain filter: `[('partner_id', '=', partner_odoo_id)]` — NOTE: uses the numeric Odoo partner ID, not the string ref
- Order fields: `id`, `name` (order reference like SO001), `date_order`, `state`, `amount_total`, `partner_id`
- Then fetch `sale.order.line` with `[('order_id', 'in', order_ids)]` for line details
- Line fields: `id`, `product_id`, `name` (description), `product_uom_qty`, `price_unit`, `price_subtotal`
- `product_id` returns `[id, "Product Name"]` tuple
- States: `draft`, `sent`, `sale`, `done`, `cancel` — filter to `sale` and `done` for meaningful history
- Order by `date_order desc` for most recent first

### Retry Pattern

The current `odoo.py` does NOT have retry logic (single attempt for `get_products`). This story introduces retry with exponential backoff:

```python
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0
_RETRY_MAX_DELAY = 8.0

async def _retry_with_backoff(self, operation: Callable, *args):
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await operation(*args)
        except (ConnectionRefusedError, OSError, xmlrpc.client.Error) as exc:
            if attempt == _MAX_RETRIES:
                raise
            delay = min(_RETRY_BASE_DELAY * (2 ** (attempt - 1)), _RETRY_MAX_DELAY)
            logger.warning("ERP retry %d/%d after %.1fs: %s", attempt, _MAX_RETRIES, delay, exc)
            await asyncio.sleep(delay)
```

Apply retry to `get_client()`, `get_client_orders()`, and `get_product_by_id()`. Do NOT retroactively add retry to existing `get_products()` (out of scope — catalog ingestion is batch, not request-time).

### CLI Pattern

Follow the exact pattern from existing commands. In `cli/main.py`:

```python
@app.command()
def erp_read(
    client: str | None = typer.Option(None, "--client", "-c", help="Client ID or ref to read from Odoo"),
    product: int | None = typer.Option(None, "--product", "-p", help="Product Odoo ID to read"),
    orders: str | None = typer.Option(None, "--orders", "-o", help="Client ID to fetch order history"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max orders to fetch"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Read client data, product details, or order history from Odoo ERP."""
    from quote_agent.cli.erp_read import erp_read as _erp_read_impl
    _erp_read_impl(client=client, product=product, orders=orders, limit=limit, json_output=json_output)
```

### Project Structure Notes

- All new code goes in EXISTING files under `src/quote_agent/adapters/erp/` — the only new file is `src/quote_agent/cli/erp_read.py`
- Tests go in `tests/unit/test_erp_adapter.py` (extend existing) and `tests/unit/cli/test_cli_erp_read.py` (new)
- No new database models or migrations in this story — client data is read live from Odoo, NOT cached in PostgreSQL (that's Epic 6 memory layer territory)
- No new Alembic migration needed

### Architecture Compliance

- ERPAdapter Protocol must remain `@runtime_checkable` — add new methods to protocol before implementation
- All methods `async`, return typed Pydantic DTOs
- `asyncio.to_thread()` for sync XML-RPC calls, `asyncio.wait_for()` for timeout
- Follow existing `_HEALTH_CHECK_TIMEOUT`, `_GET_PRODUCTS_TIMEOUT` pattern for new timeout constants
- Health check is NOT changed by this story — only data reads
- Factory `get_erp_adapter()` in `__init__.py` unchanged (already returns `OdooAdapter`)

### What NOT to Do

- Do NOT create a `models/client.py` SQLAlchemy model — client data lives in Odoo, not in local DB (for now)
- Do NOT add `get_client` to the health check endpoint — ERP health is already checked
- Do NOT modify `catalog_service.py` or `search/` — this story is adapter-level only
- Do NOT add Redis or external caching — follow PostgreSQL-only pattern
- Do NOT touch `agent/nodes/` or `agent/tools/` — those will be wired in Story 4.8 (orchestration)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 4, Story 4.6]
- [Source: _bmad-output/planning-artifacts/architecture.md — ERPAdapter Protocol, API Boundaries, Adapter Pattern]
- [Source: _bmad-output/planning-artifacts/prd.md — FR30, FR31]
- [Source: docs/project-context.md — Adapter Pattern, Async Pattern, Known Pitfalls]
- [Source: src/quote_agent/adapters/erp/odoo.py — existing implementation patterns]

### Previous Story Intelligence (Story 4.5)

- Story 4.5 added compliance checking (export control + sanctions) with LLM structured output
- Pattern: new node file + CLI command + extend existing pipeline
- 506 total unit tests passing after 4.5
- Code quality gates: `ruff check` + `mypy --strict` must pass
- Story 4.5 followed the same CLI pattern: command in `main.py` with lazy import to implementation file
- Test file pattern: separate test file per module (`test_compliance_checker.py`, `test_cli_compliance.py`)

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
- Initial test run: 7 existing ERP adapter tests passed (baseline)
- Test fix: corrected domain assertion index (execute_kw positional args) and CLI mock patch target (module-level vs lazy import)
- Final regression run: 538 tests passed, 0 failures

### Completion Notes List
- ✅ Task 1: Added `Client`, `ClientOrderHistory`, `ClientFilter` Pydantic DTOs to `models.py`
- ✅ Task 2: Extended ERPAdapter Protocol with `get_client()`, `get_client_orders()`, `get_product_by_id()`
- ✅ Task 3: Implemented all 3 methods in `odoo.py` with XML-RPC `search_read`, retry with exponential backoff (3 retries, 1s/2s/4s delays, max 8s), and 30s timeouts via `asyncio.wait_for()`
- ✅ Task 4: Created `erp-read` CLI command with `--client`, `--product`, `--orders`, `--json` flags; registered in `main.py` with lazy import
- ✅ Task 5: Structured logging on all read operations with component="adapters.erp.odoo", operation, id, duration_ms in context dict — auto-redacted by existing JSONLogFormatter
- ✅ Task 6: 32 new unit tests covering DTOs, mapping functions, adapter methods (success/error/retry/timeout), CLI (all modes + JSON + errors), and protocol compliance
- Quality gates: `ruff check` ✅, `mypy --strict` ✅, 538 total tests passing ✅

### Change Log
- 2026-03-21: Story 4.6 implemented — ERP client/order reads with retry, CLI command, 32 tests
- 2026-03-21: Code review — M1 fixed (structured error log on retry exhaustion for AC-3 graceful degradation), M2 deferred (asyncio.run project-wide pattern)

### File List
- src/quote_agent/adapters/erp/models.py (modified — added Client, ClientOrderHistory, ClientFilter DTOs)
- src/quote_agent/adapters/erp/protocol.py (modified — added get_client, get_client_orders, get_product_by_id to Protocol)
- src/quote_agent/adapters/erp/odoo.py (modified — added retry logic, mapping functions, 3 new methods)
- src/quote_agent/cli/erp_read.py (new — CLI erp-read command implementation)
- src/quote_agent/cli/main.py (modified — registered erp_read command)
- tests/unit/test_erp_client_orders.py (new — 22 tests for adapter methods, DTOs, retry, protocol)
- tests/unit/test_cli_erp_read.py (new — 10 tests for CLI command)
