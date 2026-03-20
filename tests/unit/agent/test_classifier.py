"""Unit tests for the complexity classifier node."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.agent.nodes.classifier import (
    UNTRUSTED_QUOTE_END,
    UNTRUSTED_QUOTE_START,
    ClassificationInput,
    ClassificationResult,
    _build_classification_messages,
    classify_request,
)
from quote_agent.exceptions import AdapterError, LLMTimeoutError
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem


def _make_request(
    *,
    description: str = "Tube inox 304L DN50",
    quantity: float | None = 10.0,
    reference: str | None = "REF-001",
    urgency: str | None = None,
    notes: str | None = None,
) -> ExtractedQuoteRequest:
    """Build a minimal ExtractedQuoteRequest for testing."""
    return ExtractedQuoteRequest(
        line_items=[
            QuoteLineItem(
                description=description,
                quantity=quantity,
                reference=reference,
            ),
        ],
        urgency=urgency,
        notes=notes,
        raw_text=description,
    )


def _make_classification(
    complexity: str = "simple",
    confidence: float = 0.95,
) -> ClassificationResult:
    """Build a ClassificationResult for mock returns."""
    return ClassificationResult(
        complexity=complexity,  # type: ignore[arg-type]
        reasons=["Clear product reference with quantity"],
        confidence=confidence,
        classification_duration_ms=0,
    )


def _make_adapter_mock(result: ClassificationResult) -> MagicMock:
    """Create a mock LLM adapter that returns structured output."""
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=result)
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value = mock_structured
    adapter = MagicMock()
    adapter.get_model.return_value = mock_model
    return adapter


@pytest.fixture()
def _mock_settings() -> None:
    """Provide mock settings with classification config."""
    mock_settings = MagicMock()
    mock_settings.classification.timeout_seconds = 10
    mock_settings.classification.fallback_complexity = "complex"
    with patch("quote_agent.config.get_settings", return_value=mock_settings):
        yield


class TestClassifySimpleRequest:
    """AC-1: Clear product reference + quantity → simple."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_classifies_simple_when_clear_reference_and_quantity(self) -> None:
        request = _make_request(description="Tube inox 304L DN50", quantity=10.0, reference="REF-001")
        expected = _make_classification("simple", 0.95)
        adapter = _make_adapter_mock(expected)

        result = await classify_request(request, adapter)

        assert result.complexity == "simple"
        assert result.confidence == 0.95
        adapter.get_model.assert_called_once_with("simple")


class TestClassifyAmbiguousRequest:
    """AC-2: Vague description → ambiguous."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_classifies_ambiguous_when_vague_description(self) -> None:
        request = _make_request(description="comme la dernière fois mais plus long", quantity=None, reference=None)
        expected = _make_classification("ambiguous", 0.8)
        adapter = _make_adapter_mock(expected)

        result = await classify_request(request, adapter)

        assert result.complexity == "ambiguous"
        assert len(result.reasons) >= 1


class TestClassifyComplexRequest:
    """AC-3: Multiple custom products → complex."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_classifies_complex_when_multiple_special_conditions(self) -> None:
        request = ExtractedQuoteRequest(
            line_items=[
                QuoteLineItem(description="Bride PN40 DN100 inox 316L", quantity=20.0),
                QuoteLineItem(description="Joint spiralé graphite DN100 PN40", quantity=20.0),
                QuoteLineItem(description="Boulonnerie HR classe 10.9 M20x80", quantity=80.0),
            ],
            notes="Certification 3.1 requise. Livraison chantier Fos-sur-Mer avant le 15 avril.",
            raw_text="Multiple products with certifications",
        )
        expected = _make_classification("complex", 0.9)
        adapter = _make_adapter_mock(expected)

        result = await classify_request(request, adapter)

        assert result.complexity == "complex"


class TestClassifyOutOfScopeRequest:
    """AC-4: Service request → out_of_scope."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_classifies_out_of_scope_when_service_request(self) -> None:
        request = _make_request(description="Besoin d'une intervention de maintenance sur le compresseur")
        expected = _make_classification("out_of_scope", 0.85)
        adapter = _make_adapter_mock(expected)

        result = await classify_request(request, adapter)

        assert result.complexity == "out_of_scope"
        assert len(result.reasons) >= 1


class TestClassifyTimeoutFallback:
    """AC-1: Timeout → fallback to complex."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_complex_fallback_when_timeout(self) -> None:
        request = _make_request()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await classify_request(request, adapter)

        assert result.complexity == "complex"
        assert result.confidence == 0.0
        assert any("timed out" in r.lower() or "timeout" in r.lower() for r in result.reasons)

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_complex_fallback_when_llm_timeout_error(self) -> None:
        request = _make_request()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=LLMTimeoutError("LLM timeout"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await classify_request(request, adapter)

        assert result.complexity == "complex"
        assert result.confidence == 0.0


class TestClassifyAdapterErrorFallback:
    """AC-1: AdapterError → fallback to complex."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_complex_fallback_when_adapter_error(self) -> None:
        request = _make_request()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=AdapterError("API connection failed"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await classify_request(request, adapter)

        assert result.complexity == "complex"
        assert result.confidence == 0.0
        assert any("error" in r.lower() for r in result.reasons)


class TestClassificationDuration:
    """AC-1: classification_duration_ms is populated."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_duration_populated_when_success(self) -> None:
        request = _make_request()
        expected = _make_classification("simple", 0.95)
        adapter = _make_adapter_mock(expected)

        result = await classify_request(request, adapter)

        assert result.classification_duration_ms >= 0

    @pytest.mark.usefixtures("_mock_settings")
    async def test_duration_populated_when_timeout(self) -> None:
        request = _make_request()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await classify_request(request, adapter)

        assert result.classification_duration_ms >= 0


class TestInputIsolationDelimiters:
    """AC-1: Input isolation delimiters present in prompt."""

    def test_delimiters_present_when_building_messages(self) -> None:
        input_data = ClassificationInput(
            description="Tube inox 304L",
            quantity=10.0,
            reference="REF-001",
        )

        messages = _build_classification_messages(input_data)

        assert len(messages) == 2
        human_msg = messages[1]
        assert UNTRUSTED_QUOTE_START in human_msg.content
        assert UNTRUSTED_QUOTE_END in human_msg.content

    def test_all_fields_present_when_populated(self) -> None:
        input_data = ClassificationInput(
            description="Tube inox",
            quantity=5.0,
            unit="mètres",
            specifications="304L",
            reference="REF-001",
            urgency="urgent",
            notes="Livraison rapide",
        )

        messages = _build_classification_messages(input_data)

        content = messages[1].content
        assert "Description: Tube inox" in content
        assert "Quantité: 5.0" in content
        assert "Unité: mètres" in content
        assert "Spécifications: 304L" in content
        assert "Référence: REF-001" in content
        assert "Urgence: urgent" in content
        assert "Notes: Livraison rapide" in content


class TestClassificationInput:
    """ClassificationInput.from_extracted_request builds correctly."""

    def test_from_extracted_request_when_single_line_item(self) -> None:
        request = _make_request(description="Tube inox", quantity=10.0, reference="REF-001")

        result = ClassificationInput.from_extracted_request(request)

        assert "Tube inox" in result.description
        assert result.quantity == 10.0
        assert result.reference == "REF-001"

    def test_from_extracted_request_when_no_line_items(self) -> None:
        request = ExtractedQuoteRequest(raw_text="some raw text")

        result = ClassificationInput.from_extracted_request(request)

        assert result.description == "some raw text"
        assert result.quantity is None
        assert result.reference is None
