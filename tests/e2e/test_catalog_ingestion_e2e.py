"""E2E tests for catalog ingestion with real Odoo + PostgreSQL (Story 3.1, AC-4)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import xmlrpc.client
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import delete, func, select

from quote_agent.models.product import Product as ProductModel
from quote_agent.services.catalog_service import CatalogService
from tests.e2e.conftest import requires_e2e_erp

logger = logging.getLogger(__name__)

_E2E_PRODUCT_PREFIX = "[E2E-TEST]"
_SEED_BATCH_SIZE = 50
_SEED_COUNT = 500

# ---------------------------------------------------------------------------
# Odoo XML-RPC helpers for seeding and cleanup
# ---------------------------------------------------------------------------


def _get_odoo_connection() -> tuple[xmlrpc.client.ServerProxy, int, str, str]:
    """Return (object_proxy, uid, db, api_key) for Odoo XML-RPC."""
    url = os.environ["ERP__URL"]
    db = os.environ["ERP__DATABASE"]
    username = os.environ["ERP__USERNAME"]
    api_key = os.environ["ERP__API_KEY"]

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    uid = common.authenticate(db, username, api_key, {})
    if not uid:
        msg = "Odoo authentication failed for E2E seeding"
        raise RuntimeError(msg)

    obj = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    return obj, uid, db, api_key


def _load_seed_records(count: int = _SEED_COUNT) -> list[dict[str, Any]]:
    """Load first `count` records from catalog_50k.jsonl."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    full_path = fixtures_dir / "catalog_50k.jsonl"
    sample_path = fixtures_dir / "catalog_50k_sample.jsonl"

    # Use full catalog to get enough records; fall back to sample for smaller counts
    path = full_path if full_path.exists() else sample_path
    records: list[dict[str, Any]] = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            records.append(json.loads(line))
    return records


def _seed_products_to_odoo(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
    records: list[dict[str, Any]],
) -> list[int]:
    """Create products in Odoo, return list of created odoo IDs."""
    created_ids: list[int] = []

    # Get or create a test category
    category_ids: dict[str, int] = {}

    for i in range(0, len(records), _SEED_BATCH_SIZE):
        batch = records[i : i + _SEED_BATCH_SIZE]
        vals_list = []
        for rec in batch:
            # Ensure category exists
            cat_name = rec.get("category", "Uncategorized")
            if cat_name not in category_ids:
                existing = obj.execute_kw(
                    db, uid, api_key,
                    "product.category", "search",
                    [[("name", "=", cat_name)]],
                    {"limit": 1},
                )
                if existing:
                    category_ids[cat_name] = existing[0]
                else:
                    category_ids[cat_name] = obj.execute_kw(
                        db, uid, api_key,
                        "product.category", "create",
                        [{"name": cat_name}],
                    )

            # Odoo uses False instead of None for empty fields
            description = rec.get("description") or False

            vals = {
                "name": f"{_E2E_PRODUCT_PREFIX} {rec['name']}",
                "default_code": rec.get("reference", ""),
                "description_sale": description,
                "categ_id": category_ids[cat_name],
                "list_price": rec.get("unit_price", 0.0),
                "active": rec.get("is_active", True),
                "barcode": False,  # Avoid uniqueness conflicts
                "sale_ok": True,
                "type": "consu",
            }
            # Handle weight from metadata
            metadata = rec.get("metadata", {})
            if "weight_kg" in metadata:
                vals["weight"] = metadata["weight_kg"]

            vals_list.append(vals)

        # Batch create
        ids = obj.execute_kw(
            db, uid, api_key,
            "product.product", "create",
            [vals_list],
        )
        if isinstance(ids, int):
            ids = [ids]
        created_ids.extend(ids)
        logger.info("Seeded batch %d/%d (%d products)", i // _SEED_BATCH_SIZE + 1,
                     (len(records) + _SEED_BATCH_SIZE - 1) // _SEED_BATCH_SIZE, len(ids))

    return created_ids


def _cleanup_odoo_products(
    obj: xmlrpc.client.ServerProxy,
    uid: int,
    db: str,
    api_key: str,
) -> int:
    """Delete all E2E test products from Odoo. Returns count deleted."""
    # Search for products with the E2E prefix (including archived)
    ids = obj.execute_kw(
        db, uid, api_key,
        "product.product", "search",
        [[("name", "like", _E2E_PRODUCT_PREFIX)]],
        {"context": {"active_test": False}},
    )
    if ids:
        obj.execute_kw(
            db, uid, api_key,
            "product.product", "unlink",
            [ids],
        )
    return len(ids)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def seeded_odoo_products(e2e_db_session):
    """Seed products into Odoo, yield (odoo_ids, record_count), cleanup after."""
    records = _load_seed_records(_SEED_COUNT)
    assert len(records) >= _SEED_COUNT, f"Need at least {_SEED_COUNT} fixture records"

    obj, uid, db, api_key = await asyncio.to_thread(_get_odoo_connection)
    created_ids = await asyncio.to_thread(_seed_products_to_odoo, obj, uid, db, api_key, records)

    yield created_ids, len(records)

    # Cleanup Odoo
    await asyncio.to_thread(_cleanup_odoo_products, obj, uid, db, api_key)

    # Cleanup PostgreSQL — delete products with E2E prefix in name
    await e2e_db_session.execute(
        delete(ProductModel).where(ProductModel.name.like(f"%{_E2E_PRODUCT_PREFIX}%"))
    )
    await e2e_db_session.commit()


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


@requires_e2e_erp
@pytest.mark.e2e
class TestCatalogIngestionE2E:
    """E2E tests for catalog ingestion through real Odoo → PostgreSQL."""

    async def test_ingestion_stores_products_e2e(
        self,
        e2e_db_session,
        e2e_erp_adapter,
        seeded_odoo_products,
    ) -> None:
        """AC-4: Ingestion through real ERPAdapter.get_products() produces correct records in PostgreSQL."""
        _created_ids, record_count = seeded_odoo_products

        service = CatalogService(e2e_erp_adapter, e2e_db_session)
        result = await service.ingest_full()

        # Verify products landed in PostgreSQL
        count_result = await e2e_db_session.execute(
            select(func.count()).select_from(ProductModel).where(
                ProductModel.name.like(f"%{_E2E_PRODUCT_PREFIX}%")
            )
        )
        db_count = count_result.scalar_one()

        # At least our seeded products should be there (there may be others from Odoo)
        assert db_count >= record_count, (
            f"Expected at least {record_count} E2E products in DB, got {db_count}"
        )
        assert result.inserted > 0

    async def test_resync_produces_correct_counts_e2e(
        self,
        e2e_db_session,
        e2e_erp_adapter,
        seeded_odoo_products,
    ) -> None:
        """AC-3: Second ingestion run produces 0 inserted, 0 updated, N unchanged."""
        service = CatalogService(e2e_erp_adapter, e2e_db_session)

        # First run
        result1 = await service.ingest_full()
        assert result1.inserted > 0

        # Second run — same data, should all be unchanged
        result2 = await service.ingest_full()
        assert result2.inserted == 0
        assert result2.updated == 0
        assert result2.unchanged > 0

    async def test_resync_detects_update_e2e(
        self,
        e2e_db_session,
        e2e_erp_adapter,
        seeded_odoo_products,
    ) -> None:
        """AC-3: Modified product in Odoo detected as updated on re-sync."""
        created_ids, _ = seeded_odoo_products
        service = CatalogService(e2e_erp_adapter, e2e_db_session)

        # First ingestion
        await service.ingest_full()

        # Modify one product in Odoo
        obj, uid, db, api_key = await asyncio.to_thread(_get_odoo_connection)
        target_id = created_ids[0]
        await asyncio.to_thread(
            obj.execute_kw,
            db, uid, api_key,
            "product.product", "write",
            [[target_id], {"list_price": 999.99}],
        )

        # Re-ingest
        result2 = await service.ingest_full()
        assert result2.updated >= 1, f"Expected at least 1 update, got {result2.updated}"
