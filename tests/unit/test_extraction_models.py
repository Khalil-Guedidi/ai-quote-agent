"""Unit tests for Pydantic extraction models."""

from __future__ import annotations

from quote_agent.services.extraction_models import (
    ExtractedQuoteRequest,
    ExtractionResult,
    QuoteLineItem,
)


def test_quote_line_item_all_fields() -> None:
    """QuoteLineItem with all fields populated."""
    item = QuoteLineItem(
        description="Roulement à billes SKF 6205",
        quantity=50.0,
        unit="pièces",
        specifications="étanche, acier inox",
        reference="REF-6205-2RS",
    )
    assert item.description == "Roulement à billes SKF 6205"
    assert item.quantity == 50.0
    assert item.unit == "pièces"
    assert item.specifications == "étanche, acier inox"
    assert item.reference == "REF-6205-2RS"


def test_quote_line_item_only_description() -> None:
    """QuoteLineItem with only description — all optional fields None."""
    item = QuoteLineItem(description="Tube acier 50mm")
    assert item.description == "Tube acier 50mm"
    assert item.quantity is None
    assert item.unit is None
    assert item.specifications is None
    assert item.reference is None


def test_extracted_quote_request_multiple_line_items() -> None:
    """ExtractedQuoteRequest with multiple line items."""
    request = ExtractedQuoteRequest(
        client_name="Jean Dupont",
        client_identifier="CLI-001",
        client_email="jean@example.com",
        line_items=[
            QuoteLineItem(description="Vis M8x40", quantity=100.0, unit="pièces"),
            QuoteLineItem(description="Écrou M8", quantity=100.0, unit="pièces"),
            QuoteLineItem(description="Rondelle M8", quantity=200.0, unit="pièces"),
        ],
        raw_text="Bonjour, je souhaite un devis...",
    )
    assert request.client_name == "Jean Dupont"
    assert len(request.line_items) == 3
    assert request.line_items[1].description == "Écrou M8"


def test_extracted_quote_request_missing_client_info() -> None:
    """ExtractedQuoteRequest with missing client info (None, not hallucinated)."""
    request = ExtractedQuoteRequest(
        client_name=None,
        client_identifier=None,
        client_email=None,
        line_items=[QuoteLineItem(description="Pompe hydraulique")],
        raw_text="Merci de me faire un devis pour une pompe hydraulique.",
    )
    assert request.client_name is None
    assert request.client_identifier is None
    assert request.client_email is None
    assert len(request.line_items) == 1


def test_extraction_result_missing_fields_correctly_listed() -> None:
    """ExtractionResult.missing_fields correctly lists null fields."""
    request = ExtractedQuoteRequest(
        client_name=None,
        client_identifier=None,
        line_items=[
            QuoteLineItem(description="Câble 3G2.5", quantity=None, reference=None),
        ],
        raw_text="test",
    )
    missing = ["client_name", "client_identifier", "line_items[0].quantity", "line_items[0].reference"]
    result = ExtractionResult(
        request=request,
        confidence=0.7,
        missing_fields=missing,
        extraction_duration_ms=450,
    )
    assert "client_name" in result.missing_fields
    assert "client_identifier" in result.missing_fields
    assert "line_items[0].quantity" in result.missing_fields
    assert result.extraction_duration_ms == 450
    assert result.confidence == 0.7
