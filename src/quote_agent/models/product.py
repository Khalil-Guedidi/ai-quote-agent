"""SQLAlchemy model for the products table."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Index, Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from quote_agent.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    """Catalog product ingested from ERP — stored as-is, zero preprocessing."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    odoo_id: Mapped[int | None] = mapped_column(unique=True, nullable=True)
    reference: Mapped[str] = mapped_column(default="")
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text, default=None)
    category: Mapped[str] = mapped_column(default="Uncategorized")
    unit_price: Mapped[float] = mapped_column(default=0.0)
    stock_status: Mapped[str] = mapped_column(default="in_stock")
    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_: Mapped[dict[str, object] | None] = mapped_column("metadata_", JSON, default=None, nullable=True)
    is_stale: Mapped[bool] = mapped_column(default=False)

    # Embedding vector — populated by EmbeddingService (Story 3.2)
    vector: Mapped[list[float] | None] = mapped_column(Vector(dim=1024), nullable=True, default=None)

    # Full-text search vector — populated by DB trigger (Story 3.3)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True, default=None)

    __table_args__ = (
        Index("ix_products_reference", "reference"),
        Index("ix_products_category", "category"),
        Index("ix_products_odoo_id", "odoo_id"),
        Index("ix_products_is_active", "is_active"),
    )
