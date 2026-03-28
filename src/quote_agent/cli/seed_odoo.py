"""CLI seed-odoo command — populate test Odoo with realistic industrial data."""

from __future__ import annotations

import asyncio
import json
import logging
import xmlrpc.client
from pathlib import Path
from typing import Any

import typer

logger = logging.getLogger(__name__)

_SEED_PREFIX = "[SEED]"
_SEED_ORDER_PREFIX = "SEED-"
_DEFAULT_PRODUCT_COUNT = 200
_BATCH_SIZE = 50

# ---------------------------------------------------------------------------
# 5 realistic French industrial client profiles (AC #2)
# ---------------------------------------------------------------------------

_CLIENT_PROFILES: list[dict[str, Any]] = [
    {
        "name": f"{_SEED_PREFIX} ArcelorMittal France",
        "ref": "ARCELORMITTAL",
        "email": "commandes@arcelormittal.fr",
        "phone": "+33 1 41 25 00 00",
        "street": "1 Boulevard d'Arcelor",
        "city": "Dunkerque",
        "zip": "59760",
        "country_code": "FR",
        "vat": False,
        "customer_rank": 2,
    },
    {
        "name": f"{_SEED_PREFIX} Descours & Cabaud",
        "ref": "DESCOURS",
        "email": "achats@descours-cabaud.com",
        "phone": "+33 4 72 14 27 00",
        "street": "110 Avenue du 8 Mai 1945",
        "city": "Lyon",
        "zip": "69100",
        "country_code": "FR",
        "vat": False,
        "customer_rank": 1,
    },
    {
        "name": f"{_SEED_PREFIX} Atelier Martin SARL",
        "ref": "MARTIN",
        "email": "contact@atelier-martin.fr",
        "phone": "+33 3 88 12 34 56",
        "street": "22 Rue des Forgerons",
        "city": "Strasbourg",
        "zip": "67000",
        "country_code": "FR",
        "vat": False,
        "customer_rank": 1,
    },
    {
        "name": f"{_SEED_PREFIX} Konecranes Finland Oy",
        "ref": "KONECRANES",
        "email": "orders@konecranes.fi",
        "phone": "+358 20 427 11",
        "street": "Koneenkatu 8",
        "city": "Hyvinkää",
        "zip": "05830",
        "country_code": "FI",
        "vat": False,
        "customer_rank": 1,
    },
    {
        "name": f"{_SEED_PREFIX} NouveauClient SAS",
        "ref": "NOUVEAUCLIENT",
        "email": "info@nouveauclient.fr",
        "phone": "+33 1 23 45 67 89",
        "street": "5 Avenue de la République",
        "city": "Nantes",
        "zip": "44000",
        "country_code": "FR",
        "vat": False,
        "customer_rank": 1,
    },
]

# ---------------------------------------------------------------------------
# Order history templates (AC #3)
# ---------------------------------------------------------------------------

# Each entry: (client_ref, list of orders)
# Each order: (client_order_ref, list of (product_index, qty, price_unit))
_ORDER_TEMPLATES: list[tuple[str, list[tuple[str, list[tuple[int, int, float]]]]]] = [
    (
        "ARCELORMITTAL",
        [
            ("SEED-ARCELORMITTAL-001", [(0, 500, 153.60), (1, 200, 408.40)]),
            ("SEED-ARCELORMITTAL-002", [(2, 1000, 28.23)]),
            ("SEED-ARCELORMITTAL-003", [(3, 300, 35.04), (4, 150, 219.26)]),
            ("SEED-ARCELORMITTAL-004", [(0, 800, 153.60), (1, 100, 408.40), (3, 250, 35.04)]),
            ("SEED-ARCELORMITTAL-005", [(4, 600, 219.26)]),
        ],
    ),
    (
        "DESCOURS",
        [
            ("SEED-DESCOURS-001", [(0, 50, 153.60), (2, 100, 28.23)]),
            ("SEED-DESCOURS-002", [(1, 30, 408.40)]),
            ("SEED-DESCOURS-003", [(3, 80, 35.04), (4, 20, 219.26)]),
        ],
    ),
    (
        "MARTIN",
        [
            ("SEED-MARTIN-001", [(2, 10, 28.23), (3, 5, 35.04)]),
            ("SEED-MARTIN-002", [(0, 15, 153.60)]),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Odoo XML-RPC connection (adapted from E2E test pattern)
# ---------------------------------------------------------------------------


def _get_odoo_connection() -> tuple[xmlrpc.client.ServerProxy, int, str, str]:
    """Return (object_proxy, uid, db, api_key) for Odoo XML-RPC."""
    from quote_agent.config import get_settings

    erp = get_settings().erp
    url = erp.url
    db = erp.database
    username = erp.username
    api_key = erp.api_key.get_secret_value()

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    uid_raw: Any = common.authenticate(db, username, api_key, {})
    if not uid_raw:
        msg = "Odoo authentication failed"
        raise RuntimeError(msg)
    uid = int(str(uid_raw))

    obj = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    return obj, uid, db, api_key


def _exec(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
    model: str,
    method: str,
    args: list[Any],
    kwargs: dict[str, Any] | None = None,
) -> Any:
    """Shortcut for execute_kw."""
    return obj.execute_kw(db, uid, api_key, model, method, args, kwargs or {})


# ---------------------------------------------------------------------------
# Product seeding (Task 2)
# ---------------------------------------------------------------------------


def _load_seed_records(count: int) -> list[dict[str, Any]]:
    """Load first `count` records from catalog_50k.jsonl."""
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"
    full_path = fixtures_dir / "catalog_50k.jsonl"
    sample_path = fixtures_dir / "catalog_50k_sample.jsonl"

    path = full_path if full_path.exists() else sample_path
    if not path.exists():
        msg = f"Fixture file not found: {full_path} or {sample_path}"
        raise FileNotFoundError(msg)

    records: list[dict[str, Any]] = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            records.append(json.loads(line))
    return records


def _seed_products(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
    records: list[dict[str, Any]],
) -> list[int]:
    """Seed products to Odoo. Returns list of created IDs. Idempotent: skips existing."""
    created_ids: list[int] = []
    skipped = 0
    category_ids: dict[str, int] = {}
    total_batches = (len(records) + _BATCH_SIZE - 1) // _BATCH_SIZE

    for i in range(0, len(records), _BATCH_SIZE):
        batch = records[i : i + _BATCH_SIZE]
        vals_list = []

        for rec in batch:
            ref = rec.get("reference", "")

            # Idempotency: skip if product with this default_code exists (include archived)
            existing = _exec(
                obj,
                uid,
                db,
                api_key,
                "product.product",
                "search",
                [[("default_code", "=", ref)]],
                {"limit": 1, "context": {"active_test": False}},
            )
            if existing:
                skipped += 1
                continue

            # Ensure category exists
            cat_name = rec.get("category", "Uncategorized")
            if cat_name not in category_ids:
                existing_cat = _exec(
                    obj,
                    uid,
                    db,
                    api_key,
                    "product.category",
                    "search",
                    [[("name", "=", cat_name)]],
                    {"limit": 1},
                )
                if existing_cat:
                    category_ids[cat_name] = existing_cat[0]
                else:
                    category_ids[cat_name] = _exec(
                        obj,
                        uid,
                        db,
                        api_key,
                        "product.category",
                        "create",
                        [{"name": cat_name}],
                    )

            description = rec.get("description") or False
            metadata = rec.get("metadata", {})

            vals: dict[str, Any] = {
                "name": f"{_SEED_PREFIX} {rec['name']}",
                "default_code": ref,
                "description_sale": description,
                "categ_id": category_ids[cat_name],
                "list_price": rec.get("unit_price", 0.0),
                "active": rec.get("is_active", True),
                "barcode": False,
                "sale_ok": True,
                "type": "consu",
            }
            if "weight_kg" in metadata:
                vals["weight"] = metadata["weight_kg"]

            vals_list.append(vals)

        if vals_list:
            ids = _exec(
                obj,
                uid,
                db,
                api_key,
                "product.product",
                "create",
                [vals_list],
            )
            if isinstance(ids, int):
                ids = [ids]
            created_ids.extend(ids)

        batch_num = i // _BATCH_SIZE + 1
        logger.info(
            "Products batch %d/%d — %d created, %d skipped so far",
            batch_num,
            total_batches,
            len(created_ids),
            skipped,
        )

    return created_ids


# ---------------------------------------------------------------------------
# Client seeding (Task 3)
# ---------------------------------------------------------------------------


def _resolve_country_id(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
    country_code: str,
) -> int:
    """Resolve country code to Odoo res.country ID."""
    ids = _exec(
        obj,
        uid,
        db,
        api_key,
        "res.country",
        "search",
        [[("code", "=", country_code)]],
        {"limit": 1},
    )
    if not ids:
        msg = f"Country not found in Odoo: {country_code}"
        raise ValueError(msg)
    result: int = ids[0]
    return result


def _seed_clients(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
) -> dict[str, int]:
    """Seed client profiles to Odoo. Returns {ref: partner_id}. Idempotent."""
    result: dict[str, int] = {}
    country_cache: dict[str, int] = {}

    for profile in _CLIENT_PROFILES:
        ref = profile["ref"]

        # Idempotency: skip if partner with this ref exists
        existing = _exec(
            obj,
            uid,
            db,
            api_key,
            "res.partner",
            "search",
            [[("ref", "=", ref)]],
            {"limit": 1},
        )
        if existing:
            result[ref] = existing[0]
            logger.info("Client %s already exists (ID=%d), skipping", ref, existing[0])
            continue

        # Resolve country
        cc = profile["country_code"]
        if cc not in country_cache:
            country_cache[cc] = _resolve_country_id(obj, uid, db, api_key, cc)

        vals: dict[str, Any] = {
            "name": profile["name"],
            "ref": ref,
            "email": profile["email"],
            "phone": profile["phone"],
            "street": profile["street"],
            "city": profile["city"],
            "zip": profile["zip"],
            "country_id": country_cache[cc],
            "vat": profile["vat"],
            "customer_rank": profile["customer_rank"],
            "is_company": True,
        }
        partner_id: int = _exec(
            obj,
            uid,
            db,
            api_key,
            "res.partner",
            "create",
            [vals],
        )
        result[ref] = partner_id
        logger.info("Created client %s (ID=%d)", ref, partner_id)

    return result


# ---------------------------------------------------------------------------
# Order history seeding (Task 4)
# ---------------------------------------------------------------------------


def _seed_orders(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
    client_map: dict[str, int],
    product_ids: list[int],
) -> list[int]:
    """Seed order history for clients. Idempotent via client_order_ref."""
    created_order_ids: list[int] = []

    for client_ref, orders in _ORDER_TEMPLATES:
        partner_id = client_map.get(client_ref)
        if not partner_id:
            logger.warning("Client %s not found in client_map, skipping orders", client_ref)
            continue

        for order_ref, lines in orders:
            # Idempotency: check if order with this client_order_ref exists
            existing = _exec(
                obj,
                uid,
                db,
                api_key,
                "sale.order",
                "search",
                [[("client_order_ref", "=", order_ref)]],
                {"limit": 1},
            )
            if existing:
                created_order_ids.append(existing[0])
                logger.info("Order %s already exists (ID=%d), skipping", order_ref, existing[0])
                continue

            # Build order lines
            order_lines: list[tuple[int, int, dict[str, Any]]] = []
            for product_idx, qty, price in lines:
                if product_idx < len(product_ids):
                    pid = product_ids[product_idx]
                else:
                    logger.warning("Product index %d out of range, skipping line", product_idx)
                    continue
                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": pid,
                            "product_uom_qty": qty,
                            "price_unit": price,
                        },
                    )
                )

            if not order_lines:
                continue

            order_id: int = _exec(
                obj,
                uid,
                db,
                api_key,
                "sale.order",
                "create",
                [
                    {
                        "partner_id": partner_id,
                        "client_order_ref": order_ref,
                        "order_line": order_lines,
                    }
                ],
            )

            # Confirm order (draft → sale)
            _exec(
                obj,
                uid,
                db,
                api_key,
                "sale.order",
                "action_confirm",
                [[order_id]],
            )

            created_order_ids.append(order_id)
            logger.info("Created and confirmed order %s (ID=%d) for %s", order_ref, order_id, client_ref)

    return created_order_ids


# ---------------------------------------------------------------------------
# Cleanup logic (Task 5)
# ---------------------------------------------------------------------------


def _clean_seed_data(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
) -> dict[str, int]:
    """Remove all seeded data from Odoo. FK-safe order: lines → orders → products → partners."""
    counts: dict[str, int] = {}
    ctx = {"context": {"active_test": False}}

    # 1. Delete sale.order.line on seed orders
    seed_order_ids = _exec(
        obj,
        uid,
        db,
        api_key,
        "sale.order",
        "search",
        [[("client_order_ref", "like", _SEED_ORDER_PREFIX)]],
        ctx,
    )
    if seed_order_ids:
        # Cancel → draft → unlink (each singleton, Odoo requires it)
        for oid in seed_order_ids:
            order_data = _exec(
                obj,
                uid,
                db,
                api_key,
                "sale.order",
                "read",
                [oid],
                {"fields": ["state"]},
            )
            state = order_data[0]["state"] if order_data else "unknown"
            if state in ("sale", "done"):
                _exec(obj, uid, db, api_key, "sale.order", "action_cancel", [[oid]])
            # Reset to draft so it can be deleted
            _exec(obj, uid, db, api_key, "sale.order", "write", [[oid], {"state": "draft"}])

        # Count lines before deletion
        line_ids = _exec(
            obj,
            uid,
            db,
            api_key,
            "sale.order.line",
            "search",
            [[("order_id", "in", seed_order_ids)]],
            ctx,
        )
        counts["sale.order.line"] = len(line_ids) if line_ids else 0

        # 2. Delete sale.order (cascade deletes lines in draft state)
        _exec(obj, uid, db, api_key, "sale.order", "unlink", [seed_order_ids])
        counts["sale.order"] = len(seed_order_ids)
    else:
        counts["sale.order.line"] = 0
        counts["sale.order"] = 0

    # 3. Delete products with [SEED] prefix
    product_ids = _exec(
        obj,
        uid,
        db,
        api_key,
        "product.product",
        "search",
        [[("name", "like", _SEED_PREFIX)]],
        ctx,
    )
    if product_ids:
        _exec(obj, uid, db, api_key, "product.product", "unlink", [product_ids])
    counts["product.product"] = len(product_ids) if product_ids else 0

    # 4. Delete partners with [SEED] prefix
    partner_ids = _exec(
        obj,
        uid,
        db,
        api_key,
        "res.partner",
        "search",
        [[("name", "like", _SEED_PREFIX)]],
        ctx,
    )
    if partner_ids:
        _exec(obj, uid, db, api_key, "res.partner", "unlink", [partner_ids])
    counts["res.partner"] = len(partner_ids) if partner_ids else 0

    return counts


# ---------------------------------------------------------------------------
# Async wrapper + CLI command
# ---------------------------------------------------------------------------


async def _seed_impl(count: int, clean: bool) -> None:
    """Async implementation of seed-odoo command."""
    if clean:
        typer.echo(typer.style("Cleaning seed data from Odoo...", bold=True))
        obj, uid, db, api_key = await asyncio.to_thread(_get_odoo_connection)
        counts = await asyncio.to_thread(_clean_seed_data, obj, uid, db, api_key)
        for model, n in counts.items():
            typer.echo(f"  Deleted {n} {model} records")
        typer.echo(typer.style("Cleanup complete.", fg=typer.colors.GREEN))
        return

    typer.echo(typer.style(f"Seeding Odoo with {count} products + 5 clients + orders...", bold=True))

    obj, uid, db, api_key = await asyncio.to_thread(_get_odoo_connection)

    # 1. Seed products
    typer.echo("\n--- Products ---")
    records = _load_seed_records(count)
    product_ids = await asyncio.to_thread(_seed_products, obj, uid, db, api_key, records)
    typer.echo(f"  Products created: {len(product_ids)}")

    # If no new products were created, we still need product IDs for orders
    # Fetch existing seed product IDs
    if not product_ids:
        product_ids = await asyncio.to_thread(
            _exec,
            obj,
            uid,
            db,
            api_key,
            "product.product",
            "search",
            [[("name", "like", _SEED_PREFIX)]],
            {"limit": count},
        )
        typer.echo(f"  Using {len(product_ids)} existing seed products for orders")

    # 2. Seed clients
    typer.echo("\n--- Clients ---")
    client_map = await asyncio.to_thread(_seed_clients, obj, uid, db, api_key)
    typer.echo(f"  Clients: {len(client_map)} ({', '.join(client_map.keys())})")

    # 3. Seed orders
    typer.echo("\n--- Orders ---")
    order_ids = await asyncio.to_thread(_seed_orders, obj, uid, db, api_key, client_map, product_ids)
    typer.echo(f"  Orders created/found: {len(order_ids)}")

    typer.echo(typer.style("\nSeeding complete!", fg=typer.colors.GREEN))


async def seed_odoo(
    count: int = _DEFAULT_PRODUCT_COUNT,
    clean: bool = False,
) -> None:
    """Populate test Odoo with realistic industrial data (products, clients, orders)."""
    await _seed_impl(count=count, clean=clean)
