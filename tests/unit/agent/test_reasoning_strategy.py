"""Unit tests for the adaptive reasoning strategy node."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.agent.nodes.classifier import ClassificationResult
from quote_agent.agent.nodes.reasoning_strategy import (
    UNTRUSTED_QUOTE_END,
    UNTRUSTED_QUOTE_START,
    ComparativeAnalysisResult,
    DeepEvaluationResult,
    EnrichmentResult,
    ReasoningResult,
    ReasoningStep,
    apply_reasoning_strategy,
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


def _make_search_result(n_results: int = 2) -> SearchResult:
    """Build a minimal SearchResult for testing."""
    results = [
        ScoredProduct(
            product_id=f"00000000-0000-0000-0000-00000000000{i + 1}",  # type: ignore[arg-type]
            reference=f"REF-{i + 1:03d}",
            name=f"Tube inox 304L DN50 {i + 1}m",
            category="Tubes",
            description="Tube en acier inoxydable 304L",
            unit_price=45.0 + i * 10,
            score=0.92 - i * 0.05,
            rank=i + 1,
            match_source="hybrid",
        )
        for i in range(n_results)
    ]
    return SearchResult(
        results=results,
        total_found=n_results,
        query="Tube inox 304L DN50",
        method="hybrid",
        duration_seconds=0.15,
    )


def _make_search_engine_mock(search_result: SearchResult | None = None) -> AsyncMock:
    """Create a mock SearchEngine that returns a fixed search result."""
    result = search_result or _make_search_result()
    mock_engine = AsyncMock()
    mock_engine.search_hybrid = AsyncMock(return_value=result)
    return mock_engine


def _make_adapter_mock_for_exploration(analysis: ComparativeAnalysisResult) -> MagicMock:
    """Create a mock LLM adapter for exploration strategy."""
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=analysis)
    mock_model = MagicMock()
    mock_model.with_structured_output.return_value = mock_structured
    adapter = MagicMock()
    adapter.get_model.return_value = mock_model
    return adapter


def _make_adapter_mock_for_deep(
    enrichment: EnrichmentResult,
    evaluation: DeepEvaluationResult,
) -> MagicMock:
    """Create a mock LLM adapter for deep analysis strategy (two sequential LLM calls)."""
    enrichment_structured = MagicMock()
    enrichment_structured.ainvoke = AsyncMock(return_value=enrichment)
    eval_structured = MagicMock()
    eval_structured.ainvoke = AsyncMock(return_value=evaluation)

    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(
        side_effect=[enrichment_structured, eval_structured],
    )
    adapter = MagicMock()
    adapter.get_model.return_value = mock_model
    return adapter


@pytest.fixture()
def _mock_settings():
    """Provide mock settings with reasoning config."""
    mock_settings = MagicMock()
    mock_settings.reasoning.timeout_seconds = 15
    mock_settings.reasoning.simple_search_limit = 5
    mock_settings.reasoning.ambiguous_search_limit = 10
    mock_settings.reasoning.complex_search_limit = 15
    with patch("quote_agent.config.get_settings", return_value=mock_settings):
        yield


class TestDirectMatchStrategy:
    """AC-1: Simple → Direct Match Strategy."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_simple_uses_direct_match_strategy(self) -> None:
        """AC-1: Simple request uses direct_match strategy."""
        request = _make_request()
        classification = _make_classification(complexity="simple")
        engine = _make_search_engine_mock()
        adapter = MagicMock()  # Not used for simple strategy

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.strategy == "direct_match"
        assert len(result.search_result.results) == 2
        engine.search_hybrid.assert_called_once()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_simple_no_llm_call(self) -> None:
        """AC-1: Simple strategy does NOT call LLM."""
        request = _make_request()
        classification = _make_classification(complexity="simple")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        await apply_reasoning_strategy(classification, request, adapter, engine)

        adapter.get_model.assert_not_called()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_simple_uses_simple_search_limit(self) -> None:
        """AC-1: Simple strategy uses configured simple_search_limit."""
        request = _make_request()
        classification = _make_classification(complexity="simple")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        await apply_reasoning_strategy(classification, request, adapter, engine)

        call_args = engine.search_hybrid.call_args[0][0]
        assert call_args.limit == 5

    @pytest.mark.usefixtures("_mock_settings")
    async def test_simple_records_search_step(self) -> None:
        """AC-5: Direct match records a search reasoning step."""
        request = _make_request()
        classification = _make_classification(complexity="simple")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert len(result.steps) == 1
        assert result.steps[0].step_name == "search"
        assert result.steps[0].duration_ms >= 0
        assert "results" in result.steps[0].outcome


class TestExplorationStrategy:
    """AC-2: Ambiguous → Exploration Strategy."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_ambiguous_uses_exploration_strategy(self) -> None:
        """AC-2: Ambiguous request uses exploration strategy."""
        request = _make_request(description="comme la derniere fois")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()
        analysis = ComparativeAnalysisResult(
            best_match_indices=[0],
            reasoning="Product 1 matches best",
            confidence_hint=0.65,
        )
        adapter = _make_adapter_mock_for_exploration(analysis)

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.strategy == "exploration"
        assert len(result.search_result.results) == 2

    @pytest.mark.usefixtures("_mock_settings")
    async def test_ambiguous_uses_complex_model(self) -> None:
        """AC-2: Exploration strategy uses the complex model."""
        request = _make_request(description="comme la derniere fois")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()
        analysis = ComparativeAnalysisResult(
            best_match_indices=[0],
            reasoning="Product 1 matches best",
            confidence_hint=0.65,
        )
        adapter = _make_adapter_mock_for_exploration(analysis)

        await apply_reasoning_strategy(classification, request, adapter, engine)

        adapter.get_model.assert_called_with("complex")

    @pytest.mark.usefixtures("_mock_settings")
    async def test_ambiguous_uses_ambiguous_search_limit(self) -> None:
        """AC-2: Exploration uses configured ambiguous_search_limit."""
        request = _make_request(description="comme la derniere fois")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()
        analysis = ComparativeAnalysisResult(
            best_match_indices=[0],
            reasoning="Product 1 matches best",
            confidence_hint=0.65,
        )
        adapter = _make_adapter_mock_for_exploration(analysis)

        await apply_reasoning_strategy(classification, request, adapter, engine)

        call_args = engine.search_hybrid.call_args[0][0]
        assert call_args.limit == 10

    @pytest.mark.usefixtures("_mock_settings")
    async def test_ambiguous_records_two_steps(self) -> None:
        """AC-5: Exploration records broad_search and comparative_analysis steps."""
        request = _make_request(description="comme la derniere fois")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()
        analysis = ComparativeAnalysisResult(
            best_match_indices=[0],
            reasoning="Product 1 matches best",
            confidence_hint=0.65,
        )
        adapter = _make_adapter_mock_for_exploration(analysis)

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert len(result.steps) == 2
        assert result.steps[0].step_name == "broad_search"
        assert result.steps[1].step_name == "comparative_analysis"

    @pytest.mark.usefixtures("_mock_settings")
    async def test_ambiguous_input_isolation_in_llm_call(self) -> None:
        """AC-5: Exploration LLM call uses input isolation delimiters."""
        request = _make_request(description="comme la derniere fois")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()

        mock_structured = MagicMock()
        analysis = ComparativeAnalysisResult(
            best_match_indices=[0],
            reasoning="Product 1 matches best",
            confidence_hint=0.65,
        )
        mock_structured.ainvoke = AsyncMock(return_value=analysis)
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        await apply_reasoning_strategy(classification, request, adapter, engine)

        call_args = mock_structured.ainvoke.call_args[0][0]
        human_msg = call_args[1]
        assert UNTRUSTED_QUOTE_START in human_msg.content
        assert UNTRUSTED_QUOTE_END in human_msg.content


class TestDeepAnalysisStrategy:
    """AC-3: Complex → Deep Analysis Strategy."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_complex_uses_deep_analysis_strategy(self) -> None:
        """AC-3: Complex request uses deep_analysis strategy."""
        request = _make_request(description="Tube inox avec certification ATEX et livraison urgente")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()
        enrichment = EnrichmentResult(
            enriched_description="Tube acier inoxydable certification ATEX livraison urgente",
            extracted_specifications=["ATEX certification", "Urgent delivery"],
            optimized_search_query="tube inox ATEX",
            flags=["requires_certification_check"],
        )
        evaluation = DeepEvaluationResult(
            evaluations=["Product 1: partial match — ATEX not confirmed"],
            overall_assessment="Medium match — ATEX certification needs verification",
            specification_gaps=["ATEX certification not confirmed for any product"],
        )
        adapter = _make_adapter_mock_for_deep(enrichment, evaluation)

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.strategy == "deep_analysis"
        assert result.enriched_request is not None
        assert result.enriched_request.line_items[0].description == enrichment.enriched_description

    @pytest.mark.usefixtures("_mock_settings")
    async def test_complex_uses_complex_model(self) -> None:
        """AC-3: Deep analysis strategy uses the complex model."""
        request = _make_request(description="Tube avec specs complexes")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()
        enrichment = EnrichmentResult(
            enriched_description="Enriched",
            extracted_specifications=[],
            optimized_search_query="tube specs",
        )
        evaluation = DeepEvaluationResult(
            evaluations=[],
            overall_assessment="OK",
        )
        adapter = _make_adapter_mock_for_deep(enrichment, evaluation)

        await apply_reasoning_strategy(classification, request, adapter, engine)

        adapter.get_model.assert_called_with("complex")

    @pytest.mark.usefixtures("_mock_settings")
    async def test_complex_uses_complex_search_limit(self) -> None:
        """AC-3: Deep analysis uses configured complex_search_limit."""
        request = _make_request(description="Tube avec specs complexes")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()
        enrichment = EnrichmentResult(
            enriched_description="Enriched",
            extracted_specifications=[],
            optimized_search_query="tube specs",
        )
        evaluation = DeepEvaluationResult(
            evaluations=[],
            overall_assessment="OK",
        )
        adapter = _make_adapter_mock_for_deep(enrichment, evaluation)

        await apply_reasoning_strategy(classification, request, adapter, engine)

        call_args = engine.search_hybrid.call_args[0][0]
        assert call_args.limit == 15

    @pytest.mark.usefixtures("_mock_settings")
    async def test_complex_records_three_steps(self) -> None:
        """AC-5: Deep analysis records context_enrichment, enriched_search, and deep_evaluation steps."""
        request = _make_request(description="Tube avec specs complexes")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()
        enrichment = EnrichmentResult(
            enriched_description="Enriched",
            extracted_specifications=[],
            optimized_search_query="tube specs",
        )
        evaluation = DeepEvaluationResult(
            evaluations=[],
            overall_assessment="OK",
        )
        adapter = _make_adapter_mock_for_deep(enrichment, evaluation)

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert len(result.steps) == 3
        assert result.steps[0].step_name == "context_enrichment"
        assert result.steps[1].step_name == "enriched_search"
        assert result.steps[2].step_name == "deep_evaluation"

    @pytest.mark.usefixtures("_mock_settings")
    async def test_complex_documents_reasoning_trace(self) -> None:
        """AC-3/AC-5: Deep analysis documents each step's outcome."""
        request = _make_request(description="Tube avec specs complexes")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()
        enrichment = EnrichmentResult(
            enriched_description="Enriched tube description",
            extracted_specifications=["ATEX"],
            optimized_search_query="tube ATEX",
            flags=["cert_check"],
        )
        evaluation = DeepEvaluationResult(
            evaluations=["Good match"],
            overall_assessment="Solid match",
            specification_gaps=["No gap"],
        )
        adapter = _make_adapter_mock_for_deep(enrichment, evaluation)

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        # Each step has non-empty outcome
        for step in result.steps:
            assert step.outcome
            assert step.duration_ms >= 0

    @pytest.mark.usefixtures("_mock_settings")
    async def test_complex_input_isolation_in_both_llm_calls(self) -> None:
        """AC-5: Deep analysis LLM calls (enrichment + evaluation) both use input isolation."""
        request = _make_request(description="Tube avec specs complexes")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()

        enrichment_structured = MagicMock()
        enrichment = EnrichmentResult(
            enriched_description="Enriched",
            extracted_specifications=[],
            optimized_search_query="tube specs",
        )
        enrichment_structured.ainvoke = AsyncMock(return_value=enrichment)

        eval_structured = MagicMock()
        evaluation = DeepEvaluationResult(
            evaluations=[],
            overall_assessment="OK",
        )
        eval_structured.ainvoke = AsyncMock(return_value=evaluation)

        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(
            side_effect=[enrichment_structured, eval_structured],
        )
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        await apply_reasoning_strategy(classification, request, adapter, engine)

        # Enrichment call uses input isolation
        enrichment_msgs = enrichment_structured.ainvoke.call_args[0][0]
        assert UNTRUSTED_QUOTE_START in enrichment_msgs[1].content
        assert UNTRUSTED_QUOTE_END in enrichment_msgs[1].content

        # Evaluation call uses input isolation
        eval_msgs = eval_structured.ainvoke.call_args[0][0]
        assert UNTRUSTED_QUOTE_START in eval_msgs[1].content
        assert UNTRUSTED_QUOTE_END in eval_msgs[1].content


class TestOutOfScopePassthrough:
    """AC-4: Out-of-scope Passthrough."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_out_of_scope_skips_reasoning(self) -> None:
        """AC-4: Out-of-scope returns immediately with empty result."""
        request = _make_request(description="Je cherche un plombier")
        classification = _make_classification(complexity="out_of_scope")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.strategy == "out_of_scope_skip"
        assert len(result.search_result.results) == 0
        engine.search_hybrid.assert_not_called()
        adapter.get_model.assert_not_called()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_out_of_scope_records_skip_step(self) -> None:
        """AC-5: Out-of-scope records a skip reasoning step."""
        request = _make_request(description="Je cherche un plombier")
        classification = _make_classification(complexity="out_of_scope")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert len(result.steps) == 1
        assert result.steps[0].step_name == "skip"


class TestReasoningTrace:
    """AC-5: Reasoning trace completeness."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_all_steps_have_required_fields(self) -> None:
        """AC-5: Every reasoning step has step_name, duration, and outcome."""
        request = _make_request()
        classification = _make_classification(complexity="simple")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        for step in result.steps:
            assert step.step_name
            assert step.description
            assert step.duration_ms >= 0
            assert step.outcome

    @pytest.mark.usefixtures("_mock_settings")
    async def test_reasoning_duration_populated(self) -> None:
        """AC-5: Overall reasoning_duration_ms is populated."""
        request = _make_request()
        classification = _make_classification(complexity="simple")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.reasoning_duration_ms >= 0


class TestTimeoutFallback:
    """Timeout/error → fallback to direct_match."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_falls_back_to_direct_match_on_timeout(self) -> None:
        """Timeout during exploration falls back to direct_match."""
        request = _make_request(description="comme la derniere fois")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.strategy == "direct_match"
        assert any(s.step_name == "fallback" for s in result.steps)
        assert any(s.step_name == "search" for s in result.steps)

    @pytest.mark.usefixtures("_mock_settings")
    async def test_falls_back_to_direct_match_on_adapter_error(self) -> None:
        """AdapterError during deep analysis falls back to direct_match."""
        request = _make_request(description="Tube complexe")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=AdapterError("API down"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.strategy == "direct_match"
        assert any(s.step_name == "fallback" for s in result.steps)

    @pytest.mark.usefixtures("_mock_settings")
    async def test_falls_back_to_direct_match_on_llm_timeout_error(self) -> None:
        """LLMTimeoutError falls back to direct_match."""
        request = _make_request(description="Tube ambigu")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=LLMTimeoutError("LLM timeout"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        assert result.strategy == "direct_match"

    @pytest.mark.usefixtures("_mock_settings")
    async def test_fallback_records_error_in_step(self) -> None:
        """Fallback step contains the error reason."""
        request = _make_request(description="comme la derniere fois")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured
        adapter = MagicMock()
        adapter.get_model.return_value = mock_model

        result = await apply_reasoning_strategy(classification, request, adapter, engine)

        fallback_step = next(s for s in result.steps if s.step_name == "fallback")
        assert "TimeoutError" in fallback_step.description
        assert "timed out" in fallback_step.description


class TestModelSelection:
    """Test that strategies use the correct LLM model."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_simple_does_not_call_get_model(self) -> None:
        """Simple strategy does not call get_model at all."""
        request = _make_request()
        classification = _make_classification(complexity="simple")
        engine = _make_search_engine_mock()
        adapter = MagicMock()

        await apply_reasoning_strategy(classification, request, adapter, engine)

        adapter.get_model.assert_not_called()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_ambiguous_uses_complex_model(self) -> None:
        """Ambiguous strategy calls get_model('complex')."""
        request = _make_request(description="ambigu")
        classification = _make_classification(complexity="ambiguous")
        engine = _make_search_engine_mock()
        analysis = ComparativeAnalysisResult(
            best_match_indices=[0],
            reasoning="OK",
            confidence_hint=0.6,
        )
        adapter = _make_adapter_mock_for_exploration(analysis)

        await apply_reasoning_strategy(classification, request, adapter, engine)

        adapter.get_model.assert_called_with("complex")

    @pytest.mark.usefixtures("_mock_settings")
    async def test_complex_uses_complex_model(self) -> None:
        """Complex strategy calls get_model('complex')."""
        request = _make_request(description="complexe")
        classification = _make_classification(complexity="complex")
        engine = _make_search_engine_mock()
        enrichment = EnrichmentResult(
            enriched_description="E",
            extracted_specifications=[],
            optimized_search_query="q",
        )
        evaluation = DeepEvaluationResult(
            evaluations=[],
            overall_assessment="OK",
        )
        adapter = _make_adapter_mock_for_deep(enrichment, evaluation)

        await apply_reasoning_strategy(classification, request, adapter, engine)

        adapter.get_model.assert_called_with("complex")


class TestReasoningStepDTO:
    """Unit tests for ReasoningStep DTO."""

    def test_reasoning_step_fields(self) -> None:
        step = ReasoningStep(
            step_name="search",
            description="Search executed",
            duration_ms=150,
            outcome="3 results found",
        )
        assert step.step_name == "search"
        assert step.duration_ms == 150


class TestReasoningResultDTO:
    """Unit tests for ReasoningResult DTO."""

    def test_reasoning_result_with_empty_steps(self) -> None:
        search_result = _make_search_result(n_results=0)
        result = ReasoningResult(
            strategy="out_of_scope_skip",
            steps=[],
            search_result=search_result,
        )
        assert result.strategy == "out_of_scope_skip"
        assert result.enriched_request is None
        assert result.reasoning_duration_ms == 0

    def test_reasoning_result_with_enriched_request(self) -> None:
        search_result = _make_search_result()
        enriched = _make_request(description="Enriched")
        result = ReasoningResult(
            strategy="deep_analysis",
            steps=[],
            enriched_request=enriched,
            search_result=search_result,
            reasoning_duration_ms=500,
        )
        assert result.enriched_request is not None
        assert result.reasoning_duration_ms == 500
