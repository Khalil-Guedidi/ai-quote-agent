"""Semantic search via pgvector cosine distance."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, text

from quote_agent.config import get_settings
from quote_agent.models.product import Product
from quote_agent.search.models import ScoredProduct

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def search_semantic(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int,
    *,
    include_stale: bool = False,
) -> list[ScoredProduct]:
    """Run pgvector cosine distance search, return results ranked by similarity."""
    settings = get_settings().search

    # Set higher ef_search for better recall (cannot use bind params for SET)
    ef_search = int(settings.hnsw_ef_search)
    await session.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))

    distance_expr = Product.vector.cosine_distance(query_embedding)

    stmt = (
        select(Product, distance_expr.label("distance"))
        .where(Product.vector.isnot(None))
        .order_by(distance_expr)
        .limit(limit)
    )

    if not include_stale:
        stmt = stmt.where(Product.is_stale.is_(False))

    result = await session.execute(stmt)
    rows = result.all()

    scored: list[ScoredProduct] = []
    for rank, (product, distance) in enumerate(rows, start=1):
        scored.append(
            ScoredProduct(
                product_id=product.id,
                reference=product.reference,
                name=product.name,
                category=product.category,
                description=product.description,
                unit_price=product.unit_price,
                score=1.0 - float(distance),
                rank=rank,
                match_source="semantic",
            )
        )

    return scored
