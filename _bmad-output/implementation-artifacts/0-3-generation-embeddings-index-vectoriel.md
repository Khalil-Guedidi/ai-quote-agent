# Story 0.3: Génération Embeddings + Index Vectoriel sur Catalogue Brut

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want to generate vector embeddings from the raw product catalog and create a searchable vector index,
So that I can test semantic search on uncleaned product data.

## Acceptance Criteria

1. **AC-0.3.1**: Embedding generation pipeline on raw catalog entries (no preprocessing)
   - Given: The raw catalog file `data/catalog/products_raw.json` from Story 0.2 exists (~720 products)
   - When: The developer runs the embedding generation script
   - Then: Vector embeddings are generated for every product entry using a multilingual embedding model
   - And: The text input for each embedding is constructed by concatenating raw product fields (name, default_code, category name, description) — NO cleaning, NO HTML stripping, NO deduplication
   - And: The script logs progress (products processed, time taken, embedding dimensions)

2. **AC-0.3.2**: Vector index created and queryable (Qdrant via Docker)
   - Given: Embeddings have been generated for all catalog products
   - When: The developer checks the Qdrant dashboard
   - Then: A collection named `products` exists in Qdrant with ~720 vectors
   - And: Each vector point includes the full raw product data as payload (id, name, default_code, barcode, list_price, categ_id, sale_ok, active, descriptions)
   - And: The collection uses HNSW indexing with cosine distance metric
   - And: The Qdrant REST API responds to search queries at `http://localhost:6333`

3. **AC-0.3.3**: Basic semantic search returning relevant results on test queries
   - Given: The vector index is populated with product embeddings
   - When: The developer runs semantic search with test queries like:
     - "tube acier inoxydable" (standard French product query)
     - "boulon haute résistance M12" (abbreviation-heavy query)
     - "tuyau DN50" (technical reference)
     - "plaque acier sur mesure" (custom product — should still match)
   - Then: Each query returns top-5 results with similarity scores
   - And: Results are visually relevant (manual inspection — correct product family)
   - And: Search response time is < 500ms per query

4. **AC-0.3.4**: Embedding model selection documented with rationale
   - Given: The embedding pipeline has been tested
   - When: The developer reads the documentation
   - Then: A section in `prototype/README.md` documents:
     - The chosen embedding model and why
     - Embedding dimensions and model size
     - Text construction strategy (which fields, how concatenated)
     - Indexing performance (time to embed all products, memory usage)
     - 3-5 sample search queries with result quality assessment
     - Known limitations and considerations for production

## Tasks / Subtasks

- [x] Task 1: Add Qdrant to Docker environment (AC: #2)
  - [x] 1.1: Add `qdrant/qdrant` service to `prototype/docker-compose.yml` — expose port 6333 (HTTP API) and 6334 (gRPC), persistent volume, on `proto-net` network
  - [x] 1.2: Verify Qdrant starts and dashboard is accessible at `http://localhost:6333/dashboard`

- [x] Task 2: Create embedding generation + indexing script (AC: #1, #2)
  - [x] 2.1: Create `prototype/scripts/generate-embeddings.py` — reads `data/catalog/products_raw.json`, generates embeddings, upserts into Qdrant
  - [x] 2.2: Implement text construction from raw product fields (concatenate name + default_code + category + descriptions — no cleaning)
  - [x] 2.3: Use `sentence-transformers` with `BAAI/bge-m3` model for embedding generation
  - [x] 2.4: Upsert vectors into Qdrant collection `products` with full product data as payload, using cosine distance and HNSW index
  - [x] 2.5: Add progress logging (batch processing, time per batch, total time)

- [x] Task 3: Create semantic search verification script (AC: #3)
  - [x] 3.1: Create `prototype/scripts/test-semantic-search.py` — accepts a query string, returns top-5 results with scores
  - [x] 3.2: Include a default set of test queries (at least 5) that exercise different search scenarios (standard, abbreviation, technical ref, jargon, custom product)
  - [x] 3.3: Display results in a readable format: rank, score, product name, default_code, category

- [x] Task 4: Documentation (AC: #4)
  - [x] 4.1: Update `prototype/README.md` with embedding generation and vector search section
  - [x] 4.2: Document model choice rationale, performance metrics, and sample results

## Dev Notes

### Critical: Reuse Story 0.2 Output

Story 0.2 produces `prototype/data/catalog/products_raw.json` — the raw Odoo product catalog (~720 products, JSON array of objects). This is the input for embedding generation. The file must exist before running the embedding script. The data is intentionally "dirty" (duplicates, HTML in descriptions, case variations, abbreviations, missing fields).

**DO NOT** clean, preprocess, or transform the product data before embedding. The entire point is to validate that semantic search works on raw, uncleaned data (PRD: "zero-preprocessing" promise, FR5, FR9).

### Embedding Model: BAAI/bge-m3

The architecture document specifies `BGE-M3 or multilingual-e5-large` as the production embedding model. **Use BGE-M3** for the prototype to validate the production choice.

**BGE-M3 specs:**
- **Model ID**: `BAAI/bge-m3` (on HuggingFace)
- **Dimensions**: 1024
- **Parameters**: 568M (~2.3 GB download on first run)
- **Max tokens**: 8192
- **Languages**: 100+ (French and English required for this project)
- **Retrieval modes**: Dense, sparse, and multi-vector (use dense for this story)
- **Framework**: `sentence-transformers` (or `FlagEmbedding` library)

**Usage with sentence-transformers:**
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")
embeddings = model.encode(texts, normalize_embeddings=True)
# Returns numpy array of shape (n_texts, 1024)
```

**Important**: BGE-M3 expects `normalize_embeddings=True` for cosine similarity search. Set this in the encode call.

**First run**: The model will download ~2.3 GB from HuggingFace. Subsequent runs use the cached model from `~/.cache/huggingface/`. Document this in README.

### Text Construction Strategy for Embeddings

Construct a single text string per product by concatenating raw fields. Do NOT strip HTML, do NOT normalize casing, do NOT deduplicate — the embedding model must handle the noise.

**Recommended text template:**
```python
def build_product_text(product: dict) -> str:
    parts = []
    if product.get("name"):
        parts.append(product["name"])
    if product.get("default_code"):
        parts.append(f"Ref: {product['default_code']}")
    # categ_id is [id, "Category Name"] in Odoo JSON-RPC response
    if product.get("categ_id") and isinstance(product["categ_id"], list):
        parts.append(product["categ_id"][1])
    if product.get("description_sale"):
        parts.append(product["description_sale"])
    if product.get("description"):
        parts.append(product["description"])
    return " | ".join(parts)
```

This preserves ALL the noise (HTML tags, weird spacing, abbreviations) while giving the model enough context for semantic understanding. The `|` separator helps the model distinguish fields without confusing content boundaries.

### Qdrant Setup

**Docker Compose addition:**
```yaml
qdrant:
  image: qdrant/qdrant:latest
  container_name: proto-qdrant
  ports:
    - "${QDRANT_PORT:-6333}:6333"
    - "6334:6334"
  volumes:
    - qdrant-data:/qdrant/storage
  networks:
    - proto-net
  healthcheck:
    test: ["CMD-SHELL", "wget -qO- http://localhost:6333/healthz || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Add `qdrant-data:` to the `volumes:` section.

**Why Qdrant (not pgvector for prototype):**
- The AC explicitly mentions Qdrant as an option
- Purpose-built for vector search — better dashboard, easier debugging
- n8n has a built-in Qdrant Vector Store node (useful for Story 0.4 hybrid search workflows)
- Production will use pgvector (architecture decision) — the prototype validates the embedding/search concept independently
- Qdrant dashboard at `http://localhost:6333/dashboard` gives visual verification of indexed data

**Qdrant Python client:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

client = QdrantClient(host="localhost", port=6333)

# Create collection
client.recreate_collection(
    collection_name="products",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
)

# Upsert points
client.upsert(
    collection_name="products",
    points=[
        PointStruct(
            id=product["id"],
            vector=embedding.tolist(),
            payload=product,  # store full raw product data
        )
        for product, embedding in zip(products, embeddings)
    ],
)

# Search
results = client.query_points(
    collection_name="products",
    query=query_embedding.tolist(),
    limit=5,
)
```

### Dependencies

The embedding script runs on the **host machine** (like the seeder in Story 0.2). Install:
```bash
pip install sentence-transformers qdrant-client
```

Or add a `prototype/requirements.txt` with:
```
requests
sentence-transformers
qdrant-client
```

(`requests` was already used by Story 0.2's seeder script)

### Environment Variables

Add to `prototype/.env.example`:
```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

The script should read these from `.env` (consistent with Story 0.2 pattern — use `dotenv` or just default values since this is prototype).

### Batch Processing

BGE-M3 with 568M params can be memory-intensive. Process embeddings in batches:
- **Batch size**: 32 products (adjust based on available RAM/GPU)
- **Expected time**: ~30-120 seconds for 720 products on CPU (depends on hardware)
- **GPU**: If CUDA available, `sentence-transformers` will auto-detect and use GPU (much faster, ~5-10 seconds)
- Log progress: "Batch X/Y processed (Z products total, T seconds elapsed)"

### Search Verification: Expected Behavior

The test queries should demonstrate that semantic search finds relevant products DESPITE the dirty catalog:

| Query | Expected Match Type | Why It's Interesting |
|-------|-------------------|---------------------|
| "tube acier inoxydable" | Standard name match | Basic semantic match on French product name |
| "boulon haute résistance M12" | Abbreviation match | Catalog has "Boul. HM 8.8 M12x60" — tests semantic understanding of abbreviations |
| "tuyau DN50" | Technical reference | Tests that "DN50" / "DN 50" / "DN-50" variations are captured semantically |
| "plaque acier sur mesure" | Custom product | Should match "SUR MESURE - Plaque acier" items |
| "safety helmet" | Cross-lingual | Tests multilingual capability (English → French catalog) |

The test script should print results clearly so the developer can manually assess quality. No automated accuracy threshold in this story — that's Story 0.4.

### Gotchas to Avoid

1. **Do NOT preprocess or clean the catalog data** — embed the raw fields as-is
2. **Do NOT use OpenAI embeddings API** — architecture specifies local model (BGE-M3). This validates offline/self-hosted capability
3. **Do NOT forget `normalize_embeddings=True`** — BGE-M3 needs this for correct cosine similarity
4. **Do NOT hardcode paths** — use relative paths from `prototype/` or read from env
5. **BGE-M3 first download is ~2.3 GB** — document this clearly, it will take time
6. **Qdrant `recreate_collection`** — this deletes and recreates. Safe for prototype, but log a warning
7. **Product `id` from Odoo is an integer** — Qdrant accepts integers as point IDs, this is fine
8. **Some products may have `False` for text fields (Odoo returns `False` not `null`)** — handle this in text construction (check for truthy values, not just `is not None`)
9. **Memory**: BGE-M3 loads ~2.3 GB into RAM. Ensure the dev machine has sufficient memory (4 GB+ free recommended)

### Project Structure Notes

- All files go under `prototype/` directory (consistent with Stories 0.1, 0.2)
- New files: `scripts/generate-embeddings.py`, `scripts/test-semantic-search.py`, `requirements.txt`
- Modified files: `docker-compose.yml` (add Qdrant service), `.env.example` (add Qdrant vars), `README.md` (add documentation)
- No conflict with the architecture's `src/` structure — prototype is isolated

### Previous Story Intelligence

From **Story 0.2** implementation:
- **OdooRPC class bug**: Initial implementation used a global variable instead of `self.password` in `execute_kw`. Lesson: be careful with class method scoping
- **Odoo `False` vs `None`**: Odoo JSON-RPC returns `False` (Python boolean) for empty fields, not `null`/`None`. The product data in `products_raw.json` will contain `false` values — handle these in text construction
- **`active_test: false` context**: The catalog includes archived products (`active=False`). They should be embedded too — filtering happens at search time (Story 0.4+)
- **File output pattern**: Story 0.2 writes to `data/catalog/products_raw.json`. The embedding script reads from this same path
- **Script pattern**: Use standalone Python scripts (not n8n) for data processing. Same approach as `seed-catalog.py`

### Git Intelligence

Recent commits show:
- `ddd9e53` — Story 0.2: seed-catalog.py, ingest-catalog.json, docker-compose volume mount, README update
- `c934f15` — BMAD framework setup
- `34866aa` — Story 0.1: Docker environment with n8n + Odoo

Pattern: each story commits all new/modified files together with a descriptive message.

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 0, Story 0.3]
- [Source: _bmad-output/planning-artifacts/architecture.md - Data Architecture: PostgreSQL+pgvector, HNSW, BGE-M3/multilingual-e5-large, Hybrid search]
- [Source: _bmad-output/planning-artifacts/prd.md - FR5 (semantic search on raw catalogs), FR9 (zero-preprocessing ingestion)]
- [Source: _bmad-output/implementation-artifacts/0-2-ingestion-catalogue-odoo.md - Raw catalog output, Odoo field structure, lessons learned]
- [BAAI/bge-m3 on HuggingFace](https://huggingface.co/BAAI/bge-m3) — Model card, 1024 dims, 568M params, 100+ languages
- [Qdrant Docker quickstart](https://qdrant.tech/documentation/quickstart/) — Docker image, REST API on port 6333, gRPC on 6334
- [qdrant-client PyPI](https://pypi.org/project/qdrant-client/) — Python client for Qdrant
- [Qdrant n8n integration](https://qdrant.tech/documentation/platforms/n8n/) — Official n8n node for Qdrant (relevant for Story 0.4)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Qdrant deprecation warning on `recreate_collection` — fixed to use `collection_exists` + `create_collection`
- products_raw.json format is `[{"products": [...]}]` (n8n output wrapping) — handled in load_products()

### Completion Notes List

- Task 1: Added Qdrant service to docker-compose.yml (port 6333/6334, persistent volume, healthcheck, proto-net network). Added QDRANT_HOST/PORT to .env.example. Verified dashboard accessible.
- Task 2: Created generate-embeddings.py — loads 726 raw products, builds text from raw fields (no cleaning), generates 1024-dim embeddings with BAAI/bge-m3, upserts into Qdrant `products` collection with full payload. Batch processing (32) with progress logging. Total time ~126s on CPU.
- Task 3: Created test-semantic-search.py — 5 default test queries covering standard, abbreviation, technical ref, custom product, and cross-lingual scenarios. All respond < 500ms (avg 91ms). Results demonstrate semantic relevance on uncleaned data.
- Task 4: Updated prototype/README.md with embedding model rationale, text construction strategy, performance metrics, sample search results table, and known limitations.

### Change Log

- 2026-03-16: Story 0.3 implementation complete — embedding pipeline + Qdrant vector index + semantic search verification + documentation
- 2026-03-16: Code review fixes — batch upsert to reduce memory (M1), improved error message on unexpected catalog format (M2), multi-query arg support in test script (M3), gRPC port env var (L1), empty-text warning now shows product IDs (L2)

### File List

- prototype/docker-compose.yml (modified — added qdrant service and qdrant-data volume)
- prototype/.env.example (modified — added QDRANT_HOST, QDRANT_PORT)
- prototype/requirements.txt (new — requests, sentence-transformers, qdrant-client)
- prototype/scripts/generate-embeddings.py (new — embedding generation + Qdrant indexing)
- prototype/scripts/test-semantic-search.py (new — semantic search verification)
- prototype/README.md (modified — added embedding/vector search documentation section)
