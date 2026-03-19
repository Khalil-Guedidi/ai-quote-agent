"""Typed DTOs for the embedding adapter layer."""

from __future__ import annotations

from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    """Request payload for embedding generation."""

    texts: list[str]


class EmbeddingResult(BaseModel):
    """Summary of an embedding generation run."""

    embedded: int
    skipped_stale: int
    errors: int
    duration_seconds: float
