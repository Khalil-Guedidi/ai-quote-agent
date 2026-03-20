"""Keyword search via PostgreSQL tsvector full-text search + exact reference matching."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from quote_agent.models.product import Product
from quote_agent.search.models import ScoredProduct
from quote_agent.search.proposability import is_product_proposable

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.elements import ColumnElement

    from quote_agent.config import ProposabilitySettings

REF_CODE_PATTERN = re.compile(
    r"^[A-Z]{2,6}[-_][A-Z0-9.²]+(?:[-_][A-Z0-9.²x]+)*$",
    re.IGNORECASE,
)


def is_reference_code(query: str) -> bool:
    """Return True if query looks like a product reference code."""
    return bool(REF_CODE_PATTERN.match(query.strip()))


async def search_keyword(
    session: AsyncSession,
    query_text: str,
    limit: int,
    *,
    include_stale: bool = False,
    proposability_clauses: list[ColumnElement[bool]] | None = None,
    proposability_settings: ProposabilitySettings | None = None,
) -> list[ScoredProduct]:
    """Full-text search using French tsvector with cover density ranking."""
    tsquery = func.plainto_tsquery("french", query_text)
    rank = func.ts_rank_cd(Product.search_vector, tsquery)

    stmt = (
        select(Product, rank.label("rank_score"))
        .where(Product.search_vector.op("@@")(tsquery))
        .order_by(rank.desc())
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
    for position, (product, rank_score) in enumerate(rows, start=1):
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
                score=float(rank_score),
                rank=position,
                match_source="keyword",
                is_proposable=proposable,
            )
        )

    return scored


async def search_exact_ref(
    session: AsyncSession,
    query_text: str,
    limit: int,
    *,
    include_stale: bool = False,
    proposability_clauses: list[ColumnElement[bool]] | None = None,
    proposability_settings: ProposabilitySettings | None = None,
) -> list[ScoredProduct]:
    """Exact reference matching — ILIKE on reference column, score = 1.0."""
    stmt = select(Product).where(Product.reference.ilike(query_text.strip())).limit(limit)

    if not include_stale:
        stmt = stmt.where(Product.is_stale.is_(False))

    if proposability_clauses:
        for clause in proposability_clauses:
            stmt = stmt.where(clause)

    result = await session.execute(stmt)
    products = result.scalars().all()

    return [
        ScoredProduct(
            product_id=product.id,
            reference=product.reference,
            name=product.name,
            category=product.category,
            description=product.description,
            unit_price=product.unit_price,
            score=1.0,
            rank=rank,
            match_source="exact_ref",
            is_proposable=(
                is_product_proposable(product.is_active, product.stock_status, product.category, proposability_settings)
                if proposability_settings is not None
                else True
            ),
        )
        for rank, product in enumerate(products, start=1)
    ]
