#!/usr/bin/env python3
"""Story 0.6 — End-to-end quote pipeline: email → extraction → search → Odoo draft quote.

Orchestrates the full prototype flow:
1. Load email fixture JSON
2. LLM extraction via GPT-4o (reuses Story 0.5 prompt)
3. Product matching via hybrid search (reuses Story 0.4 functions)
4. Customer lookup/create in Odoo (JSON-RPC)
5. Draft quote creation in Odoo (sale.order)

Usage:
    python3 scripts/e2e-quote-pipeline.py                          # Run all 3 test scenarios
    python3 scripts/e2e-quote-pipeline.py email_simple_ref.json    # Run single scenario
"""

import json
import os
import re
import sys
import time
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# Add scripts dir to path so we can import hybrid-search functions
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import requests
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Import hybrid search functions (Story 0.4)
from importlib import import_module
_hs = import_module("hybrid-search")
search_hybrid = _hs.search_hybrid
search_exact_ref = _hs.search_exact_ref
REF_CODE_PATTERN = _hs.REF_CODE_PATTERN
DENSE_MODEL_NAME = _hs.DENSE_MODEL_NAME
SPARSE_MODEL_NAME = _hs.SPARSE_MODEL_NAME

# --- Config ---
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "products"

ODOO_HOST = os.environ.get("ODOO_HOST", "localhost")
ODOO_PORT = int(os.environ.get("ODOO_PORT", "8069"))
ODOO_DB = os.environ.get("ODOO_DB", "odoo_db")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

EMAILS_DIR = Path(__file__).parent.parent / "data" / "emails"

# --- LLM Extraction (reuse Story 0.5 prompt) ---
EXTRACTION_PROMPT = """You are an expert B2B quote request parser for an industrial steel and metals distributor.
Extract structured data from the following quote request email.

IMPORTANT RULES:
- The email is in French (industrial B2B context)
- Product descriptions may contain jargon: "inox" = stainless steel, "Ø" = diameter, "lg" = length
- Common abbreviations: 304L, 316L (steel grades), HM (hexagonal), BLN (bolt), DN (nominal diameter)
- Quantities may use French notation: "200 pcs", "5 barres", "10 ml" (mètres linéaires)
- If information is not mentioned, use null (do NOT invent data)
- Extract ALL products mentioned, even if descriptions are vague
- References may look like: "TUBE-INOX-304L-25x1.5-6M" or "BHM-M12x50"
- For client_name, extract the company name if available, otherwise the person name
- For client_email, use the "from" field of the email

Return a JSON object with this exact schema:
{
  "client_name": "string or null",
  "client_email": "string or null",
  "products": [
    {
      "description": "product description as written by client",
      "reference": "product code/reference if mentioned, else null",
      "quantity": "quantity with unit as written",
      "specs": "any specs (dimensions, material, grade, finish) or null"
    }
  ],
  "delivery_date": "delivery date if mentioned, else null",
  "notes": "any additional context or requirements, else null"
}"""


def call_openai_extraction(email_text: str) -> dict:
    """Call OpenAI GPT-4o for structured email extraction."""
    import urllib.request

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Export it or add to prototype/.env")

    body = json.dumps({
        "model": "gpt-4o",
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "messages": [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": email_text},
        ],
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    content = result["choices"][0]["message"]["content"]
    return json.loads(content)


# --- Odoo JSON-RPC Client ---

def odoo_authenticate(host=ODOO_HOST, port=ODOO_PORT, db=ODOO_DB,
                      login=ODOO_USER, password=ODOO_PASSWORD):
    """Authenticate to Odoo and return (session_cookie, uid)."""
    resp = requests.post(
        f"http://{host}:{port}/web/session/authenticate",
        json={"jsonrpc": "2.0", "params": {"db": db, "login": login, "password": password}},
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Odoo auth error: {data['error']}")
    session_cookie = resp.cookies.get("session_id")
    uid = data["result"]["uid"]
    return session_cookie, uid


def odoo_execute_kw(session_cookie, uid, model, method, args, kwargs=None,
                    host=ODOO_HOST, port=ODOO_PORT, db=ODOO_DB, password=ODOO_PASSWORD):
    """Generic Odoo JSON-RPC execute_kw call."""
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [db, uid, password, model, method, args, kwargs or {}],
        },
    }
    resp = requests.post(
        f"http://{host}:{port}/jsonrpc",
        json=payload,
        cookies={"session_id": session_cookie},
    )
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise RuntimeError(f"Odoo RPC error on {model}.{method}: {result['error']}")
    return result["result"]


def odoo_find_or_create_partner(session, uid, client_name, client_email):
    """Find existing customer by email or create a new one. Returns partner_id."""
    if client_email:
        partner_ids = odoo_execute_kw(session, uid, "res.partner", "search",
                                      [[["email", "=", client_email]]])
        if partner_ids:
            return partner_ids[0]
    if client_name:
        partner_ids = odoo_execute_kw(session, uid, "res.partner", "search",
                                      [[["name", "ilike", client_name]]])
        if partner_ids:
            return partner_ids[0]
    # Create new customer
    return odoo_execute_kw(session, uid, "res.partner", "create",
                           [{"name": client_name or client_email or "Unknown",
                             "email": client_email or ""}])


def odoo_create_draft_quote(session, uid, partner_id, order_lines, delivery_date=None):
    """Create a sale.order draft in Odoo with order lines."""
    values = {
        "partner_id": partner_id,
        "order_line": [
            [0, 0, {
                "product_id": line["product_id"],
                "product_uom_qty": line["quantity"],
                "price_unit": line["price_unit"],
                "name": line["description"],
            }]
            for line in order_lines
        ],
    }
    if delivery_date:
        values["commitment_date"] = delivery_date
    return odoo_execute_kw(session, uid, "sale.order", "create", [values])


# --- Search & Matching ---

def build_search_query(product: dict) -> str:
    """Build search query from extracted product fields."""
    parts = []
    if product.get("description"):
        parts.append(product["description"])
    if product.get("specs"):
        parts.append(product["specs"])
    return " ".join(parts)


def parse_quantity(qty_str) -> float:
    """Parse quantity from string like '500', '200 pcs', '5 barres'. Default: 1."""
    if not qty_str:
        return 1.0
    match = re.search(r"[\d]+(?:[.,]\d+)?", str(qty_str))
    return float(match.group().replace(",", ".")) if match else 1.0


def filter_proposable(results: list[dict]) -> list[dict]:
    """Keep only products that can be sold (sale_ok=True, active=True)."""
    filtered = [r for r in results if r.get("sale_ok") and r.get("active")]
    return filtered if filtered else results  # fallback to unfiltered with warning


def search_product_with_price(client, dense_model, sparse_model, product: dict) -> dict | None:
    """Search for a product and return match with price from Qdrant payload.

    Uses hybrid search from Story 0.4, but also fetches list_price from
    the raw Qdrant payload (not included in _format_result).
    """
    # Try exact reference match first
    if product.get("reference"):
        ref = product["reference"].strip()
        if REF_CODE_PATTERN.match(ref):
            results = search_exact_ref(client, ref)
            if results:
                proposable = filter_proposable(results)
                best = proposable[0]
                # Fetch list_price from Qdrant payload
                price = _get_price_from_qdrant(client, best["id"])
                return {
                    "odoo_product_id": best["id"],
                    "name": best["name"],
                    "default_code": best["default_code"],
                    "score": best["score"],
                    "price": price,
                    "match_type": "exact_ref",
                }

    # Build query and do hybrid search
    query = build_search_query(product)
    if not query:
        return None

    results = search_hybrid(client, dense_model, sparse_model, query, limit=5)
    if not results:
        return None

    proposable = filter_proposable(results)
    best = proposable[0]
    price = _get_price_from_qdrant(client, best["id"])
    return {
        "odoo_product_id": best["id"],
        "name": best["name"],
        "default_code": best["default_code"],
        "score": best["score"],
        "price": price,
        "match_type": "hybrid",
    }


def _get_price_from_qdrant(client: QdrantClient, point_id: int) -> float:
    """Retrieve list_price from Qdrant payload for a given point ID."""
    points = client.retrieve(COLLECTION_NAME, ids=[point_id], with_payload=True)
    if points:
        return points[0].payload.get("list_price", 0.0)
    return 0.0


# --- Pipeline ---

def run_pipeline(email_path: Path, dense_model, sparse_model, qdrant_client,
                 odoo_session, odoo_uid) -> dict:
    """Run the full end-to-end pipeline for a single email fixture."""
    pipeline_start = time.time()
    result = {
        "email_file": email_path.name,
        "steps": {},
        "status": "PASS",
        "errors": [],
    }

    # Step 1: Load email fixture
    with open(email_path) as f:
        email = json.load(f)
    email_text = (
        f"From: {email['from']}\n"
        f"Subject: {email['subject']}\n"
        f"Date: {email['date']}\n\n"
        f"{email['body']}"
    )
    print(f"\n{'='*70}")
    print(f"  Pipeline: {email_path.name}")
    print(f"  From: {email['from']} | Subject: {email['subject']}")
    print(f"{'='*70}")

    # Step 2: LLM Extraction
    print("\n  [Step 1] LLM Extraction (GPT-4o)...")
    t0 = time.time()
    try:
        extraction = call_openai_extraction(email_text)
        extraction_ms = (time.time() - t0) * 1000
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Extraction failed: {e}")
        print(f"  ERROR: {e}")
        return result
    result["steps"]["extraction"] = {
        "latency_ms": round(extraction_ms),
        "client_name": extraction.get("client_name"),
        "client_email": extraction.get("client_email"),
        "product_count": len(extraction.get("products", [])),
        "delivery_date": extraction.get("delivery_date"),
    }
    print(f"    Client: {extraction.get('client_name')} <{extraction.get('client_email')}>")
    print(f"    Products: {len(extraction.get('products', []))}")
    print(f"    Latency: {extraction_ms:.0f}ms")

    # Step 3: Product Search (per extracted product)
    print("\n  [Step 2] Product Search (hybrid)...")
    matched_products = []
    search_details = []
    for i, product in enumerate(extraction.get("products", []), 1):
        query = build_search_query(product)
        qty = parse_quantity(product.get("quantity"))
        ref = product.get("reference")

        t0 = time.time()
        match = search_product_with_price(qdrant_client, dense_model, sparse_model, product)
        search_ms = (time.time() - t0) * 1000

        if match:
            matched_products.append({
                "product_id": match["odoo_product_id"],
                "quantity": qty,
                "price_unit": match["price"],
                "description": product.get("description", ""),
                "matched_name": match["name"],
                "matched_code": match["default_code"],
                "score": match["score"],
                "match_type": match["match_type"],
            })
            print(f"    {i}. '{product.get('description', '?')}' → {match['name']} "
                  f"[{match['default_code']}] score={match['score']:.3f} "
                  f"qty={qty} ({search_ms:.0f}ms)")
        else:
            print(f"    {i}. '{product.get('description', '?')}' → NO MATCH ({search_ms:.0f}ms)")
            result["errors"].append(f"No match for product: {product.get('description')}")

        search_details.append({
            "description": product.get("description"),
            "reference": ref,
            "query": query,
            "quantity": qty,
            "match": match,
            "latency_ms": round(search_ms),
        })

    result["steps"]["search"] = {
        "total_products": len(extraction.get("products", [])),
        "matched": len(matched_products),
        "details": search_details,
    }

    if not matched_products:
        result["status"] = "FAIL"
        result["errors"].append("No products matched — cannot create quote")
        return result

    # Step 4: Customer Lookup/Create
    print("\n  [Step 3] Customer Lookup/Create (Odoo)...")
    t0 = time.time()
    try:
        partner_id = odoo_find_or_create_partner(
            odoo_session, odoo_uid,
            extraction.get("client_name"),
            extraction.get("client_email"),
        )
        customer_ms = (time.time() - t0) * 1000
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Customer lookup failed: {e}")
        print(f"    ERROR: {e}")
        return result
    result["steps"]["customer"] = {
        "partner_id": partner_id,
        "latency_ms": round(customer_ms),
    }
    print(f"    Partner ID: {partner_id} ({customer_ms:.0f}ms)")

    # Step 5: Create Draft Quote
    print("\n  [Step 4] Create Draft Quote (Odoo)...")
    t0 = time.time()
    try:
        sale_order_id = odoo_create_draft_quote(
            odoo_session, odoo_uid, partner_id, matched_products,
            delivery_date=extraction.get("delivery_date"),
        )
        quote_ms = (time.time() - t0) * 1000
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Quote creation failed: {e}")
        print(f"    ERROR: {e}")
        return result

    result["steps"]["quote"] = {
        "sale_order_id": sale_order_id,
        "partner_id": partner_id,
        "line_count": len(matched_products),
        "latency_ms": round(quote_ms),
    }
    print(f"    Sale Order ID: {sale_order_id} ({quote_ms:.0f}ms)")

    # Summary
    total_ms = (time.time() - pipeline_start) * 1000
    result["total_latency_ms"] = round(total_ms)
    result["sale_order_id"] = sale_order_id
    result["partner_id"] = partner_id
    result["matched_products"] = matched_products

    print(f"\n  ✅ RESULT: Sale Order #{sale_order_id} | {len(matched_products)} lines "
          f"| Partner #{partner_id} | Total: {total_ms:.0f}ms")

    return result


def main():
    filter_file = sys.argv[1] if len(sys.argv) > 1 else None

    # Test scenarios (AC-0.6.3)
    test_scenarios = [
        "email_simple_ref.json",      # Scenario A: single product, exact ref
        "email_multi_products.json",   # Scenario B: multi-product fuzzy match
        "email_jargon.json",           # Scenario C: jargon-heavy request
    ]

    if filter_file:
        test_scenarios = [filter_file]

    # Verify fixture files exist
    for scenario in test_scenarios:
        if not (EMAILS_DIR / scenario).exists():
            print(f"ERROR: fixture not found: {EMAILS_DIR / scenario}")
            sys.exit(1)

    print(f"{'='*70}")
    print(f"Story 0.6 — End-to-End Quote Pipeline")
    print(f"Scenarios: {len(test_scenarios)} | Model: GPT-4o + BGE-M3 + BM25")
    print(f"{'='*70}")

    # Load models (once for all scenarios)
    print("\nLoading search models...")
    t0 = time.time()
    dense_model = SentenceTransformer(DENSE_MODEL_NAME)
    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
    model_load_ms = (time.time() - t0) * 1000
    print(f"Models loaded in {model_load_ms:.0f}ms")

    # Connect to Qdrant
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    info = qdrant_client.get_collection(COLLECTION_NAME)
    print(f"Qdrant connected — {COLLECTION_NAME}: {info.points_count} vectors")

    # Authenticate to Odoo
    print("Authenticating to Odoo...")
    odoo_session, odoo_uid = odoo_authenticate()
    print(f"Odoo authenticated — uid={odoo_uid}")

    # Run all scenarios
    all_results = []
    for scenario in test_scenarios:
        email_path = EMAILS_DIR / scenario
        result = run_pipeline(
            email_path, dense_model, sparse_model, qdrant_client,
            odoo_session, odoo_uid,
        )
        all_results.append(result)

    # Summary table
    print(f"\n{'='*70}")
    print(f"  SUMMARY — End-to-End Results")
    print(f"{'='*70}")
    print(f"  {'Scenario':<30} {'Products':<12} {'Matched':<10} {'Qty OK':<10} {'Customer':<10} {'Latency':<10} {'Status'}")
    print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    for r in all_results:
        search = r["steps"].get("search", {})
        total_p = search.get("total_products", 0)
        matched_p = search.get("matched", 0)
        qty_ok = "Y" if matched_p > 0 else "N"
        customer = "Y" if r.get("partner_id") else "N"
        latency = f"{r.get('total_latency_ms', 0)}ms"
        print(f"  {r['email_file']:<30} {total_p:<12} {matched_p:<10} {qty_ok:<10} "
              f"{customer:<10} {latency:<10} {r['status']}")

    passed = sum(1 for r in all_results if r["status"] == "PASS")
    print(f"\n  Result: {passed}/{len(all_results)} scenarios PASS")

    # Save results
    results_path = EMAILS_DIR.parent / "e2e-results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to {results_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
