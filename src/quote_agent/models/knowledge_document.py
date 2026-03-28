"""SQLAlchemy model for the knowledge_documents table."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Boolean, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from quote_agent.models.base import Base, TimestampMixin


class KnowledgeDocument(Base, TimestampMixin):
    """Industry knowledge document chunk — stored with vector embedding for RAG retrieval."""

    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String, default="")
    source: Mapped[str] = mapped_column(String, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    vector: Mapped[list[float] | None] = mapped_column(Vector(dim=1024), nullable=True, default=None)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True, default=None)
    metadata_: Mapped[dict[str, object] | None] = mapped_column("metadata_", JSON, default=None, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
