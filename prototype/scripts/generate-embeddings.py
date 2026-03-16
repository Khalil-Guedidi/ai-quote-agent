#!/usr/bin/env python3
"""Generate vector embeddings from raw product catalog and index in Qdrant.

Reads products_raw.json (Story 0.2 output), generates embeddings using
BAAI/bge-m3 (multilingual, 1024 dims), and upserts into a Qdrant collection.

No preprocessing or cleaning is applied — raw product fields are concatenated
as-is to validate semantic search on uncleaned data.
"""

import json
import os
import sys
import time

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOTYPE_DIR = os.path.dirname(SCRIPT_DIR)
CATALOG_PATH = os.path.join(PROTOTYPE_DIR, "data", "catalog", "products_raw.json")

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "products"
MODEL_NAME = "BAAI/bge-m3"
BATCH_SIZE = 32


def load_products(path: str) -> list[dict]:
    """Load products from the raw catalog JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle n8n output format: [{"products": [...]}]
    if isinstance(data, list) and len(data) == 1 and "products" in data[0]:
        return data[0]["products"]
    if isinstance(data, dict) and "products" in data:
        return data["products"]
    if isinstance(data, list) and len(data) > 0 and "id" in data[0]:
        return data
    raise ValueError(
        f"Unexpected catalog format in {path}. "
        f"Got {type(data).__name__}, top-level keys: "
        f"{list(data.keys()) if isinstance(data, dict) else 'N/A'}"
    )


def build_product_text(product: dict) -> str:
    """Construct text for embedding from raw product fields.

    NO cleaning, NO HTML stripping, NO deduplication — raw concatenation.
    Odoo returns False (not None) for empty fields, so we check truthiness.
    """
    parts = []
    if product.get("name"):
        parts.append(product["name"])
    if product.get("default_code"):
        parts.append(f"Ref: {product['default_code']}")
    # categ_id is [id, "Category Name"] in Odoo JSON-RPC response
    categ = product.get("categ_id")
    if categ and isinstance(categ, list) and len(categ) >= 2:
        parts.append(categ[1])
    if product.get("description_sale"):
        parts.append(product["description_sale"])
    if product.get("description"):
        parts.append(product["description"])
    return " | ".join(parts)


def main():
    # Load catalog
    if not os.path.exists(CATALOG_PATH):
        print(f"ERROR: Catalog file not found: {CATALOG_PATH}")
        print("Run Story 0.2 ingestion workflow first to generate products_raw.json")
        sys.exit(1)

    print(f"Loading catalog from {CATALOG_PATH}...")
    products = load_products(CATALOG_PATH)
    print(f"Loaded {len(products)} products")

    # Build texts for embedding
    print("Building text representations from raw product fields...")
    texts = [build_product_text(p) for p in products]
    empty_ids = [p["id"] for p, t in zip(products, texts) if not t.strip()]
    if empty_ids:
        print(f"WARNING: {len(empty_ids)} products have empty text representations (IDs: {empty_ids})")

    # Load embedding model
    print(f"Loading embedding model: {MODEL_NAME}")
    print("(First run downloads ~2.3 GB from HuggingFace — this may take a while)")
    model_start = time.time()
    model = SentenceTransformer(MODEL_NAME)
    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")

    # Generate embeddings in batches
    print(f"Generating embeddings (batch size: {BATCH_SIZE})...")
    embed_start = time.time()
    all_embeddings = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(texts), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch_texts = texts[i : i + BATCH_SIZE]
        batch_embeddings = model.encode(
            batch_texts, normalize_embeddings=True, show_progress_bar=False
        )
        all_embeddings.extend(batch_embeddings)
        elapsed = time.time() - embed_start
        print(
            f"  Batch {batch_num}/{total_batches} processed "
            f"({len(all_embeddings)} products total, {elapsed:.1f}s elapsed)"
        )

    embed_time = time.time() - embed_start
    embedding_dim = all_embeddings[0].shape[0]
    print(
        f"Embedding generation complete: {len(all_embeddings)} vectors, "
        f"{embedding_dim} dimensions, {embed_time:.1f}s total"
    )

    # Connect to Qdrant and create collection
    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    if client.collection_exists(COLLECTION_NAME):
        print(f"WARNING: Deleting existing collection '{COLLECTION_NAME}'")
        client.delete_collection(COLLECTION_NAME)
    print(f"Creating collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
    )

    # Upsert vectors with full product data as payload (batch to limit memory)
    print("Upserting vectors into Qdrant...")
    upsert_start = time.time()
    for i in range(0, len(products), BATCH_SIZE):
        batch_products = products[i : i + BATCH_SIZE]
        batch_embeddings = all_embeddings[i : i + BATCH_SIZE]
        points = [
            PointStruct(
                id=product["id"],
                vector=embedding.tolist(),
                payload=product,
            )
            for product, embedding in zip(batch_products, batch_embeddings)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    upsert_time = time.time() - upsert_start
    print(f"Upsert complete: {len(points)} vectors indexed in {upsert_time:.1f}s")

    # Verify
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    print(f"Products processed: {len(products)}")
    print(f"Embedding model: {MODEL_NAME}")
    print(f"Embedding dimensions: {embedding_dim}")
    print(f"Model load time: {model_load_time:.1f}s")
    print(f"Embedding time: {embed_time:.1f}s")
    print(f"Upsert time: {upsert_time:.1f}s")
    print(f"Total time: {time.time() - model_start:.1f}s")
    print(f"Collection '{COLLECTION_NAME}': {collection_info.points_count} vectors")
    print(f"Distance metric: COSINE")
    print(f"Dashboard: http://{QDRANT_HOST}:{QDRANT_PORT}/dashboard")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
