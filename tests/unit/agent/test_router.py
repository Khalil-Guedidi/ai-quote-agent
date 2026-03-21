"""Unit tests for the tier routing node."""

from quote_agent.agent.nodes.classifier import ClassificationResult
from quote_agent.agent.nodes.confidence_scorer import ConfidenceResult, ProductConfidence
from quote_agent.agent.nodes.router import route_by_confidence
from quote_agent.config import ConfidenceScoringSettings


def _make_classification(
    complexity: str = "simple",
    confidence: float = 0.95,
) -> ClassificationResult:
    """Build a ClassificationResult for router tests."""
    return ClassificationResult(
        complexity=complexity,  # type: ignore[arg-type]
        reasons=["Test reason"],
        confidence=confidence,
        classification_duration_ms=50,
    )


def _make_product_scores(count: int = 3) -> list[ProductConfidence]:
    """Build a list of product confidence scores."""
    scores = []
    for i in range(count):
        scores.append(
            ProductConfidence(
                product_id=f"00000000-0000-0000-0000-00000000000{i + 1}",
                reference=f"REF-{i + 1:03d}",
                name=f"Product {i + 1}",
                confidence=round(0.90 - i * 0.15, 2),
                match_quality=f"Match quality for product {i + 1}",
                rank=i + 1,
            )
        )
    return scores


def _make_confidence_result(
    overall: float = 0.90,
    tier: str = "high",
    product_scores: list[ProductConfidence] | None = None,
) -> ConfidenceResult:
    """Build a ConfidenceResult for router tests."""
    return ConfidenceResult(
        overall_confidence=overall,
        tier=tier,  # type: ignore[arg-type]
        product_scores=product_scores or _make_product_scores(),
        reasoning=["Test reasoning"],
        scoring_duration_ms=100,
    )


def _default_settings() -> ConfidenceScoringSettings:
    """Return default ConfidenceScoringSettings."""
    return ConfidenceScoringSettings()


class TestHighConfidenceRouting:
    """AC-1: High confidence (>0.85) → proceed_to_draft."""

    def test_routes_to_draft_when_high_confidence(self) -> None:
        result = _make_confidence_result(overall=0.90)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.action == "proceed_to_draft"
        assert decision.tier == "high"
        assert decision.confidence == 0.90


class TestMediumConfidenceRouting:
    """AC-2: Medium confidence (0.50-0.85) → generate_proposals with 2-5 proposals."""

    def test_routes_to_proposals_when_medium_confidence(self) -> None:
        result = _make_confidence_result(overall=0.70)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.action == "generate_proposals"
        assert decision.tier == "medium"
        assert decision.confidence == 0.70
        assert len(decision.proposals) >= 1


class TestLowConfidenceRouting:
    """AC-3: Low confidence (<0.50) → escalate with EscalationContext."""

    def test_routes_to_escalate_when_low_confidence(self) -> None:
        result = _make_confidence_result(overall=0.30)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.action == "escalate"
        assert decision.tier == "low"
        assert decision.confidence == 0.30
        assert decision.escalation_context is not None


class TestOutOfScopeRouting:
    """AC-4: Out-of-scope → notify_out_of_scope regardless of confidence."""

    def test_routes_to_notify_when_out_of_scope(self) -> None:
        result = _make_confidence_result(overall=0.95)
        classification = _make_classification(complexity="out_of_scope")

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.action == "notify_out_of_scope"
        assert decision.tier == "out_of_scope"

    def test_routes_to_notify_when_out_of_scope_low_confidence(self) -> None:
        result = _make_confidence_result(overall=0.10)
        classification = _make_classification(complexity="out_of_scope")

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.action == "notify_out_of_scope"
        assert decision.tier == "out_of_scope"


class TestProposalsSorted:
    """AC-2: Proposals are sorted by confidence descending, limited to max_proposals."""

    def test_proposals_sorted_descending_when_medium(self) -> None:
        scores = [
            ProductConfidence(
                product_id="id-1", reference="R1", name="P1",
                confidence=0.60, match_quality="ok", rank=1,
            ),
            ProductConfidence(
                product_id="id-2", reference="R2", name="P2",
                confidence=0.80, match_quality="good", rank=2,
            ),
            ProductConfidence(
                product_id="id-3", reference="R3", name="P3",
                confidence=0.70, match_quality="fair", rank=3,
            ),
        ]
        result = _make_confidence_result(overall=0.70, product_scores=scores)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.proposals[0].confidence >= decision.proposals[1].confidence

    def test_proposals_limited_to_max_proposals(self) -> None:
        scores = [
            ProductConfidence(
                product_id=f"id-{i}", reference=f"R{i}", name=f"P{i}",
                confidence=round(0.80 - i * 0.05, 2), match_quality="ok", rank=i,
            )
            for i in range(8)
        ]
        result = _make_confidence_result(overall=0.70, product_scores=scores)
        classification = _make_classification()
        settings = ConfidenceScoringSettings(max_proposals=5)

        decision = route_by_confidence(result, classification, settings)

        assert len(decision.proposals) <= 5


class TestProposalsMinCount:
    """AC-2: If fewer than min_proposals available, include all."""

    def test_includes_all_when_fewer_than_min_proposals(self) -> None:
        scores = [
            ProductConfidence(
                product_id="id-1", reference="R1", name="P1",
                confidence=0.70, match_quality="ok", rank=1,
            ),
        ]
        result = _make_confidence_result(overall=0.70, product_scores=scores)
        classification = _make_classification()
        settings = ConfidenceScoringSettings(min_proposals=2)

        decision = route_by_confidence(result, classification, settings)

        assert len(decision.proposals) == 1


class TestEscalationContext:
    """AC-3: Escalation context includes understood, uncertain, suggested_next_steps."""

    def test_escalation_context_populated_when_low(self) -> None:
        result = _make_confidence_result(overall=0.30)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.escalation_context is not None
        assert decision.escalation_context.understood
        assert decision.escalation_context.uncertain
        assert len(decision.escalation_context.suggested_next_steps) >= 1


class TestCustomThresholds:
    """AC-1: Custom thresholds via settings override."""

    def test_custom_high_threshold(self) -> None:
        settings = ConfidenceScoringSettings(high_threshold=0.90)
        result = _make_confidence_result(overall=0.88)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, settings)

        # 0.88 <= 0.90 threshold → medium, not high
        assert decision.action == "generate_proposals"
        assert decision.tier == "medium"

    def test_custom_low_threshold(self) -> None:
        settings = ConfidenceScoringSettings(low_threshold=0.60)
        result = _make_confidence_result(overall=0.55)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, settings)

        # 0.55 < 0.60 threshold → escalate
        assert decision.action == "escalate"
        assert decision.tier == "low"


class TestBoundaryValues:
    """AC-1: Boundary values — exactly 0.85 → medium, exactly 0.50 → medium."""

    def test_exactly_high_threshold_routes_to_medium(self) -> None:
        result = _make_confidence_result(overall=0.85)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        # Exactly 0.85 is NOT > 0.85, so it should be medium
        assert decision.action == "generate_proposals"
        assert decision.tier == "medium"

    def test_exactly_low_threshold_routes_to_medium(self) -> None:
        result = _make_confidence_result(overall=0.50)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        # Exactly 0.50 is >= 0.50, so it should be medium
        assert decision.action == "generate_proposals"
        assert decision.tier == "medium"

    def test_just_below_low_threshold_routes_to_escalate(self) -> None:
        result = _make_confidence_result(overall=0.49)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.action == "escalate"
        assert decision.tier == "low"

    def test_just_above_high_threshold_routes_to_draft(self) -> None:
        result = _make_confidence_result(overall=0.86)
        classification = _make_classification()

        decision = route_by_confidence(result, classification, _default_settings())

        assert decision.action == "proceed_to_draft"
        assert decision.tier == "high"
