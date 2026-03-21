"""Unit tests for the confidence scorer node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.agent.nodes.classifier import ClassificationResult
from quote_agent.agent.nodes.confidence_scorer import (
    UNTRUSTED_QUOTE_END,
    UNTRUSTED_QUOTE_START,
    ConfidenceResult,
    ProductConfidence,
    ScoringInput,
    _build_scoring_messages,
    score_confidence,
)
from quote_agent.exceptions import AdapterError, LLMTimeoutError
from quote_agent.search.models import ScoredProduct, SearchResult
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem


def _make_request(
    *,
    description: str = "Tube inox 304L DN50",
    quantity: float | None = 10.0,
    reference: str | None = "REF-001",
    urgency: str | None = None,
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
        raw_text=description,
    )


def _make_classification(
    complexity: str = "simple",
    confidence: float = 0.95,
) -> ClassificationResult:
    """Build a ClassificationResult for mock inputs."""
    return ClassificationResult(
        complexity=complexity,  # type: ignore[arg-type]
        reasons=["Clear product reference with quantity"],
        confidence=confidence,
        classification_duration_ms=50,
    )


def _make_search_result() -> SearchResult:
    """Build a minimal SearchResult for testing."""
    return SearchResult(
        results=[
            ScoredProduct(
                product_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
                reference="REF-001",
                name="Tube inox 304L DN50 6m",
                category="Tubes",
                description="Tube en acier inoxydable 304L diametre nominal 50mm",
                unit_price=45.0,
                score=0.92,
                rank=1,
                match_source="hybrid",
            ),
            ScoredProduct(
                product_id="00000000-0000-0000-0000-000000000002",  # type: ignore[arg-type]
                reference="REF-002",
                name="Tube inox 316L DN50 6m",
                category="Tubes",
                description="Tube en acier inoxydable 316L diametre nominal 50mm",
                unit_price=65.0,
                score=0.85,
                rank=2,
                match_source="hybrid",
            ),
        ],
        total_found=2,
        query="Tube inox 304L DN50",
        method="hybrid",
        duration_seconds=0.15,
    )


def _make_confidence_result(
    overall: float = 0.90,
    tier: str = "high",
) -> ConfidenceResult:
    """Build a ConfidenceResult for mock returns."""
    return ConfidenceResult(
        overall_confidence=overall,
        tier=tier,  # type: ignore[arg-type]
        product_scores=[
            ProductConfidence(
                product_id="00000000-0000-0000-0000-000000000001",
                reference="REF-001",
                name="Tube inox 304L DN50 6m",
                confidence=0.92,
                match_quality="Exact reference match with matching specifications",
                rank=1,
            ),
        ],
        reasoning=["High confidence: exact reference match and matching specs"],
        scoring_duration_ms=0,
    )


def _make_adapter_mock(result: ConfidenceResult) -> MagicMock:
    """Create a mock LLM adapter that returns structured output."""
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=result)
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value = mock_structured
    adapter = MagicMock()
    adapter.get_model.return_value = mock_model
    return adapter


@pytest.fixture()
def _mock_settings():
    """Provide mock settings with confidence scoring config."""
    mock_settings = MagicMock()
    mock_settings.confidence_scoring.timeout_seconds = 10
    mock_settings.confidence_scoring.fallback_tier = "low"
    with patch("quote_agent.config.get_settings", return_value=mock_settings):
        yield


class TestHighConfidenceScoring:
    """AC-1: High confidence (>85%) returns tier=high."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_high_tier_when_high_confidence(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        expected = _make_confidence_result(overall=0.92, tier="high")
        adapter = _make_adapter_mock(expected)

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.tier == "high"
        assert result.overall_confidence == 0.92
        adapter.get_model.assert_called_once_with("simple")


class TestMediumConfidenceScoring:
    """AC-2: Medium confidence (50-85%) returns tier=medium."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_medium_tier_when_medium_confidence(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        expected = _make_confidence_result(overall=0.70, tier="medium")
        adapter = _make_adapter_mock(expected)

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.tier == "medium"
        assert result.overall_confidence == 0.70


class TestLowConfidenceScoring:
    """AC-3: Low confidence (<50%) returns tier=low."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_low_tier_when_low_confidence(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        expected = _make_confidence_result(overall=0.30, tier="low")
        adapter = _make_adapter_mock(expected)

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.tier == "low"
        assert result.overall_confidence == 0.30


class TestTimeoutFallback:
    """AC-1: Timeout returns tier=low with confidence=0.0."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_low_fallback_when_timeout(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.tier == "low"
        assert result.overall_confidence == 0.0
        assert any("timed out" in r.lower() or "timeout" in r.lower() for r in result.reasoning)


class TestAdapterErrorFallback:
    """AC-1: AdapterError returns tier=low with confidence=0.0."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_low_fallback_when_adapter_error(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=AdapterError("API down"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.tier == "low"
        assert result.overall_confidence == 0.0
        assert any("error" in r.lower() for r in result.reasoning)

    @pytest.mark.usefixtures("_mock_settings")
    async def test_returns_low_fallback_when_llm_timeout_error(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=LLMTimeoutError("LLM timeout"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.tier == "low"
        assert result.overall_confidence == 0.0


class TestScoringDuration:
    """AC-1: scoring_duration_ms is populated."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_duration_populated_when_success(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        expected = _make_confidence_result()
        adapter = _make_adapter_mock(expected)

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.scoring_duration_ms >= 0

    @pytest.mark.usefixtures("_mock_settings")
    async def test_duration_populated_when_timeout(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await score_confidence(classification, search_result, request, adapter)

        assert result.scoring_duration_ms >= 0


class TestInputIsolationDelimiters:
    """AC-1: Input isolation delimiters present in the prompt sent to LLM."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_delimiters_present_in_llm_prompt(self) -> None:
        request = _make_request()
        classification = _make_classification()
        search_result = _make_search_result()
        expected = _make_confidence_result()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=expected)
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        await score_confidence(classification, search_result, request, adapter)

        # Verify ainvoke was called with messages containing delimiters
        call_args = mock_structured.ainvoke.call_args[0][0]
        human_msg = call_args[1]
        assert UNTRUSTED_QUOTE_START in human_msg.content
        assert UNTRUSTED_QUOTE_END in human_msg.content

    def test_delimiters_present_when_building_messages(self) -> None:
        input_data = ScoringInput(
            classification_complexity="simple",
            classification_reasons=["Clear reference"],
            classification_confidence=0.95,
            search_results=[],
            request_description="Tube inox 304L",
            request_quantity=10.0,
            request_reference="REF-001",
        )

        messages = _build_scoring_messages(input_data)

        assert len(messages) == 2
        human_msg = messages[1]
        assert UNTRUSTED_QUOTE_START in human_msg.content
        assert UNTRUSTED_QUOTE_END in human_msg.content


class TestClassificationContextInfluence:
    """AC-1: Classification context influences scoring (ambiguous → stricter)."""

    def test_ambiguous_classification_adds_strict_warning(self) -> None:
        input_data = ScoringInput(
            classification_complexity="ambiguous",
            classification_reasons=["Vague description"],
            classification_confidence=0.6,
            search_results=[],
            request_description="comme la derniere fois",
        )

        messages = _build_scoring_messages(input_data)

        system_msg = messages[0]
        assert "ATTENTION" in system_msg.content
        assert "ambigue" in system_msg.content.lower()

    def test_simple_classification_no_strict_warning(self) -> None:
        input_data = ScoringInput(
            classification_complexity="simple",
            classification_reasons=["Clear reference"],
            classification_confidence=0.95,
            search_results=[],
            request_description="Tube inox 304L DN50",
        )

        messages = _build_scoring_messages(input_data)

        system_msg = messages[0]
        assert "ATTENTION" not in system_msg.content


class TestScoringInput:
    """ScoringInput.from_components builds correctly."""

    def test_from_components_when_standard_inputs(self) -> None:
        classification = _make_classification()
        search_result = _make_search_result()
        request = _make_request()

        result = ScoringInput.from_components(classification, search_result, request)

        assert result.classification_complexity == "simple"
        assert len(result.search_results) == 2
        assert "Tube inox 304L DN50" in result.request_description
        assert result.request_quantity == 10.0
        assert result.request_reference == "REF-001"

    def test_from_components_when_no_line_items(self) -> None:
        classification = _make_classification()
        search_result = _make_search_result()
        request = ExtractedQuoteRequest(raw_text="some raw text")

        result = ScoringInput.from_components(classification, search_result, request)

        assert result.request_description == "some raw text"
        assert result.request_quantity is None
        assert result.request_reference is None
