"""Direct PostgreSQL bulk loader for product fixture — bypasses Odoo for speed.

Volume is configurable via SCALE_TEST_PRODUCT_COUNT env var (default: 2000).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, insert, select

from quote_agent.models.product import Product

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000
_FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "catalog_50k.jsonl"


def _get_product_count() -> int:
    """Read target product count from env var, default 2000."""
    return int(os.environ.get("SCALE_TEST_PRODUCT_COUNT", "2000"))


def _load_jsonl(fixture_path: Path) -> list[dict[str, Any]]:
    """Load all records from a JSONL fixture file."""
    records: list[dict[str, Any]] = []
    with open(fixture_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


async def load_50k_fixture(
    session: AsyncSession,
    fixture_path: Path = _FIXTURE_PATH,
) -> int:
    """Bulk-load products directly into PostgreSQL.

    Volume controlled by SCALE_TEST_PRODUCT_COUNT env var (default: 2000).

    - Reads catalog_50k.jsonl (up to target count)
    - Checks if products are already loaded (idempotent via count check)
    - Batch-inserts 1000 products at a time via SQLAlchemy core insert
    - Returns total products inserted
    """
    start = time.perf_counter()
    target_count = _get_product_count()

    # Idempotency: skip if enough products are already loaded
    count_result = await session.execute(select(func.count()).select_from(Product).where(Product.is_stale.is_(False)))
    existing_count = count_result.scalar_one()
    if existing_count >= target_count:
        logger.info(
            "Skipping bulk load — %d products already present (target: %d)",
            existing_count,
            target_count,
        )
        return 0

    all_records = _load_jsonl(fixture_path)
    records = all_records[:target_count]
    total_records = len(records)
    logger.info("Loading %d products (target: %d, available: %d)", total_records, target_count, len(all_records))
    total_inserted = 0

    # Collect existing references to avoid duplicates
    existing_refs_result = await session.execute(select(Product.reference))
    existing_refs: set[str] = {row[0] for row in existing_refs_result}

    for i in range(0, total_records, _BATCH_SIZE):
        batch = records[i : i + _BATCH_SIZE]

        values = [
            {
                "reference": rec.get("reference", ""),
                "name": rec["name"],
                "description": rec.get("description"),
                "category": rec.get("category", "Uncategorized"),
                "unit_price": rec.get("unit_price", 0.0),
                "stock_status": rec.get("stock_status", "in_stock"),
                "is_active": rec.get("is_active", True),
                "metadata_": rec.get("metadata"),
            }
            for rec in batch
            if rec.get("reference", "") not in existing_refs
        ]

        if not values:
            continue

        stmt = insert(Product).values(values)
        await session.execute(stmt)
        total_inserted += len(values)

        # Track inserted references for subsequent batches
        for v in values:
            existing_refs.add(v["reference"])

        batch_num = i // _BATCH_SIZE + 1
        total_batches = (total_records + _BATCH_SIZE - 1) // _BATCH_SIZE
        logger.info(
            "Bulk load batch %d/%d — %d inserted so far",
            batch_num,
            total_batches,
            total_inserted,
        )

    await session.commit()

    duration = time.perf_counter() - start
    logger.info(
        "Bulk load complete: %d/%d products inserted in %.2fs",
        total_inserted,
        total_records,
        duration,
    )

    return total_inserted
