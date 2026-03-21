"""Unit tests for the self-review node."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest

from quote_agent.agent.nodes.reasoning_strategy import ReasoningResult, ReasoningStep
from quote_agent.agent.nodes.self_reviewer import (
    CoherenceCheckResult,
    IntegrityCheckResult,
    ValidationStep,
    self_review,
)
from quote_agent.exceptions import AdapterError, LLMTimeoutError
from quote_agent.search.models import ScoredProduct, SearchResult
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem

UUID_1 = uuid.UUID("00000000-0000-0000-0000-000000000001")
UUID_2 = uuid.UUID("00000000-0000-0000-0000-000000000002")
UUID_FAKE = uuid.UUID("00000000-0000-0000-0000-0000000000ff")


def _make_request(
    *,
    description: str = "Tube inox 304L DN50",
    quantity: float | None = 10.0,
    reference: str | None = "REF-001",
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
        raw_text=description,
    )


def _make_search_result(
    product_ids: list[uuid.UUID] | None = None,
) -> SearchResult:
    """Build a SearchResult with the given product IDs."""
    ids = product_ids or [UUID_1, UUID_2]
    return SearchResult(
        results=[
            ScoredProduct(
                product_id=pid,
                reference=f"REF-{i + 1:03d}",
                name=f"Product {i + 1}",
                category="Tubes",
                description=f"Product description {i + 1}",
                unit_price=45.0,
                score=0.92 - i * 0.05,
                rank=i + 1,
                match_source="hybrid",
            )
            for i, pid in enumerate(ids)
        ],
        total_found=len(ids),
        query="Tube inox 304L DN50",
        method="hybrid",
        duration_seconds=0.15,
    )


def _make_reasoning_result(
    product_ids: list[uuid.UUID] | None = None,
) -> ReasoningResult:
    """Build a ReasoningResult for testing."""
    return ReasoningResult(
        strategy="direct_match",
        steps=[
            ReasoningStep(
                step_name="search",
                description="Direct hybrid search with limit=5",
                duration_ms=150,
                outcome="2 results found",
            ),
        ],
        search_result=_make_search_result(product_ids),
        reasoning_duration_ms=200,
    )


def _make_adapter_mock(
    coherence: CoherenceCheckResult | None = None,
    integrity: IntegrityCheckResult | None = None,
    coherence_error: Exception | None = None,
    integrity_error: Exception | None = None,
) -> MagicMock:
    """Create a mock LLM adapter that returns different results per with_structured_output call."""
    if coherence is None:
        coherence = CoherenceCheckResult(
            is_coherent=True, mismatches=[], reasoning="All products match the request",
        )
    if integrity is None:
        integrity = IntegrityCheckResult(
            is_clean=True, anomalies=[], reasoning="No anomalies detected",
        )

    # Track which output model is being requested
    call_count = {"n": 0}
    responses = [coherence, integrity]
    errors = [coherence_error, integrity_error]

    def _make_structured(output_class: type) -> MagicMock:
        idx = call_count["n"]
        call_count["n"] += 1
        mock_structured = MagicMock()
        if idx < len(errors) and errors[idx] is not None:
            mock_structured.ainvoke = AsyncMock(side_effect=errors[idx])
        else:
            mock_structured.ainvoke = AsyncMock(return_value=responses[idx])
        return mock_structured

    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(side_effect=_make_structured)
    adapter = MagicMock()
    adapter.get_model = MagicMock(return_value=mock_model)
    return adapter


def _make_session_mock(
    existing_ids: list[uuid.UUID] | None = None,
) -> AsyncMock:
    """Create a mock AsyncSession that returns the given product IDs."""
    ids = existing_ids or [UUID_1, UUID_2]
    mock_result = MagicMock()
    mock_result.fetchall = MagicMock(return_value=[(pid,) for pid in ids])
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


@pytest.fixture()
def _mock_settings() -> Generator[None]:
    """Provide mock settings with self-review config."""
    mock_settings = MagicMock()
    mock_settings.self_review.timeout_seconds = 10
    mock_settings.self_review.max_quantity = 1_000_000
    mock_settings.self_review.min_quantity = 0
    with patch("quote_agent.config.get_settings", return_value=mock_settings):
        yield


class TestCatalogValidation:
    """AC-1: Catalog validation (anti-hallucination)."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_catalog_validation_passes_when_all_products_exist(self) -> None:
        """AC-1: All proposed products exist in catalog → approved."""
        reasoning = _make_reasoning_result([UUID_1, UUID_2])
        request = _make_request()
        adapter = _make_adapter_mock()
        session = _make_session_mock([UUID_1, UUID_2])

        result = await self_review(reasoning, request, adapter, session)

        catalog_step = next(s for s in result.steps if s.step_name == "catalog_validation")
        assert catalog_step.passed is True
        assert "verified" in catalog_step.detail.lower()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_catalog_validation_fails_when_hallucinated_product(self) -> None:
        """AC-1: Hallucinated product ID (not in DB) → rejected."""
        reasoning = _make_reasoning_result([UUID_1, UUID_FAKE])
        request = _make_request()
        adapter = _make_adapter_mock()
        # Only UUID_1 exists in DB
        session = _make_session_mock([UUID_1])

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        catalog_step = next(s for s in result.steps if s.step_name == "catalog_validation")
        assert catalog_step.passed is False
        assert "hallucinated" in catalog_step.detail.lower()


class TestQuantityPlausibility:
    """AC-2: Quantity plausibility validation."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_quantity_passes_when_normal_values(self) -> None:
        """AC-2: Normal quantities → pass."""
        reasoning = _make_reasoning_result()
        request = _make_request(quantity=10.0)
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        qty_step = next(s for s in result.steps if s.step_name == "quantity_plausibility")
        assert qty_step.passed is True

    @pytest.mark.usefixtures("_mock_settings")
    async def test_quantity_fails_when_zero(self) -> None:
        """AC-2: Zero quantity → fail."""
        reasoning = _make_reasoning_result()
        request = _make_request(quantity=0.0)
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        qty_step = next(s for s in result.steps if s.step_name == "quantity_plausibility")
        assert qty_step.passed is False
        assert "not positive" in qty_step.detail.lower()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_quantity_fails_when_negative(self) -> None:
        """AC-2: Negative quantity → fail."""
        reasoning = _make_reasoning_result()
        request = _make_request(quantity=-5.0)
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        qty_step = next(s for s in result.steps if s.step_name == "quantity_plausibility")
        assert qty_step.passed is False

    @pytest.mark.usefixtures("_mock_settings")
    async def test_quantity_fails_when_extreme(self) -> None:
        """AC-2: Quantity above max → fail."""
        reasoning = _make_reasoning_result()
        request = _make_request(quantity=2_000_000.0)
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        qty_step = next(s for s in result.steps if s.step_name == "quantity_plausibility")
        assert qty_step.passed is False
        assert "exceeds maximum" in qty_step.detail.lower()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_quantity_passes_when_none(self) -> None:
        """AC-2: None quantity (not specified) → pass."""
        reasoning = _make_reasoning_result()
        request = _make_request(quantity=None)
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        qty_step = next(s for s in result.steps if s.step_name == "quantity_plausibility")
        assert qty_step.passed is True


class TestCoherenceValidation:
    """AC-3: Coherence validation via LLM."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_coherence_passes_when_coherent_match(self) -> None:
        """AC-3: Coherent products → pass."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        coherence = CoherenceCheckResult(
            is_coherent=True, mismatches=[], reasoning="Products match request",
        )
        adapter = _make_adapter_mock(coherence=coherence)
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        coh_step = next(s for s in result.steps if s.step_name == "coherence_validation")
        assert coh_step.passed is True

    @pytest.mark.usefixtures("_mock_settings")
    async def test_coherence_fails_when_incoherent(self) -> None:
        """AC-3: Incoherent products → fail."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        coherence = CoherenceCheckResult(
            is_coherent=False,
            mismatches=["Product 1 is a valve, not a tube"],
            reasoning="Product type mismatch",
        )
        adapter = _make_adapter_mock(coherence=coherence)
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        coh_step = next(s for s in result.steps if s.step_name == "coherence_validation")
        assert coh_step.passed is False
        assert "incoherence" in coh_step.detail.lower()


class TestOutputIntegrity:
    """AC-4: Output integrity (prompt injection layer 3)."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_integrity_passes_when_clean_output(self) -> None:
        """AC-4: Clean output → pass."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        integrity = IntegrityCheckResult(
            is_clean=True, anomalies=[], reasoning="Output is clean",
        )
        adapter = _make_adapter_mock(integrity=integrity)
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        int_step = next(s for s in result.steps if s.step_name == "output_integrity")
        assert int_step.passed is True
        assert result.anomaly_flags == []

    @pytest.mark.usefixtures("_mock_settings")
    async def test_integrity_fails_when_injection_detected(self) -> None:
        """AC-4: Injection-influenced output → fail + anomaly flags."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        integrity = IntegrityCheckResult(
            is_clean=False,
            anomalies=["Product name contains suspicious instruction pattern"],
            reasoning="Potential prompt injection influence detected",
        )
        adapter = _make_adapter_mock(integrity=integrity)
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        int_step = next(s for s in result.steps if s.step_name == "output_integrity")
        assert int_step.passed is False
        assert len(result.anomaly_flags) == 1
        assert "suspicious" in result.anomaly_flags[0].lower()


class TestAggregateResult:
    """AC-5: Aggregate result — approved only if ALL steps pass."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_approved_when_all_steps_pass(self) -> None:
        """AC-5: All validations pass → approved=True."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is True
        assert result.failure_reasons == []
        assert all(s.passed for s in result.steps)

    @pytest.mark.usefixtures("_mock_settings")
    async def test_rejected_when_one_step_fails(self) -> None:
        """AC-5: One validation fails → approved=False."""
        reasoning = _make_reasoning_result()
        # Zero quantity fails plausibility
        request = _make_request(quantity=0.0)
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        assert len(result.failure_reasons) >= 1


class TestErrorFallback:
    """AC-5: Error handling — fail-safe (reject on error)."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_rejected_when_coherence_llm_timeout(self) -> None:
        """AC-5: LLM timeout during coherence → approved=False."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        adapter = _make_adapter_mock(coherence_error=TimeoutError("timed out"))
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        coh_step = next(s for s in result.steps if s.step_name == "coherence_validation")
        assert coh_step.passed is False
        assert "error" in coh_step.detail.lower()

    @pytest.mark.usefixtures("_mock_settings")
    async def test_rejected_when_integrity_adapter_error(self) -> None:
        """AC-5: AdapterError during integrity → approved=False."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        adapter = _make_adapter_mock(integrity_error=AdapterError("API down"))
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False
        int_step = next(s for s in result.steps if s.step_name == "output_integrity")
        assert int_step.passed is False

    @pytest.mark.usefixtures("_mock_settings")
    async def test_rejected_when_llm_timeout_error(self) -> None:
        """AC-5: LLMTimeoutError during coherence → approved=False."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        adapter = _make_adapter_mock(coherence_error=LLMTimeoutError("LLM timeout"))
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.approved is False


class TestValidationStepsDurations:
    """AC-6: Validation steps recorded with durations."""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_all_steps_have_durations(self) -> None:
        """AC-6: Every validation step records duration_ms."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert len(result.steps) == 4
        for step in result.steps:
            assert isinstance(step, ValidationStep)
            assert step.duration_ms >= 0
            assert step.step_name != ""
            assert step.detail != ""

    @pytest.mark.usefixtures("_mock_settings")
    async def test_review_duration_recorded(self) -> None:
        """AC-6: Overall review duration is recorded."""
        reasoning = _make_reasoning_result()
        request = _make_request()
        adapter = _make_adapter_mock()
        session = _make_session_mock()

        result = await self_review(reasoning, request, adapter, session)

        assert result.review_duration_ms >= 0
