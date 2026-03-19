"""Pydantic DTOs for LLM-based structured data extraction from quote request emails."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuoteLineItem(BaseModel):
    """A single product line item extracted from a quote request."""

    description: str
    quantity: float | None = None
    unit: str | None = None
    specifications: str | None = None
    reference: str | None = None


class ExtractedQuoteRequest(BaseModel):
    """Structured data extracted from a quote request email."""

    client_name: str | None = None
    client_identifier: str | None = None
    client_email: str | None = None
    line_items: list[QuoteLineItem] = Field(default_factory=list)
    urgency: str | None = None
    delivery_address: str | None = None
    notes: str | None = None
    raw_text: str = ""


class ExtractionResult(BaseModel):
    """Wrapper around extraction output with metadata."""

    request: ExtractedQuoteRequest
    confidence: float
    missing_fields: list[str] = Field(default_factory=list)
    extraction_duration_ms: int


class RequestGroup(BaseModel):
    """A group of line items forming a single quote request."""

    line_item_indices: list[int]
    rationale: str


class SplitDecision(BaseModel):
    """LLM decision on how to group line items into distinct requests."""

    groups: list[RequestGroup]


class SplitResult(BaseModel):
    """Result of splitting an extraction into one or more sub-requests."""

    requests: list[ExtractedQuoteRequest]
    split_count: int
    split_rationale: str
    split_duration_ms: int
