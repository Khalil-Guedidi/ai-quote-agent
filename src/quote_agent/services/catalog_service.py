"""Catalog ingestion service — orchestrates ERP → PostgreSQL product sync."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from quote_agent.adapters.erp.models import IngestionResult, ProductFilter
from quote_agent.adapters.erp.models import Product as ProductDTO
from quote_agent.models.product import Product as ProductModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.erp.protocol import ERPAdapter

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500
_WRITE_BATCH_SIZE = 50


def _product_hash(dto: ProductDTO) -> str:
    """Compute a deterministic hash of key product fields for change detection."""
    data = {
        "odoo_id": dto.odoo_id,
        "reference": dto.reference,
        "name": dto.name,
        "description": dto.description,
        "category": dto.category,
        "unit_price": dto.unit_price,
        "stock_status": dto.stock_status,
        "is_active": dto.is_active,
        "metadata": dto.metadata,
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


class CatalogService:
    """Orchestrates catalog ingestion from ERP to PostgreSQL."""

    def __init__(self, erp_adapter: ERPAdapter, session: AsyncSession) -> None:
        self._erp = erp_adapter
        self._session = session

    async def ingest_full(self) -> IngestionResult:
        """Run a full catalog ingestion: paginated fetch → upsert → stale detection."""
        start = time.monotonic()
        inserted = 0
        updated = 0
        unchanged = 0
        fetched_odoo_ids: set[int] = set()

        offset = 0
        batch_num = 0

        while True:
            filters = ProductFilter(active_only=False, limit=_BATCH_SIZE, offset=offset)
            batch = await self._erp.get_products(filters)
            batch_num += 1

            if not batch:
                break

            result = await self._upsert_batch(batch, fetched_odoo_ids)
            inserted += result["inserted"]
            updated += result["updated"]
            unchanged += result["unchanged"]

            logger.info(
                "Catalog batch ingested",
                extra={
                    "context": {
                        "component": "services.catalog_service",
                        "batch": batch_num,
                        "count": len(batch),
                        "total": inserted + updated + unchanged,
                    }
                },
            )

            if len(batch) < _BATCH_SIZE:
                break

            offset += _BATCH_SIZE

        # Stale detection
        stale = await self._mark_stale(fetched_odoo_ids)

        duration = time.monotonic() - start

        logger.info(
            "Catalog ingestion complete",
            extra={
                "context": {
                    "component": "services.catalog_service",
                    "inserted": inserted,
                    "updated": updated,
                    "unchanged": unchanged,
                    "stale": stale,
                    "duration_seconds": round(duration, 2),
                }
            },
        )

        return IngestionResult(
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            stale=stale,
            duration_seconds=round(duration, 2),
        )

    async def _upsert_batch(
        self,
        batch: list[ProductDTO],
        fetched_odoo_ids: set[int],
    ) -> dict[str, int]:
        """Upsert a batch of products keyed on odoo_id. Returns counts."""
        inserted = 0
        updated = 0
        unchanged = 0

        # Collect odoo_ids from this batch
        batch_odoo_ids = [dto.odoo_id for dto in batch if dto.odoo_id is not None]
        fetched_odoo_ids.update(batch_odoo_ids)

        # Load existing products by odoo_id
        existing_map: dict[int, ProductModel] = {}
        if batch_odoo_ids:
            stmt = select(ProductModel).where(ProductModel.odoo_id.in_(batch_odoo_ids))
            result = await self._session.execute(stmt)
            for row in result.scalars():
                if row.odoo_id is not None:
                    existing_map[row.odoo_id] = row

        for dto in batch:
            if dto.odoo_id is None:
                continue

            new_hash = _product_hash(dto)
            existing = existing_map.get(dto.odoo_id)

            if existing is None:
                # INSERT new product
                model = ProductModel(
                    odoo_id=dto.odoo_id,
                    reference=dto.reference,
                    name=dto.name,
                    description=dto.description,
                    category=dto.category,
                    unit_price=dto.unit_price,
                    stock_status=dto.stock_status,
                    is_active=dto.is_active,
                    metadata_=dto.metadata or None,
                    is_stale=False,
                )
                self._session.add(model)
                inserted += 1
            else:
                # Check if changed
                existing_hash = _product_hash(ProductDTO(
                    odoo_id=existing.odoo_id,
                    reference=existing.reference,
                    name=existing.name,
                    description=existing.description,
                    category=existing.category,
                    unit_price=existing.unit_price,
                    stock_status=existing.stock_status,
                    is_active=existing.is_active,
                    metadata=existing.metadata_ or {},
                ))
                if new_hash != existing_hash:
                    existing.reference = dto.reference
                    existing.name = dto.name
                    existing.description = dto.description
                    existing.category = dto.category
                    existing.unit_price = dto.unit_price
                    existing.stock_status = dto.stock_status
                    existing.is_active = dto.is_active
                    existing.metadata_ = dto.metadata or None
                    existing.is_stale = False
                    updated += 1
                else:
                    # Un-stale if it was marked stale previously
                    if existing.is_stale:
                        existing.is_stale = False
                    unchanged += 1

        await self._session.flush()

        return {"inserted": inserted, "updated": updated, "unchanged": unchanged}

    async def _mark_stale(self, fetched_odoo_ids: set[int]) -> int:
        """Mark products not in fetched_odoo_ids as stale. Returns count."""
        if not fetched_odoo_ids:
            return 0

        stmt = (
            update(ProductModel)
            .where(
                ProductModel.odoo_id.isnot(None),
                ProductModel.odoo_id.notin_(fetched_odoo_ids),
                ProductModel.is_stale.is_(False),
            )
            .values(is_stale=True)
        )
        cursor_result = await self._session.execute(stmt)
        await self._session.commit()
        return int(cursor_result.rowcount)  # type: ignore[attr-defined]
