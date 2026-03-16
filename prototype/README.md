# Prototype: n8n + Odoo Community Environment

Local Docker environment for validating the n8n ↔ Odoo integration prototype.

## Prerequisites

- Docker and Docker Compose (v2+)
- Python 3.10+ with dependencies (`pip install -r requirements.txt`)
- curl (for verification script)

## Quick Start

```bash
# 1. Copy and configure environment variables
cp .env.example .env

# 2. Start all services
docker compose up -d

# 3. Wait for initialization (Odoo first boot takes 2-3 minutes)
docker compose logs -f odoo   # Watch for "HTTP service (werkzeug) running"

# 4. Verify everything is working
./scripts/verify-setup.sh
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Odoo 18 Community | http://localhost:8069 | ERP with demo data (login: admin / admin) |
| n8n | http://localhost:5678 | Workflow automation |
| PostgreSQL 16 | localhost:5432 | Odoo database backend |
| Qdrant | http://localhost:6333/dashboard | Vector search engine (REST API on 6333, gRPC on 6334) |

## n8n ↔ Odoo Connection

The connection uses **HTTP Request nodes** with JSON-RPC (not the built-in Odoo node) for reliability.

### Test Workflow

Import `n8n-workflows/test-odoo-connection.json` into n8n to test the connection:

1. Open n8n at http://localhost:5678
2. Go to Workflows → Import from File
3. Select `n8n-workflows/test-odoo-connection.json`
4. Execute the workflow — it should authenticate and list products

### JSON-RPC Connection Details

- **Endpoint**: `http://odoo:8069/jsonrpc` (from within Docker network)
- **Authentication**: POST to `http://odoo:8069/web/session/authenticate`
- **Database**: `odoo_db`
- **Credentials**: admin / admin

## Catalog Ingestion (Story 0.2)

### Step 1: Seed Odoo with Synthetic Catalog

The seeder creates 500+ industrial products in Odoo with realistic noise (duplicates, case variations, missing fields, HTML descriptions, abbreviations, archived/non-sellable items).

```bash
# Install dependency
pip install requests

# Run seeder (Odoo must be running)
python3 scripts/seed-catalog.py
```

The seeder creates ~680 products across 8 industrial categories. It prints a summary with noise breakdown on completion.

### Step 2: Run Ingestion Workflow

Import and run `n8n-workflows/ingest-catalog.json` in n8n:

1. Open n8n at http://localhost:5678
2. Go to Workflows → Import from File
3. Select `n8n-workflows/ingest-catalog.json`
4. Execute the workflow — it fetches all products and writes to disk

Output: `data/catalog/products_raw.json` (~0.25 MB for ~720 products)

### Ingestion Path Decision

**Chosen method:** JSON-RPC API via n8n HTTP Request nodes + Code node for pagination.

**Why JSON-RPC API (not CSV export):**
- Real-time access to current Odoo data — no export step needed
- Programmatic pagination handles any catalog size
- Same authentication pattern as Story 0.1 (proven reliable)
- Structured JSON output ready for downstream processing
- Can be scheduled/triggered automatically in n8n

**Pagination strategy:** Fetch in batches of 200 products using `offset`+`limit` on `search_read`. Loop until result count < limit. Context `active_test: false` ensures archived products are included.

**Fields extracted:**

| Field | Purpose |
|-------|---------|
| `id` | Odoo internal ID |
| `name` | Product name (primary search field) |
| `default_code` | Internal reference / SKU |
| `barcode` | EAN/barcode |
| `list_price` | Sale price |
| `categ_id` | Product category |
| `type` | Product type (consu/service/product) |
| `sale_ok` | Whether product can be sold (proposability filter) |
| `description` | Internal description (HTML) |
| `description_sale` | Customer-facing description |
| `active` | Whether product is archived |

> **Note:** `qty_available` (from `stock` module) is not available in this prototype since only the `sale` module is installed. It will be available in the production environment.

**Performance:** ~720 products fetched in <0.2s over 4 API calls (200 per page). File output ~0.25 MB.

**Known limitations:**
- Credentials hardcoded in n8n workflow JSON (acceptable for prototype)
- No incremental/delta sync — full catalog fetch each time
- `qty_available` unavailable without `stock` module

**API vs CSV export trade-offs:**

| Aspect | JSON-RPC API | CSV Export |
|--------|-------------|------------|
| Freshness | Real-time | Snapshot at export time |
| Automation | Full (n8n triggered) | Manual export step |
| Pagination | Built-in with offset/limit | N/A (single file) |
| Fields | Programmatic selection | UI-dependent columns |
| Error handling | HTTP status + JSON errors | Parse errors possible |
| Performance | Fast (0.2s for 700+) | Depends on export tool |

## Embedding Generation & Vector Search (Story 0.3)

### Embedding Model: BAAI/bge-m3

**Why BGE-M3:**
- Multilingual model (100+ languages) — handles French product catalog and English queries
- 1024-dimension dense embeddings with strong semantic understanding
- 568M parameters (~2.3 GB download on first run, cached in `~/.cache/huggingface/`)
- Recommended in architecture document for production use — prototype validates this choice

**Text construction strategy:**
Product fields are concatenated as-is with `|` separator: `name | Ref: default_code | category | description_sale | description`. No HTML stripping, no normalization, no deduplication — the embedding model handles the noise.

### Step 1: Generate Embeddings and Index in Qdrant

```bash
# Install dependencies (includes sentence-transformers and qdrant-client)
pip install -r requirements.txt

# Start Qdrant (if not already running)
docker compose up -d qdrant

# Generate embeddings and index (first run downloads ~2.3 GB model)
python3 scripts/generate-embeddings.py
```

**Performance (726 products on CPU):**
- Model load: ~15s
- Embedding generation: ~109s (batch size 32)
- Qdrant upsert: <1s
- Total: ~126s

The script creates a `products` collection in Qdrant with HNSW indexing and cosine distance metric. Each vector point includes the full raw product data as payload.

### Step 2: Test Semantic Search

```bash
# Run default test queries
python3 scripts/test-semantic-search.py

# Run a custom query
python3 scripts/test-semantic-search.py "your search query here"
```

**Sample search results (5 default queries):**

| Query | Top Result | Score | Response Time |
|-------|-----------|-------|---------------|
| "tube acier inoxydable" | Tube carré acier | 0.63 | 111ms |
| "boulon haute résistance M12" | Boulon tête hexagonale M12x50 | 0.68 | 90ms |
| "tuyau DN50" | Tuyau acier DN50 | 0.77 | 85ms |
| "plaque acier sur mesure" | SUR MESURE - Plaque acier découpée | 0.68 | 86ms |
| "safety helmet" (cross-lingual) | Gilet haute visibilité S | 0.57 | 81ms |

All queries respond in < 500ms. Results demonstrate semantic understanding of abbreviations ("M12"), technical references ("DN50"), custom products ("SUR MESURE"), and cross-lingual capability (English → French catalog).

**Known limitations:**
- No preprocessing means HTML tags in descriptions add noise (scores may be slightly lower than with cleaned data)
- Cross-lingual queries (e.g., "safety helmet") match the right category but may not find exact product types (no helmets in catalog — returns closest safety equipment)
- Model loads ~2.3 GB into RAM — ensure 4 GB+ free memory
- GPU auto-detected by sentence-transformers if CUDA available (much faster: ~5-10s vs ~109s on CPU)
- Qdrant collection is recreated on each run (existing data deleted)

## Useful Commands

```bash
# View logs
docker compose logs -f

# Stop services
docker compose down

# Stop and remove volumes (full reset)
docker compose down -v

# Restart a specific service
docker compose restart odoo
```

## Troubleshooting

- **Odoo not loading**: First boot takes 2-3 minutes for DB initialization. Check `docker compose logs odoo`.
- **n8n can't reach Odoo**: Both must be on the `proto-net` network. Check with `docker network inspect proto-net`.
- **Products not found**: Ensure Odoo initialized with demo data. The entrypoint script handles this automatically on first boot.
