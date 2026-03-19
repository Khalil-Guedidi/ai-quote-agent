"""Typed DTOs for the ERP adapter layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OdooVersionInfo(BaseModel):
    """Version information returned by Odoo XML-RPC common.version()."""

    server_version: str
    protocol_version: int


class Product(BaseModel):
    """Product catalog entry from ERP — stored as-is, zero preprocessing."""

    odoo_id: int | None = None
    reference: str
    name: str
    description: str | None = None
    category: str
    unit_price: float
    stock_status: str
    is_active: bool
    metadata: dict[str, Any] = {}


class ProductFilter(BaseModel):
    """Optional filters for product retrieval from ERP."""

    active_only: bool = True
    category: str | None = None
    limit: int = 500
    offset: int = 0


class IngestionResult(BaseModel):
    """Summary of a catalog ingestion run."""

    inserted: int
    updated: int
    unchanged: int
    stale: int
    duration_seconds: float
