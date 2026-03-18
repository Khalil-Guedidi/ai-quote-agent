"""SQLAlchemy model for the email_requests table."""

import uuid
from datetime import datetime

from sqlalchemy import Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from quote_agent.models.base import Base, TimestampMixin


class EmailRequest(Base, TimestampMixin):
    """Persisted inbound email awaiting processing."""

    __tablename__ = "email_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    message_id: Mapped[str] = mapped_column(unique=True)
    subject: Mapped[str]
    sender: Mapped[str]
    recipients: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_content: Mapped[str] = mapped_column(Text)
    cleaned_content: Mapped[str | None] = mapped_column(Text, default=None)
    folder: Mapped[str]
    status: Mapped[str] = mapped_column(default="received")
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    received_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index("ix_email_requests_status", "status"),
    )
