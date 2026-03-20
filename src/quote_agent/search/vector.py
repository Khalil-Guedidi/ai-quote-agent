"""Semantic search via pgvector cosine distance."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, text

from quote_agent.config import get_settings
from quote_agent.models.product import Product
from quote_agent.search.models import ScoredProduct
from quote_agent.search.proposability import is_product_proposable

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.elements import ColumnElement

    from quote_agent.config import ProposabilitySettings


async def search_semantic(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int,
    *,
    include_stale: bool = False,
    proposability_clauses: list[ColumnElement[bool]] | None = None,
    proposability_settings: ProposabilitySettings | None = None,
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

    if proposability_clauses:
        for clause in proposability_clauses:
            stmt = stmt.where(clause)

    result = await session.execute(stmt)
    rows = result.all()

    scored: list[ScoredProduct] = []
    for rank, (product, distance) in enumerate(rows, start=1):
        proposable = (
            is_product_proposable(product.is_active, product.stock_status, product.category, proposability_settings)
            if proposability_settings is not None
            else True
        )
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
                is_proposable=proposable,
            )
        )

    return scored
