"""Search DTOs — request, scored product, and result models."""

from __future__ import annotations

import uuid  # noqa: TC003 — Pydantic needs runtime access for UUID field
from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Incoming search query."""

    query: str
    limit: int = 10
    include_stale: bool = False
    apply_proposability_filter: bool = True


class ScoredProduct(BaseModel):
    """A product with its search relevance score."""

    product_id: uuid.UUID
    reference: str
    name: str
    category: str
    description: str | None = None
    unit_price: float
    score: float
    rank: int
    match_source: Literal["semantic", "keyword", "exact_ref", "hybrid"]
    is_proposable: bool = True


class SearchResult(BaseModel):
    """Container for search results with metadata."""

    results: list[ScoredProduct] = Field(default_factory=list)
    total_found: int
    query: str
    method: str
    duration_seconds: float
    from_cache: bool = False
    jargon_expanded: bool = False
    expanded_query: str | None = None
