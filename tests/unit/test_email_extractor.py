"""Unit tests for email_extractor.extract() function."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from quote_agent.exceptions import AdapterError, LLMTimeoutError
from quote_agent.services.email_extractor import extract
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem


def _mock_adapter(return_value: ExtractedQuoteRequest) -> MagicMock:
    """Create a mock LLM adapter that returns a predefined extraction result."""
    structured_model = MagicMock()
    structured_model.ainvoke = AsyncMock(return_value=return_value)

    model = MagicMock()
    model.with_structured_output = MagicMock(return_value=structured_model)

    adapter = MagicMock()
    adapter.get_model = MagicMock(return_value=model)
    return adapter


@patch("quote_agent.services.email_extractor.get_llm_adapter")
async def test_simple_french_quote_extraction(mock_get_adapter: MagicMock) -> None:
    """Simple French quote request extracts client name and line items correctly."""
    expected = ExtractedQuoteRequest(
        client_name="Jean Dupont",
        client_identifier="CLI-001",
        client_email="jean@dupont.fr",
        line_items=[
            QuoteLineItem(description="Roulement SKF 6205", quantity=50.0, unit="pièces", reference="REF-6205"),
        ],
        raw_text="",
    )
    mock_get_adapter.return_value = _mock_adapter(expected)

    result = await extract(
        cleaned_content="Bonjour, je souhaite un devis pour 50 roulements SKF 6205.",
        sender="jean@dupont.fr",
        subject="Demande de devis",
    )

    assert result.request.client_name == "Jean Dupont"
    assert len(result.request.line_items) == 1
    assert result.request.line_items[0].quantity == 50.0


@patch("quote_agent.services.email_extractor.get_llm_adapter")
async def test_partial_info_returns_none_not_guess(mock_get_adapter: MagicMock) -> None:
    """Email with partial info (no quantity) returns None for quantity, not a guess."""
    expected = ExtractedQuoteRequest(
        client_name="Marie Martin",
        line_items=[
            QuoteLineItem(description="Pompe hydraulique", quantity=None, unit=None),
        ],
        raw_text="",
    )
    mock_get_adapter.return_value = _mock_adapter(expected)

    result = await extract(
        cleaned_content="Merci de me faire un devis pour une pompe hydraulique.",
        sender="marie@example.com",
        subject="Devis pompe",
    )

    assert result.request.line_items[0].quantity is None
    assert "line_items[0].quantity" in result.missing_fields


@patch("quote_agent.services.email_extractor.get_llm_adapter")
async def test_multiple_products_extracted(mock_get_adapter: MagicMock) -> None:
    """Email with multiple products extracts all line items."""
    expected = ExtractedQuoteRequest(
        client_name="Pierre Lefèvre",
        line_items=[
            QuoteLineItem(description="Vis M8x40", quantity=100.0, unit="pièces"),
            QuoteLineItem(description="Écrou M8", quantity=100.0, unit="pièces"),
            QuoteLineItem(description="Rondelle M8", quantity=200.0, unit="pièces"),
        ],
        raw_text="",
    )
    mock_get_adapter.return_value = _mock_adapter(expected)

    result = await extract(
        cleaned_content="Devis pour 100 vis M8x40, 100 écrous M8 et 200 rondelles M8.",
        sender="pierre@example.com",
        subject="Devis boulonnerie",
    )

    assert len(result.request.line_items) == 3


@patch("quote_agent.services.email_extractor.get_llm_adapter")
async def test_product_references_captured(mock_get_adapter: MagicMock) -> None:
    """Email with product references captures reference field."""
    expected = ExtractedQuoteRequest(
        client_name="Sophie Durand",
        line_items=[
            QuoteLineItem(description="Câble 3G2.5", quantity=500.0, unit="mètres", reference="REF-12345"),
        ],
        raw_text="",
    )
    mock_get_adapter.return_value = _mock_adapter(expected)

    result = await extract(
        cleaned_content="500m de câble 3G2.5 référence REF-12345 svp.",
        sender="sophie@example.com",
        subject="Devis câblage",
    )

    assert result.request.line_items[0].reference == "REF-12345"


@patch("quote_agent.services.email_extractor._EXTRACTION_TIMEOUT", 0.05)
@patch("quote_agent.services.email_extractor.get_llm_adapter")
async def test_extraction_timeout_raises_llm_timeout_error(mock_get_adapter: MagicMock) -> None:
    """Extraction timeout raises LLMTimeoutError."""
    structured_model = MagicMock()

    async def _slow_invoke(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(100)

    structured_model.ainvoke = _slow_invoke
    model = MagicMock()
    model.with_structured_output = MagicMock(return_value=structured_model)
    adapter = MagicMock()
    adapter.get_model = MagicMock(return_value=model)
    mock_get_adapter.return_value = adapter

    with pytest.raises(LLMTimeoutError, match="NFR-P3"):
        await extract(
            cleaned_content="Bonjour, je souhaite un devis pour des roulements.",
            sender="test@example.com",
            subject="Devis",
        )


@patch("quote_agent.services.email_extractor.get_llm_adapter")
async def test_adapter_error_raised(mock_get_adapter: MagicMock) -> None:
    """LLM adapter error raises AdapterError."""
    structured_model = MagicMock()
    structured_model.ainvoke = AsyncMock(
        side_effect=openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )
    )
    model = MagicMock()
    model.with_structured_output = MagicMock(return_value=structured_model)
    adapter = MagicMock()
    adapter.get_model = MagicMock(return_value=model)
    mock_get_adapter.return_value = adapter

    with pytest.raises(AdapterError):
        await extract(
            cleaned_content="Bonjour, je souhaite un devis pour des roulements.",
            sender="test@example.com",
            subject="Devis",
        )


@patch("quote_agent.services.email_extractor.get_llm_adapter")
async def test_extraction_duration_measured(mock_get_adapter: MagicMock) -> None:
    """Extraction duration is measured and returned."""
    expected = ExtractedQuoteRequest(
        client_name="Test",
        line_items=[QuoteLineItem(description="Test product", quantity=1.0)],
        raw_text="",
    )
    mock_get_adapter.return_value = _mock_adapter(expected)

    result = await extract(
        cleaned_content="Devis pour 1 test product svp.",
        sender="test@example.com",
        subject="Devis",
    )

    assert result.extraction_duration_ms >= 0


async def test_empty_content_returns_empty_line_items() -> None:
    """Empty email content returns empty line_items list (not an error)."""
    result = await extract(
        cleaned_content="short",
        sender="test@example.com",
        subject="Devis",
    )

    assert result.request.line_items == []
    assert result.confidence == 0.0
    assert result.extraction_duration_ms == 0
