"""Embedding service — orchestrates batch embedding generation for products."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update

from quote_agent.adapters.embedding.models import EmbeddingResult
from quote_agent.models.product import Product

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.embedding.protocol import EmbeddingAdapter

logger = logging.getLogger(__name__)

_FETCH_BATCH_SIZE = 500
_WRITE_BATCH_SIZE = 50


def _build_product_text(product: Product) -> str:
    """Build text representation of a product for embedding."""
    parts = [product.name]
    if product.reference:
        parts.append(f"Ref: {product.reference}")
    parts.append(product.category)
    if product.description:
        parts.append(product.description)
    return " | ".join(parts)


class EmbeddingService:
    """Orchestrates embedding generation for catalog products."""

    def __init__(self, adapter: EmbeddingAdapter, session: AsyncSession) -> None:
        self._adapter = adapter
        self._session = session

    async def embed_all(self) -> EmbeddingResult:
        """Embed all products with NULL vector and is_stale=False."""
        start = time.monotonic()
        total_embedded = 0
        total_skipped_stale = 0
        total_errors = 0
        batch_num = 0

        # Count stale products that will be skipped (DB-side count, no ORM loading)
        stale_stmt = select(func.count()).select_from(Product).where(
            Product.is_stale.is_(True), Product.vector.is_(None)
        )
        stale_result = await self._session.execute(stale_stmt)
        total_skipped_stale = stale_result.scalar_one()

        if total_skipped_stale > 0:
            logger.info(
                "Skipping stale products",
                extra={"context": {"component": "services.embedding_service", "skipped_stale": total_skipped_stale}},
            )

        offset = 0

        while True:
            # Fetch products needing embeddings (not stale, no vector)
            stmt = (
                select(Product)
                .where(Product.vector.is_(None), Product.is_stale.is_(False))
                .order_by(Product.created_at)
                .limit(_FETCH_BATCH_SIZE)
                .offset(offset)
            )
            result = await self._session.execute(stmt)
            products = result.scalars().all()

            if not products:
                break

            batch_num += 1

            # Build texts and embed
            texts = [_build_product_text(p) for p in products]

            try:
                vectors = await self._adapter.embed_texts(texts)
            except Exception:
                logger.exception(
                    "Embedding batch failed",
                    extra={"context": {"component": "services.embedding_service", "batch": batch_num}},
                )
                total_errors += len(products)
                offset += _FETCH_BATCH_SIZE
                continue

            # Update products with vectors in write batches
            for i, (product, vector) in enumerate(zip(products, vectors, strict=True)):
                product.vector = vector
                if (i + 1) % _WRITE_BATCH_SIZE == 0:
                    await self._session.flush()

            await self._session.flush()
            total_embedded += len(vectors)

            logger.info(
                "Embedding batch generated",
                extra={
                    "context": {
                        "component": "services.embedding_service",
                        "batch": batch_num,
                        "count": len(vectors),
                        "total": total_embedded,
                    }
                },
            )

            if len(products) < _FETCH_BATCH_SIZE:
                break

            # Don't increment offset — processed products now have vectors, so
            # the next query (vector IS NULL) will naturally skip them.

        await self._session.commit()

        duration = time.monotonic() - start

        logger.info(
            "Embedding generation complete",
            extra={
                "context": {
                    "component": "services.embedding_service",
                    "embedded": total_embedded,
                    "skipped_stale": total_skipped_stale,
                    "errors": total_errors,
                    "duration_seconds": round(duration, 2),
                }
            },
        )

        return EmbeddingResult(
            embedded=total_embedded,
            skipped_stale=total_skipped_stale,
            errors=total_errors,
            duration_seconds=round(duration, 2),
        )

    async def embed_batch(self, product_ids: list[object]) -> EmbeddingResult:
        """Embed a specific list of products by ID."""
        start = time.monotonic()
        total_embedded = 0
        total_errors = 0

        stmt = select(Product).where(Product.id.in_(product_ids), Product.is_stale.is_(False))
        result = await self._session.execute(stmt)
        products = result.scalars().all()

        if not products:
            return EmbeddingResult(embedded=0, skipped_stale=0, errors=0, duration_seconds=0.0)

        texts = [_build_product_text(p) for p in products]

        try:
            vectors = await self._adapter.embed_texts(texts)
            for product, vector in zip(products, vectors, strict=True):
                product.vector = vector
            await self._session.flush()
            await self._session.commit()
            total_embedded = len(vectors)
        except Exception:
            logger.exception(
                "Embedding batch failed",
                extra={"context": {"component": "services.embedding_service"}},
            )
            total_errors = len(products)

        duration = time.monotonic() - start
        return EmbeddingResult(
            embedded=total_embedded,
            skipped_stale=0,
            errors=total_errors,
            duration_seconds=round(duration, 2),
        )

    async def reset_embeddings(self) -> int:
        """Set all product vectors to NULL for re-embedding after model change."""
        stmt = update(Product).where(Product.vector.isnot(None)).values(vector=None)
        cursor_result = await self._session.execute(stmt)
        await self._session.commit()

        count = int(cursor_result.rowcount)  # type: ignore[attr-defined]
        logger.info(
            "Embeddings reset",
            extra={"context": {"component": "services.embedding_service", "reset_count": count}},
        )
        return count
