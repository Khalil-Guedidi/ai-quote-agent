#!/usr/bin/env python3
"""
Story 0.5 — Test email extraction via OpenAI API.

Reads all email fixtures from prototype/data/emails/, sends each to GPT-4o
for structured extraction, and reports results with accuracy analysis.

Usage:
    python3 scripts/test-email-extraction.py                # Run all fixtures
    python3 scripts/test-email-extraction.py email_jargon   # Run single fixture

Requires: OPENAI_API_KEY environment variable (or in prototype/.env)
"""

import json
import os
import sys
import time
from pathlib import Path

# Load .env if python-dotenv available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

EMAILS_DIR = Path(__file__).parent.parent / "data" / "emails"

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

# Expected results for accuracy evaluation
EXPECTED = {
    "email_simple_ref.json": {
        "client_email": "sophie.martin@acme-metal.fr",
        "product_count": 1,
        "has_reference": True,
        "delivery_date_present": False,
    },
    "email_multi_products.json": {
        "client_email": "j.dupont@constructions-bernard.fr",
        "product_count": 4,
        "has_reference": False,
        "delivery_date_present": True,
    },
    "email_jargon.json": {
        "client_email": "p.lefevre@sideral-industrie.com",
        "product_count": 3,
        "has_reference": False,
        "delivery_date_present": False,
    },
    "email_previous_order.json": {
        "client_email": "m.garcia@ferrotec.fr",
        "product_count": 3,
        "has_reference": False,
        "delivery_date_present": False,
    },
    "email_vague.json": {
        "client_email": "contact@petit-atelier.fr",
        "product_count": 2,
        "has_reference": False,
        "delivery_date_present": False,
    },
}


def call_openai(email_text: str) -> dict:
    """Call OpenAI API for extraction."""
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


def evaluate(filename: str, extracted: dict) -> dict:
    """Compare extraction result against expected values."""
    expected = EXPECTED.get(filename, {})
    checks = {}

    # Check client_email
    if "client_email" in expected:
        checks["client_email_match"] = (
            extracted.get("client_email") == expected["client_email"]
        )

    # Check product count
    if "product_count" in expected:
        actual_count = len(extracted.get("products", []))
        checks["product_count_match"] = actual_count == expected["product_count"]
        checks["product_count_actual"] = actual_count
        checks["product_count_expected"] = expected["product_count"]

    # Check if reference was extracted when expected
    if "has_reference" in expected:
        products = extracted.get("products", [])
        has_ref = any(p.get("reference") for p in products)
        checks["reference_extracted"] = has_ref == expected["has_reference"]

    # Check delivery date presence
    if "delivery_date_present" in expected:
        has_date = extracted.get("delivery_date") is not None
        checks["delivery_date_match"] = has_date == expected["delivery_date_present"]

    checks["all_passed"] = all(
        v for k, v in checks.items()
        if k.endswith("_match") or k == "reference_extracted"
    )

    return checks


def main():
    filter_name = sys.argv[1] if len(sys.argv) > 1 else None

    fixture_files = sorted(EMAILS_DIR.glob("*.json"))
    if filter_name:
        fixture_files = [f for f in fixture_files if filter_name in f.stem]

    if not fixture_files:
        print(f"No fixtures found in {EMAILS_DIR}")
        sys.exit(1)

    print(f"{'='*70}")
    print(f"Story 0.5 — Email Extraction Test")
    print(f"Fixtures: {len(fixture_files)} | Model: GPT-4o | Temperature: 0")
    print(f"{'='*70}\n")

    all_results = []

    for fixture_path in fixture_files:
        with open(fixture_path) as f:
            email = json.load(f)

        email_text = (
            f"From: {email['from']}\n"
            f"Subject: {email['subject']}\n"
            f"Date: {email['date']}\n\n"
            f"{email['body']}"
        )

        print(f"--- {fixture_path.name} ---")
        print(f"  From: {email['from']}")
        print(f"  Subject: {email['subject']}")

        start = time.time()
        try:
            extracted = call_openai(email_text)
            elapsed = time.time() - start
        except Exception as e:
            print(f"  ERROR: {e}\n")
            all_results.append({
                "file": fixture_path.name,
                "status": "ERROR",
                "error": str(e),
            })
            continue

        print(f"  Latency: {elapsed:.1f}s")
        print(f"  Client: {extracted.get('client_name')} <{extracted.get('client_email')}>")
        print(f"  Products: {len(extracted.get('products', []))}")
        for i, p in enumerate(extracted.get("products", []), 1):
            ref_str = f" [ref: {p['reference']}]" if p.get("reference") else ""
            specs_str = f" ({p['specs']})" if p.get("specs") else ""
            print(f"    {i}. {p.get('description', '?')} — qty: {p.get('quantity', '?')}{ref_str}{specs_str}")
        if extracted.get("delivery_date"):
            print(f"  Delivery: {extracted['delivery_date']}")
        if extracted.get("notes"):
            print(f"  Notes: {extracted['notes']}")

        # Evaluate
        checks = evaluate(fixture_path.name, extracted)
        status = "PASS" if checks.get("all_passed", False) else "FAIL"
        print(f"  Evaluation: {status}")
        for k, v in checks.items():
            if k != "all_passed":
                print(f"    {k}: {v}")
        print()

        all_results.append({
            "file": fixture_path.name,
            "status": status,
            "latency_s": round(elapsed, 2),
            "extraction": extracted,
            "checks": checks,
        })

    # Summary
    print(f"{'='*70}")
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")
    errors = sum(1 for r in all_results if r["status"] == "ERROR")
    total = len(all_results)
    print(f"SUMMARY: {passed}/{total} passed, {failed} failed, {errors} errors")
    if total > 0 and errors < total:
        avg_latency = sum(r.get("latency_s", 0) for r in all_results if "latency_s" in r) / (total - errors)
        print(f"Average latency: {avg_latency:.1f}s")
    print(f"{'='*70}")

    # Save results
    results_path = EMAILS_DIR.parent / "extraction-results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
