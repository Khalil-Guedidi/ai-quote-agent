"""SQLAlchemy model for the quote_requests table."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from quote_agent.models.base import Base, TimestampMixin


class QuoteRequest(Base, TimestampMixin):
    """Individual quote request extracted from an email (1 email -> N requests)."""

    __tablename__ = "quote_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_requests.id"),
    )
    request_index: Mapped[int] = mapped_column(default=0)
    line_items: Mapped[list[dict]] = mapped_column(JSON, default=list)
    client_name: Mapped[str | None] = mapped_column(default=None)
    client_identifier: Mapped[str | None] = mapped_column(default=None)
    client_email: Mapped[str | None] = mapped_column(default=None)
    urgency: Mapped[str | None] = mapped_column(default=None)
    delivery_address: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    confidence: Mapped[float | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint(
            "email_request_id",
            "request_index",
            name="uq_quote_requests_email_request_id_request_index",
        ),
        Index("ix_quote_requests_email_request_id", "email_request_id"),
        Index("ix_quote_requests_status", "status"),
    )
