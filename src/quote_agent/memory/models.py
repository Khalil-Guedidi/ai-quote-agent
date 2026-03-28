"""Pydantic DTOs for the memory module."""

from __future__ import annotations

from pydantic import BaseModel


class KnowledgeChunk(BaseModel):
    """A single retrieved chunk from the industry knowledge base."""

    content: str
    title: str
    source: str
    score: float
    metadata: dict[str, object] | None = None


class IngestionResult(BaseModel):
    """Result of ingesting a document into the knowledge base."""

    document_title: str
    chunks_created: int
    source: str
