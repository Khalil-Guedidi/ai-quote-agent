"""Proposability filter — SQL WHERE clauses and pure-Python check for product proposability."""

from __future__ import annotations

from typing import TYPE_CHECKING

from quote_agent.models.product import Product

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from quote_agent.config import ProposabilitySettings


def build_proposability_clauses(settings: ProposabilitySettings) -> list[ColumnElement[bool]]:
    """Return SQL WHERE clauses that exclude non-proposable products based on settings."""
    clauses: list[ColumnElement[bool]] = []
    if settings.exclude_inactive:
        clauses.append(Product.is_active.is_(True))
    if settings.exclude_out_of_stock:
        clauses.append(Product.stock_status != "out_of_stock")
    if settings.excluded_categories:
        clauses.append(Product.category.notin_(settings.excluded_categories))
    return clauses


def is_product_proposable(
    product_active: bool,
    stock_status: str,
    category: str,
    settings: ProposabilitySettings,
) -> bool:
    """Pure Python check mirroring SQL logic — used to set ScoredProduct.is_proposable."""
    if settings.exclude_inactive and not product_active:
        return False
    if settings.exclude_out_of_stock and stock_status == "out_of_stock":
        return False
    return not (settings.excluded_categories and category in settings.excluded_categories)
