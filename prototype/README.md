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

The script creates a `products` collection in Qdrant with HNSW indexing. Since Story 0.4, the collection stores both dense (cosine) and sparse (BM25/IDF) vectors. Each vector point includes the full raw product data as payload.

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

## Story 0.4 — Hybrid Search Benchmark

### Hybrid Search: Dense + Sparse with RRF Fusion

Story 0.4 extends the search system from dense-only (Story 0.3) to **hybrid search** combining:

- **Dense search** (BGE-M3 semantic embeddings, 1024 dims) — captures meaning
- **Sparse search** (Qdrant/bm25 via fastembed) — captures exact keyword matching
- **Hybrid search** (dense + sparse with Reciprocal Rank Fusion) — best of both

Additionally, **exact reference matching** is supported: if a query looks like a product code (e.g., "BHM-M12x50"), a direct payload filter search runs before vector search.

### Step 1: Generate Dense + Sparse Embeddings

```bash
# Install dependencies (now includes fastembed for BM25 sparse vectors)
pip install -r requirements.txt

# Generate both dense and sparse vectors (recreates Qdrant collection)
python3 scripts/generate-embeddings.py
```

The collection now stores both `dense` (1024-dim COSINE) and `sparse` (BM25 with server-side IDF) vectors per product.

### Step 2: Test Hybrid Search

```bash
# Run all 3 methods on a query
python3 scripts/hybrid-search.py "boulon hexagonal M12"

# Single method
python3 scripts/hybrid-search.py --method hybrid "tuyau PVC DN50"

# Exact reference
python3 scripts/hybrid-search.py --method hybrid "BHM-M12x50"
```

### Step 3: Run Benchmark

```bash
python3 scripts/run-benchmark.py
```

The benchmark runs 26 test queries across 9 categories against all 3 search methods and computes Hit@1, Hit@5, and MRR metrics.

### Benchmark Results & Decision

#### Summary Results

| Method | Hit@1 | Hit@5 | MRR | Avg Latency | P95 Latency |
|--------|-------|-------|-----|-------------|-------------|
| Dense (semantic) | 76.9% | 96.2% | 85.9% | 85ms | 96ms |
| Sparse (BM25) | 69.2% | 92.3% | 77.1% | 18ms | 21ms |
| **Hybrid (RRF)** | **76.9%** | **96.2%** | **85.9%** | **80ms** | **98ms** |

#### Per-Category Analysis

| Category | Dense | Sparse | Hybrid | Winner |
|----------|-------|--------|--------|--------|
| standard | 100% | 100% | 100% | Tie |
| abbreviation | 100% | 100% | 100% | Tie |
| jargon | 100% | 100% | 100% | Tie |
| exact-ref | 100% | 100% | 100% | Tie |
| typo | 100% | 100% | 100% | Tie |
| custom-product | 100% | 100% | 100% | Tie |
| multi-word | 100% | 100% | 100% | Tie |
| technical-spec | 100% | 100% | 100% | Tie |
| cross-lingual | 50% | 0% | 50% | Dense/Hybrid |

**Strong categories**: Standard, abbreviation, jargon, exact-ref, typo, custom-product, multi-word, and technical-spec all achieve 100% Hit@5 across all methods.

**Weak category**: Cross-lingual (English → French) is the only challenge. The query "angle iron steel" maps to "meuleuse d'angle" (angle grinder) instead of "cornière acier" (angle iron). This is expected — the English term "angle" is ambiguous. Dense search still handles "stainless steel bolt" → French bolts correctly.

#### GO/NO-GO Decision

**Decision: GO** ✅

- **Hybrid Hit@5 = 96.2%** — significantly above the 80% threshold
- Hybrid search works on raw, uncleaned catalog data (zero-preprocessing validated)
- All 8/9 categories achieve 100% accuracy; only cross-lingual has one edge case
- Latency is well within the 3s architecture target (avg 80ms, p95 98ms)

#### Recommended Search Strategy for Production

1. **Primary**: Hybrid search (dense BGE-M3 + sparse BM25 with RRF fusion)
2. **Exact match fallback**: Payload filter on `default_code` for reference-like queries
3. **Fusion method**: RRF (Reciprocal Rank Fusion) — robust and score-agnostic
4. **Top-K**: Return 10 candidates, re-rank with LLM reasoning for final selection

#### Known Limitations and Production Considerations

- **Cross-lingual**: English queries with ambiguous terms may match wrong products. Production LLM layer can add translation/disambiguation
- **Production stack differs**: Prototype uses Qdrant; production will use pgvector (dense) + PostgreSQL tsvector (sparse). Core hybrid approach transfers
- **BM25 model**: Using `Qdrant/bm25` (fastembed) instead of BGE-M3 sparse mode due to FlagEmbedding compatibility issues. Production should evaluate both options
- **Catalog size**: Tested on 726 products. Performance should scale linearly for typical industrial catalogs (10K-100K products)
- **No proposability filter in search**: Production search should filter on `sale_ok=True` and `active=True` post-retrieval

## Story 0.5 — Email Reception & Structured Data Extraction

### Extraction Approach

**Method:** Code node in n8n calling OpenAI GPT-4o API with structured JSON output (`response_format: json_object`).

**Why Code node (not Information Extractor):** Maximum control over the extraction prompt, which requires domain-specific instructions for French industrial B2B terminology, abbreviations, and multi-product handling.

### Extraction JSON Schema

```json
{
  "client_name": "string or null — company name preferred, person name as fallback",
  "client_email": "string or null — sender email address",
  "products": [
    {
      "description": "product description as written by client",
      "reference": "product code/reference if mentioned, else null",
      "quantity": "quantity with unit as written (e.g. '500', '20 barres'), null if unspecified",
      "specs": "specifications (dimensions, material, grade, finish) or null"
    }
  ],
  "delivery_date": "delivery date if mentioned, else null",
  "notes": "additional context or requirements, else null"
}
```

**Alignment with production `ParsedRequest` model:**

| Prototype field | Production direction | Notes |
|----------------|---------------------|-------|
| `client_name` | `ParsedRequest.client.name` | Will be richer (company, contact, account ID) |
| `client_email` | `ParsedRequest.client.email` | Used for client history lookup |
| `products[]` | `ParsedRequest.line_items[]` | More fields in production |
| `products[].description` | `line_items[].raw_description` | Preserved for audit trail |
| `products[].reference` | `line_items[].reference_code` | Triggers exact-ref search path |
| `products[].quantity` | `line_items[].quantity` + `.unit` | Separate quantity and unit in production |
| `products[].specs` | `line_items[].specifications` | Structured specs object in production |
| `delivery_date` | `ParsedRequest.delivery_date` | ISO 8601 in production |
| `notes` | `ParsedRequest.additional_context` | Free text |

### n8n Workflow

Import `n8n-workflows/extract-quote-request.json` into n8n:

1. Open n8n at http://localhost:5678
2. Go to Workflows → Import from File
3. Select `n8n-workflows/extract-quote-request.json`
4. Ensure `OPENAI_API_KEY` is set in `prototype/.env` (passed to n8n container via docker-compose)
5. Execute the workflow — it processes all 5 embedded email fixtures through GPT-4o extraction

> **Note (n8n 2.12+):** Code nodes require `N8N_RUNNERS_ENABLED=false` and `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` to access `$env` variables. These are already configured in `docker-compose.yml`.

**Workflow structure:**
```
[Manual Trigger] → [Load Email Fixtures] → [LLM Extract Structured Data] → [Results Summary]
```

The extraction node calls GPT-4o with `temperature: 0` and `response_format: json_object` for deterministic, structured output. It validates the response (handles malformed JSON, missing fields) before passing to the summary node.

**For future IMAP integration** (Story 0.6 or production): replace Manual Trigger + Load Email Fixtures with an Email Trigger (IMAP) node. The extraction and summary nodes stay the same.

### Test Script (Local)

```bash
# Install dependency (if not already)
pip install python-dotenv

# Run all 5 test fixtures
python3 scripts/test-email-extraction.py

# Run a single fixture
python3 scripts/test-email-extraction.py email_jargon
```

Requires `OPENAI_API_KEY` in environment or `prototype/.env`.

### Test Results (GPT-4o, temperature=0)

| Fixture | Scenario | Products | Reference | Delivery | Latency | Status |
|---------|----------|----------|-----------|----------|---------|--------|
| `email_simple_ref` | Single product with exact ref | 1/1 ✓ | BHM-M12x50 ✓ | N/A ✓ | 2.3s | PASS |
| `email_multi_products` | 4 products, delivery date | 4/4 ✓ | — ✓ | 15 avril ✓ | 3.8s | PASS |
| `email_jargon` | Industrial French jargon (DN, lg, certif) | 3/3 ✓ | — ✓ | N/A ✓ | 3.1s | PASS |
| `email_previous_order` | References past order | 3/3 ✓ | — ✓ | N/A ✓ | 2.0s | PASS |
| `email_vague` | Minimal detail, vague descriptions | 2/2 ✓ | — ✓ | N/A ✓ | 1.7s | PASS |

**Summary: 5/5 passed** | Average latency: 2.6s

**Key observations:**
- GPT-4o handles French industrial jargon well (DN, lg, inox, certif 3.1)
- Multi-product extraction is reliable (4 products in one email)
- Vague descriptions are handled correctly (null quantity when unspecified)
- Client name extraction prefers company name over person name
- Reference codes (BHM-M12x50) are correctly identified and extracted

### Edge Cases

| Case | Handling |
|------|----------|
| Non-quote email | Extraction returns empty products array, notes describe content |
| Empty body | Products array empty, all fields null |
| Attachments only | Not handled in prototype (production Epic 2 will parse attachments) |
| Multiple languages | GPT-4o handles French/English mix; prompt instructs French context |
| Malformed LLM output | Code node catches JSON parse errors, returns error status |

### Email Fixtures

Sample emails in `data/emails/`:

| File | Scenario |
|------|----------|
| `email_simple_ref.json` | Single product with exact reference code |
| `email_multi_products.json` | 4 products in one email with delivery date |
| `email_jargon.json` | Industrial French jargon and abbreviations |
| `email_previous_order.json` | References to past orders |
| `email_vague.json` | Minimal detail, vague product descriptions |

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
