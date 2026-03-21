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


class Client(BaseModel):
    """Client (res.partner) entry from ERP."""

    odoo_id: int
    name: str
    ref: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    vat: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] = {}


class ClientOrderHistory(BaseModel):
    """Single order line from client order history."""

    order_id: str
    date: str
    product_ref: str | None = None
    product_name: str
    quantity: float
    unit_price: float
    total: float
    state: str


class ClientFilter(BaseModel):
    """Optional filters for client search from ERP."""

    search_term: str | None = None
    limit: int = 20
    offset: int = 0


class UniversalQuoteLine(BaseModel):
    """Single line item for a draft quote — ERP-agnostic."""

    product_id: int
    product_ref: str | None = None
    product_name: str
    quantity: float
    unit_price: float
    description: str | None = None


class UniversalQuote(BaseModel):
    """ERP-agnostic draft quote DTO — translated to Odoo sale.order by the adapter."""

    client_id: str
    client_name: str
    lines: list[UniversalQuoteLine]
    delivery_date: str | None = None
    notes: str | None = None


class QuoteDraftResult(BaseModel):
    """Result of creating a draft quote in the ERP."""

    odoo_id: int
    order_reference: str
    state: str
    line_count: int
