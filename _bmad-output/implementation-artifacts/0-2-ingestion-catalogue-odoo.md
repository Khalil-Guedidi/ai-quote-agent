# Story 0.2: Ingestion Catalogue Odoo → Stockage Intermédiaire

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want to ingest the product catalog from Odoo (API or export) into an intermediate storage,
So that I can validate the ingestion path and prepare data for vector indexing.

## Acceptance Criteria

1. **AC-0.2.1**: n8n workflow that extracts product catalog from Odoo (API or CSV export)
   - Given: The Docker environment from Story 0.1 is running (n8n + Odoo + Postgres)
   - When: The developer triggers the catalog ingestion workflow in n8n
   - Then: The workflow authenticates with Odoo via JSON-RPC (`/web/session/authenticate`)
   - And: Retrieves ALL products from `product.product` model using `search_read` via JSON-RPC
   - And: Fetches key fields: `id`, `name`, `default_code`, `barcode`, `list_price`, `categ_id`, `type`, `sale_ok`, `description`, `description_sale`, `active` (note: `qty_available` unavailable — requires `stock` module not installed in prototype; documented in README)
   - And: Handles pagination (Odoo returns max ~80 records per call by default — must loop with `offset`+`limit`)

2. **AC-0.2.2**: Raw catalog data stored in intermediate format (JSON/CSV) without manual cleaning
   - Given: The ingestion workflow has completed
   - When: The developer checks the output directory
   - Then: A JSON file exists at a known, persistent path inside the n8n container (mounted volume)
   - And: The file contains the raw, unmodified product data exactly as returned by Odoo
   - And: No cleaning, deduplication, or transformation has been applied — the data is "dirty"
   - And: The JSON structure is an array of product objects with all fetched fields

3. **AC-0.2.3**: Odoo populated with synthetic dirty catalog (~500+ products with noise, duplicates, custom items)
   - Given: Odoo is running with default demo data (~20-50 products)
   - When: The developer runs the catalog seeding script
   - Then: Odoo contains 500+ products including:
     - Real-looking industrial products with French names
     - Duplicate entries with slight name variations (e.g., "Tuyau acier DN50" vs "Tuyau Acier DN 50" vs "TUYAU ACIER dn50")
     - Products with missing `default_code` or `barcode`
     - Products with `sale_ok=False` (non-proposable)
     - Products with `active=False` (archived)
     - Custom/special products (e.g., "SUR MESURE - Plaque acier")
     - Products with abbreviations and jargon (e.g., "Boul. HM 8.8 M12x60" for "Boulon tête hexagonale haute résistance 8.8 M12x60")
     - Products with noisy descriptions (HTML fragments, encoding artifacts, extra whitespace)

4. **AC-0.2.4**: Ingestion path documented (API vs export vs mixed)
   - Given: The ingestion workflow has been tested
   - When: The developer reads the documentation
   - Then: A section in `prototype/README.md` documents:
     - The chosen ingestion method (JSON-RPC API) and why
     - Pagination strategy used
     - Fields extracted and their purpose
     - Volume of data ingested and performance (time taken)
     - Known limitations or issues encountered
     - Comparison notes: API vs CSV export trade-offs

## Tasks / Subtasks

- [x] Task 1: Create synthetic dirty catalog seeder (AC: #3)
  - [x] 1.1: Create Python script `prototype/scripts/seed-catalog.py` that generates 500+ synthetic products via Odoo JSON-RPC API (`product.product` create)
  - [x] 1.2: Include industrial product categories: steel/metal products, fasteners (boulonnerie), pipes (tuyauterie), electrical components, safety equipment
  - [x] 1.3: Introduce controlled "noise": duplicates with case/spacing variations, missing fields, archived products, non-sellable items, abbreviation-heavy names, HTML in descriptions
  - [x] 1.4: Run seeder and verify product count in Odoo via JSON-RPC `search_count`

- [x] Task 2: Create n8n ingestion workflow (AC: #1, #2)
  - [x] 2.1: Create n8n workflow `prototype/n8n-workflows/ingest-catalog.json` — ManualTrigger → Authenticate → Paginated Product Fetch → Aggregate → Write JSON
  - [x] 2.2: Implement pagination loop: fetch products in batches of 200 (`limit=200`, incrementing `offset`), stop when result count < limit
  - [x] 2.3: Use n8n "Convert to File" node to serialize aggregated JSON
  - [x] 2.4: Use n8n "Read/Write Files from Disk" node to write to `/data/catalog/products_raw.json` (persistent via Docker volume)
  - [x] 2.5: Add Docker volume mount for catalog output in `docker-compose.yml`

- [x] Task 3: Documentation (AC: #4)
  - [x] 3.1: Update `prototype/README.md` with catalog ingestion section
  - [x] 3.2: Document ingestion path decision, performance metrics, and trade-offs

## Dev Notes

### Critical: Reuse Story 0.1 Connection Pattern

Story 0.1 established the n8n ↔ Odoo connection pattern. The test workflow at `prototype/n8n-workflows/test-odoo-connection.json` shows the exact approach:
1. **Authenticate** via HTTP Request node → `POST http://odoo:8069/web/session/authenticate` with JSON-RPC payload
2. **Extract session cookie** from response headers: `$json.headers['set-cookie']` → first cookie before `;`
3. **Call JSON-RPC** with session cookie in `Cookie` header → `POST http://odoo:8069/jsonrpc` with `execute_kw` payload
4. **Use `product.product` model** (NOT `product.template`) — we need variant-level data for accurate matching

**DO NOT** use the n8n built-in Odoo node — it has serialization issues (Story 0.1 lesson).

### Odoo product.product vs product.template

- `product.template` = parent product (e.g., "T-Shirt"). Shared fields: name, categ_id, sale_ok, type
- `product.product` = variant (e.g., "T-Shirt - Blue / M"). Has own: default_code, barcode, qty_available
- **Use `product.product`** for ingestion — we need the most granular level for accurate search matching
- To discover all available fields, use `fields_get()` method on `product.product` via JSON-RPC

### JSON-RPC Pagination Pattern

Odoo's `search_read` does NOT return total count. Strategy:
```
offset = 0, limit = 200
Loop:
  results = search_read(offset=offset, limit=limit)
  if len(results) < limit → last page, stop
  offset += limit
```

Alternative: call `search_count` first to know total, then fetch in batches. Either approach works.

### n8n File Output Strategy

n8n runs inside a Docker container. To persist output files:
1. Add a Docker volume mount in `docker-compose.yml`: `./data/catalog:/data/catalog` on the n8n service
2. In n8n workflow, use **"Convert to File"** node (converts JSON items → binary JSON file)
3. Then use **"Read/Write Files from Disk"** node to write to `/data/catalog/products_raw.json`
4. The file will be accessible from the host at `prototype/data/catalog/products_raw.json`

### Synthetic Catalog Design

The dirty catalog must simulate real-world industrial ERP data to validate the "zero-preprocessing" promise (PRD FR5, FR9). Key noise patterns:

| Noise Type | Example | Purpose |
|-----------|---------|---------|
| Case variations | "Tuyau Acier" vs "TUYAU ACIER" vs "tuyau acier" | Test case-insensitive matching |
| Spacing/punctuation | "DN50" vs "DN 50" vs "DN-50" | Test normalization robustness |
| Abbreviations | "Boul. HM 8.8" = "Boulon Haute Résistance 8.8" | Test semantic understanding |
| Missing refs | Products with empty `default_code` | Test fallback to name search |
| HTML in descriptions | `<p>Acier <b>inox</b> 304L</p>` | Test raw data handling |
| Duplicates | Same product, slightly different names | Test dedup at search time |
| Non-proposable | `sale_ok=False`, `active=False` | Test filtering in Story 0.4+ |

### Seeder Script: Use Python + requests (NOT n8n)

The seeder creates data in Odoo — use a standalone Python script (simpler, no n8n dependency for data setup). Connect to Odoo JSON-RPC from the host machine via `localhost:8069`. The script should:
- Authenticate to Odoo JSON-RPC
- Create product categories first (using `product.category` model)
- Create 500+ products using `product.product` `create` method with batch writes
- Print summary: total created, by category, noise breakdown

### Environment Variables

The seeder script should read from `prototype/.env`:
```env
ODOO_HOST=localhost
ODOO_PORT=8069
ODOO_DB=odoo_db
ODOO_USER=admin
ODOO_PASSWORD=admin
```

### Docker Compose Changes

Add volume mount to n8n service for catalog output:
```yaml
n8n:
  volumes:
    - n8n-data:/home/node/.n8n
    - ./data/catalog:/data/catalog    # <-- ADD THIS
```

Create `prototype/data/catalog/.gitkeep` to track the directory.

### Testing Standards

This is a prototype — no unit tests required. Validation is manual:
- Run seeder → verify count via `search_count` JSON-RPC call
- Run n8n ingestion workflow → verify JSON file exists and contains all products
- Spot-check JSON: confirm noise patterns present, no data modification
- Verify file size is reasonable for 500+ products (~1-3 MB)

### Gotchas to Avoid

1. **Do NOT clean or transform the catalog data** — the entire point is raw, dirty data
2. **Do NOT use the n8n built-in Odoo node** — use HTTP Request nodes (Story 0.1 lesson)
3. **Do NOT forget pagination** — Odoo default limit may truncate results silently
4. **Do NOT hardcode credentials** — read from `.env` (Story 0.1 code review feedback)
5. **Do NOT create products via Odoo UI** — use script for reproducibility
6. **Odoo `create` with large batches may timeout** — batch in groups of 50-100 products
7. **n8n Docker volume permissions** — the n8n user (node, uid 1000) must have write access to the mounted volume

### Project Structure Notes

- All files go under `prototype/` directory (consistent with Story 0.1)
- New files: `scripts/seed-catalog.py`, `n8n-workflows/ingest-catalog.json`, `data/catalog/.gitkeep`
- Modified files: `docker-compose.yml` (add volume), `README.md` (add documentation)
- The `data/catalog/products_raw.json` output file should be `.gitignore`d (generated data)
- No conflict with the architecture's `src/` structure — prototype is isolated

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 0, Story 0.2]
- [Source: _bmad-output/planning-artifacts/architecture.md - Data Architecture, ERP Integration]
- [Source: _bmad-output/planning-artifacts/prd.md - FR5, FR9, Prototype Phase, Zero-Preprocessing]
- [Source: _bmad-output/implementation-artifacts/0-1-setup-environnement-n8n-odoo.md - Connection pattern, lessons learned]
- [Odoo 18 External API docs](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)
- [Odoo product.product vs product.template](https://www.dasolo.ai/blog/odoo-data-api-5/odoo-product-product-model-guide-162)
- [n8n Convert to File node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.converttofile/)
- [n8n Binary data handling](https://docs.n8n.io/data/binary-data/)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Odoo `product.product` barcode uniqueness constraint triggered when abbreviation variants copied barcodes from the original product. Fixed by setting `barcode=False` on abbreviation variants.
- `qty_available` field does not exist on `product.product` without the `stock` module installed. Removed from fields list; documented as known limitation.
- Odoo `search_read` filters out `active=False` records by default. Added `context: {active_test: false}` to kwargs to fetch ALL products including archived ones.

### Implementation Plan

Used the proven JSON-RPC connection pattern from Story 0.1 (HTTP Request nodes, session cookie auth). Seeder script uses Python+requests for batch product creation in groups of 50. n8n workflow uses a Code node for paginated fetch (200/page loop) since native n8n nodes don't support Odoo pagination. Convert to File + Write to Disk nodes handle output persistence. Docker volume mount maps `./data/catalog` to `/data/catalog` inside n8n container.

### Completion Notes List

- **Task 1**: Created `scripts/seed-catalog.py` — 677 synthetic products across 8 industrial categories (Acier & Métaux, Boulonnerie, Tuyauterie, Composants Électriques, Sécurité, Outillage, Joints, Peinture). Noise patterns: 41 duplicates with name variations, 39 abbreviation variants, 74 missing codes, 7 non-sellable, 7 archived, 143 HTML descriptions, 10 special/custom products. Total in Odoo: 726 (incl. 42 demo + 7 inactive).
- **Task 2**: Created `n8n-workflows/ingest-catalog.json` — 5-node workflow: ManualTrigger → Authenticate (HTTP Request, JSON-RPC) → Fetch All Products Paginated (Code node, 200/page with offset loop, active_test=false) → Convert to File → Write to Disk (/data/catalog/products_raw.json). Added Docker volume mount `./data/catalog:/data/catalog` on n8n service. Created `data/catalog/.gitkeep`. Added `products_raw.json` to `.gitignore`.
- **Task 3**: Updated `prototype/README.md` with comprehensive catalog ingestion documentation: seeder usage, workflow import steps, ingestion path decision (JSON-RPC chosen over CSV), pagination strategy, fields table, performance metrics (0.2s / 720+ products), limitations, API vs CSV trade-offs comparison.

### File List

- prototype/scripts/seed-catalog.py (new)
- prototype/n8n-workflows/ingest-catalog.json (new)
- prototype/data/catalog/.gitkeep (new)
- prototype/docker-compose.yml (modified — added volume mount)
- prototype/README.md (modified — added catalog ingestion docs)
- .gitignore (modified — added products_raw.json)

### Change Log

- 2026-03-16: Implemented Story 0.2 — Synthetic catalog seeder (677 products, 8 categories, realistic noise), n8n paginated ingestion workflow, Docker volume mount, comprehensive documentation.
- 2026-03-16: Code review fixes — Fixed OdooRPC class using global ODOO_PASSWORD instead of self.password in execute_kw (coupling bug). Updated AC-0.2.1 to reflect qty_available limitation.
