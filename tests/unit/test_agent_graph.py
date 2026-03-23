"""Tests for the LangGraph agent graph — compilation, routing, and error handling."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.agent.graph import (
    _route_after_compliance,
    _route_after_router,
    build_agent_graph,
)
from quote_agent.agent.state import AgentState, create_initial_state
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem

# Patch targets — the modules where node functions are defined
_CLASSIFY = "quote_agent.agent.nodes.classifier.classify_request"
_REASON = "quote_agent.agent.nodes.reasoning_strategy.apply_reasoning_strategy"
_SCORE = "quote_agent.agent.nodes.confidence_scorer.score_confidence"
_ROUTE = "quote_agent.agent.nodes.router.route_by_confidence"
_REVIEW = "quote_agent.agent.nodes.self_reviewer.self_review"
_COMPLIANCE = "quote_agent.agent.nodes.compliance_checker.check_compliance"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_request(desc: str = "tubes inox 304L", qty: float = 100.0) -> ExtractedQuoteRequest:
    return ExtractedQuoteRequest(
        client_name="ACME Corp",
        client_identifier="ACME-001",
        line_items=[QuoteLineItem(description=desc, quantity=qty)],
        raw_text=desc,
    )


def _mock_classification(complexity: str = "simple", confidence: float = 0.95) -> MagicMock:
    mock = MagicMock()
    mock.complexity = complexity
    mock.confidence = confidence
    return mock


def _mock_reasoning() -> MagicMock:
    mock = MagicMock()
    mock.strategy = "direct_match"
    mock.reasoning_duration_ms = 123
    scored = MagicMock()
    scored.product_id = uuid.uuid4()
    scored.reference = "TUBE-304L-25"
    scored.name = "Tube Inox 304L Ø25"
    scored.unit_price = 15.50
    scored.rank = 1
    mock.search_result.results = [scored]
    return mock


def _mock_confidence(tier: str = "high", score: float = 0.92) -> MagicMock:
    mock = MagicMock()
    mock.overall_confidence = score
    mock.tier = tier
    mock.product_scores = []
    mock.reasoning = ["Good match"]
    mock.scoring_duration_ms = 50
    return mock


def _mock_routing(action: str = "proceed_to_draft") -> MagicMock:
    mock = MagicMock()
    mock.action = action
    mock.tier = "high" if action == "proceed_to_draft" else "medium"
    mock.confidence = 0.92
    mock.proposals = []
    mock.escalation_context = None
    return mock


def _mock_review(approved: bool = True) -> MagicMock:
    mock = MagicMock()
    mock.approved = approved
    mock.steps = []
    mock.failure_reasons = [] if approved else ["Product not in catalog"]
    mock.review_duration_ms = 80
    mock.anomaly_flags = []
    return mock


def _mock_compliance(compliant: bool = True, has_block: bool = False) -> MagicMock:
    mock = MagicMock()
    mock.is_compliant = compliant
    if has_block:
        flag = MagicMock()
        flag.severity = "block"
        flag.flag_type = "export_control"
        flag.detail = "Export controlled"
        flag.matched_term = "nuclear"
        mock.flags = [flag]
    else:
        mock.flags = []
    return mock


def _mock_draft_result() -> MagicMock:
    mock = MagicMock()
    mock.odoo_id = 42
    mock.order_reference = "SO042"
    mock.state = "draft"
    mock.line_count = 1
    return mock


def _make_settings_mock(**overrides: object) -> MagicMock:
    """Create a mock Settings with required sub-models for graph construction."""
    from quote_agent.config import NotificationBatchSettings

    batch = NotificationBatchSettings()
    mock = MagicMock(
        confidence_scoring=MagicMock(),
        notification_batch=batch,
    )
    for key, val in overrides.items():
        setattr(mock, key, val)
    return mock


def _make_session_factory() -> AsyncMock:
    """Create a mock async session factory that works as async context manager."""
    mock_session = AsyncMock()
    mock_row = MagicMock()
    mock_row.scalar_one_or_none.return_value = 99  # odoo_id
    mock_session.execute = AsyncMock(return_value=mock_row)

    factory = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


# ---------------------------------------------------------------------------
# Test: Conditional routing functions
# ---------------------------------------------------------------------------


class TestRouteAfterRouter:
    """AC-3: Conditional routing after router node."""

    def test_proceed_to_draft_routes_to_review(self) -> None:
        """AC-3: proceed_to_draft → review node."""
        state: AgentState = AgentState(routing_decision=_mock_routing("proceed_to_draft"))  # type: ignore[typeddict-item]
        assert _route_after_router(state) == "review"

    def test_generate_proposals_routes_to_notify_proposals(self) -> None:
        """AC-3 (5.2): generate_proposals → notify_proposals node."""
        state: AgentState = AgentState(routing_decision=_mock_routing("generate_proposals"))  # type: ignore[typeddict-item]
        assert _route_after_router(state) == "notify_proposals"

    def test_escalate_routes_to_notify_escalation(self) -> None:
        """AC-3 (5.3): escalate → notify_escalation node."""
        state: AgentState = AgentState(routing_decision=_mock_routing("escalate"))  # type: ignore[typeddict-item]
        assert _route_after_router(state) == "notify_escalation"

    def test_notify_out_of_scope_routes_to_notify_escalation(self) -> None:
        """AC-3 (5.3): notify_out_of_scope → notify_escalation node."""
        state: AgentState = AgentState(routing_decision=_mock_routing("notify_out_of_scope"))  # type: ignore[typeddict-item]
        assert _route_after_router(state) == "notify_escalation"

    def test_none_routing_decision_routes_to_notify_escalation(self) -> None:
        """AC-5 (5.5.5): Missing routing decision (fallback) → notify_escalation (not silent end)."""
        state: AgentState = AgentState(routing_decision=None)  # type: ignore[typeddict-item]
        assert _route_after_router(state) == "notify_escalation"


class TestRouteAfterCompliance:
    """AC-3, AC-5: Conditional routing after compliance check."""

    def test_approved_compliant_routes_to_draft(self) -> None:
        """AC-5: Approved review + compliant → draft."""
        state: AgentState = AgentState(  # type: ignore[typeddict-item]
            self_review=_mock_review(approved=True),
            compliance=_mock_compliance(compliant=True),
        )
        assert _route_after_compliance(state) == "draft"

    def test_rejected_review_routes_to_notify_rejection(self) -> None:
        """AC-1 (5.5.1): Rejected review → notify_rejection (not end)."""
        state: AgentState = AgentState(  # type: ignore[typeddict-item]
            self_review=_mock_review(approved=False),
            compliance=_mock_compliance(compliant=True),
        )
        assert _route_after_compliance(state) == "notify_rejection"

    def test_compliance_block_routes_to_notify_rejection(self) -> None:
        """AC-2 (5.5.1): Compliance block → notify_rejection (not end)."""
        state: AgentState = AgentState(  # type: ignore[typeddict-item]
            self_review=_mock_review(approved=True),
            compliance=_mock_compliance(compliant=False, has_block=True),
        )
        assert _route_after_compliance(state) == "notify_rejection"

    def test_none_review_routes_to_draft(self) -> None:
        """Edge case: missing review defaults to continuing."""
        state: AgentState = AgentState(  # type: ignore[typeddict-item]
            self_review=None,
            compliance=_mock_compliance(compliant=True),
        )
        assert _route_after_compliance(state) == "draft"

    def test_error_state_routes_to_notify_rejection(self) -> None:
        """AC-6 (5.5.5): Error state in compliance → notify_rejection (not draft)."""
        state: AgentState = AgentState(  # type: ignore[typeddict-item]
            error="compliance: LLM timeout",
            self_review=_mock_review(approved=True),
            compliance=None,
        )
        assert _route_after_compliance(state) == "notify_rejection"


# ---------------------------------------------------------------------------
# Test: Graph compilation
# ---------------------------------------------------------------------------


class TestGraphCompilation:
    """AC-1, AC-6: Graph compiles and has expected structure."""

    def test_graph_compiles_without_error(self) -> None:
        """AC-1: build_agent_graph returns a compiled graph."""
        graph = build_agent_graph(
            MagicMock(), _make_session_factory(), MagicMock(),
            _make_settings_mock(),
        )
        assert graph is not None

    def test_graph_is_invokable(self) -> None:
        """AC-6: Compiled graph has ainvoke method."""
        graph = build_agent_graph(
            MagicMock(), _make_session_factory(), MagicMock(),
            _make_settings_mock(),
        )
        assert hasattr(graph, "ainvoke")

    def test_notify_node_is_wired_after_draft(self) -> None:
        """AC-1 (5.1): notify node exists and sits between draft and END."""
        graph = build_agent_graph(
            MagicMock(), _make_session_factory(), MagicMock(),
            _make_settings_mock(),
        )
        node_names = list(graph.get_graph().nodes.keys())
        assert "notify" in node_names
        # notify should come after draft in the node list
        assert node_names.index("notify") > node_names.index("draft")

    def test_notify_proposals_node_is_wired(self) -> None:
        """AC-3 (5.2): notify_proposals node exists in the graph."""
        graph = build_agent_graph(
            MagicMock(), _make_session_factory(), MagicMock(),
            _make_settings_mock(),
        )
        node_names = list(graph.get_graph().nodes.keys())
        assert "notify_proposals" in node_names

    def test_notify_escalation_node_is_wired(self) -> None:
        """AC-3 (5.3): notify_escalation node exists in the graph."""
        graph = build_agent_graph(
            MagicMock(), _make_session_factory(), MagicMock(),
            _make_settings_mock(),
        )
        node_names = list(graph.get_graph().nodes.keys())
        assert "notify_escalation" in node_names

    def test_notify_rejection_node_is_wired(self) -> None:
        """AC-1 (5.5.1): notify_rejection node exists in the graph."""
        graph = build_agent_graph(
            MagicMock(), _make_session_factory(), MagicMock(),
            _make_settings_mock(),
        )
        node_names = list(graph.get_graph().nodes.keys())
        assert "notify_rejection" in node_names


# ---------------------------------------------------------------------------
# Test: Full graph execution paths
# ---------------------------------------------------------------------------


class TestGraphExecution:
    """AC-1, AC-3, AC-4, AC-5, AC-6: Full graph execution with mocked nodes."""

    @pytest.mark.asyncio
    async def test_proceed_to_draft_full_path(self) -> None:
        """AC-5, AC-6: High confidence → review → compliance → draft → notify → END."""
        request = _make_request()
        state = create_initial_state(request)

        classification = _mock_classification()
        reasoning = _mock_reasoning()
        confidence = _mock_confidence(tier="high", score=0.92)
        routing = _mock_routing("proceed_to_draft")
        review_result = _mock_review(approved=True)
        compliance_result = _mock_compliance(compliant=True)
        draft_result = _mock_draft_result()

        erp = AsyncMock()
        erp.create_draft_quote = AsyncMock(return_value=draft_result)

        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        mock_notif_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        mock_adapter = AsyncMock()
        mock_adapter.send_notification = AsyncMock(return_value=mock_notif_result)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=classification),
            patch(_REASON, new_callable=AsyncMock, return_value=reasoning),
            patch(_SCORE, new_callable=AsyncMock, return_value=confidence),
            patch(_ROUTE, return_value=routing),
            patch(_REVIEW, new_callable=AsyncMock, return_value=review_result),
            patch(_COMPLIANCE, new_callable=AsyncMock, return_value=compliance_result),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), erp,
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result["classification"] is classification
        assert result["reasoning"] is reasoning
        assert result["confidence"] is confidence
        assert result["routing_decision"] is routing
        assert result["self_review"] is review_result
        assert result["compliance"] is compliance_result
        assert result["draft_result"] is draft_result
        assert result["final_action"] == "proceed_to_draft"
        assert result.get("error") is None
        # Verify notify node actually executed
        assert result["notification_result"] is mock_notif_result
        assert result["current_node"] == "notify"
        mock_adapter.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_proposals_routes_through_notify_proposals(self) -> None:
        """AC-3 (5.2): generate_proposals → notify_proposals → END (no review/draft)."""
        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        request = _make_request()
        state = create_initial_state(request)

        classification = _mock_classification("ambiguous")
        reasoning = _mock_reasoning()
        confidence = _mock_confidence(tier="medium", score=0.65)
        routing = _mock_routing("generate_proposals")

        mock_notif_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        mock_adapter = AsyncMock()
        mock_adapter.send_notification = AsyncMock(return_value=mock_notif_result)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=classification),
            patch(_REASON, new_callable=AsyncMock, return_value=reasoning),
            patch(_SCORE, new_callable=AsyncMock, return_value=confidence),
            patch(_ROUTE, return_value=routing),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), MagicMock(),
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result["routing_decision"] is routing
        assert result["final_action"] == "generate_proposals"
        assert result.get("self_review") is None
        assert result.get("compliance") is None
        assert result.get("draft_result") is None
        # AC-3: Notification was sent via notify_proposals node
        assert result["current_node"] == "notify_proposals"
        mock_adapter.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_escalate_routes_through_notify_escalation(self) -> None:
        """AC-3 (5.3): escalate → notify_escalation → END (no review/draft)."""
        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        request = _make_request()
        state = create_initial_state(request)

        classification = _mock_classification("complex")
        reasoning = _mock_reasoning()
        confidence = _mock_confidence(tier="low", score=0.3)
        routing = _mock_routing("escalate")

        mock_notif_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        mock_adapter = AsyncMock()
        mock_adapter.send_notification = AsyncMock(return_value=mock_notif_result)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=classification),
            patch(_REASON, new_callable=AsyncMock, return_value=reasoning),
            patch(_SCORE, new_callable=AsyncMock, return_value=confidence),
            patch(_ROUTE, return_value=routing),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), MagicMock(),
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result["final_action"] == "escalate"
        assert result.get("self_review") is None
        assert result.get("draft_result") is None
        # AC-3: Notification was sent via notify_escalation node
        assert result["current_node"] == "notify_escalation"
        mock_adapter.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_out_of_scope_routes_through_notify_escalation(self) -> None:
        """AC-3 (5.3): notify_out_of_scope → notify_escalation → END."""
        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        request = _make_request()
        state = create_initial_state(request)

        classification = _mock_classification("out_of_scope")
        reasoning = _mock_reasoning()
        confidence = _mock_confidence(tier="low", score=0.1)
        routing = _mock_routing("notify_out_of_scope")

        mock_notif_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        mock_adapter = AsyncMock()
        mock_adapter.send_notification = AsyncMock(return_value=mock_notif_result)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=classification),
            patch(_REASON, new_callable=AsyncMock, return_value=reasoning),
            patch(_SCORE, new_callable=AsyncMock, return_value=confidence),
            patch(_ROUTE, return_value=routing),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), MagicMock(),
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result["final_action"] == "notify_out_of_scope"
        assert result.get("draft_result") is None
        # AC-3: Notification was sent via notify_escalation node
        assert result["current_node"] == "notify_escalation"
        mock_adapter.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_rejection_sends_notification(self) -> None:
        """AC-1 (5.5.1): Self-review rejected → notify_rejection → END (no draft, notification sent)."""
        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        request = _make_request()
        state = create_initial_state(request)

        mock_notif_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        mock_adapter = AsyncMock()
        mock_adapter.send_notification = AsyncMock(return_value=mock_notif_result)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=_mock_classification()),
            patch(_REASON, new_callable=AsyncMock, return_value=_mock_reasoning()),
            patch(_SCORE, new_callable=AsyncMock, return_value=_mock_confidence()),
            patch(_ROUTE, return_value=_mock_routing("proceed_to_draft")),
            patch(_REVIEW, new_callable=AsyncMock, return_value=_mock_review(approved=False)),
            patch(_COMPLIANCE, new_callable=AsyncMock, return_value=_mock_compliance(compliant=True)),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), MagicMock(),
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result["self_review"].approved is False
        assert result.get("draft_result") is None
        assert result["final_action"] == "review_rejected"
        assert result["notification_result"] is not None
        assert result["current_node"] == "notify_rejection"
        mock_adapter.send_notification.assert_called_once()
        payload = mock_adapter.send_notification.call_args[0][0]
        assert payload.card_type == "escalation"

    @pytest.mark.asyncio
    async def test_compliance_block_sends_notification(self) -> None:
        """AC-2 (5.5.1): Compliance block → notify_rejection → END (no draft, notification sent)."""
        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        request = _make_request()
        state = create_initial_state(request)

        mock_notif_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        mock_adapter = AsyncMock()
        mock_adapter.send_notification = AsyncMock(return_value=mock_notif_result)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=_mock_classification()),
            patch(_REASON, new_callable=AsyncMock, return_value=_mock_reasoning()),
            patch(_SCORE, new_callable=AsyncMock, return_value=_mock_confidence()),
            patch(_ROUTE, return_value=_mock_routing("proceed_to_draft")),
            patch(_REVIEW, new_callable=AsyncMock, return_value=_mock_review(approved=True)),
            patch(_COMPLIANCE, new_callable=AsyncMock, return_value=_mock_compliance(compliant=False, has_block=True)),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), MagicMock(),
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result.get("draft_result") is None
        assert result["final_action"] == "compliance_blocked"
        assert result["notification_result"] is not None
        assert result["current_node"] == "notify_rejection"
        mock_adapter.send_notification.assert_called_once()
        payload = mock_adapter.send_notification.call_args[0][0]
        assert payload.card_type == "escalation"


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------


class TestGraphErrorHandling:
    """AC-4: Error handling in graph nodes."""

    @pytest.mark.asyncio
    async def test_classify_failure_routes_to_escalation(self) -> None:
        """AC-4 (5.5.5): Classification failure → error → route fallback → notify_escalation (not silent END)."""
        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        request = _make_request()
        state = create_initial_state(request)

        mock_notif_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        mock_adapter = AsyncMock()
        mock_adapter.send_notification = AsyncMock(return_value=mock_notif_result)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, side_effect=RuntimeError("LLM timeout")),
            patch("quote_agent.adapters.notification.get_notification_adapter", return_value=mock_adapter),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), MagicMock(),
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result.get("error") is not None
        assert "classify" in result["error"]
        assert "LLM timeout" in result["error"]
        # After fix: error path routes to escalation, not silent END
        assert result["current_node"] == "notify_escalation"
        assert result["final_action"] == "routing_fallback"
        # Notification was sent with fallback context
        mock_adapter.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_reason_failure_sets_error(self) -> None:
        """AC-4: Reasoning failure → error in state."""
        request = _make_request()
        state = create_initial_state(request)

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=_mock_classification()),
            patch(_REASON, new_callable=AsyncMock, side_effect=RuntimeError("Search unavailable")),
        ):
            graph = build_agent_graph(
                MagicMock(), _make_session_factory(), MagicMock(),
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result.get("error") is not None
        assert "reason" in result["error"]

    @pytest.mark.asyncio
    async def test_draft_fails_when_no_odoo_id(self) -> None:
        """AC-4, AC-5: Draft node sets error when product has no odoo_id."""
        request = _make_request()
        state = create_initial_state(request)

        # Session factory returns None for odoo_id
        session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_row = MagicMock()
        mock_row.scalar_one_or_none.return_value = None  # no odoo_id
        mock_session.execute = AsyncMock(return_value=mock_row)
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=mock_session)
        cm.__aexit__ = AsyncMock(return_value=False)
        session_factory.return_value = cm

        with (
            patch(_CLASSIFY, new_callable=AsyncMock, return_value=_mock_classification()),
            patch(_REASON, new_callable=AsyncMock, return_value=_mock_reasoning()),
            patch(_SCORE, new_callable=AsyncMock, return_value=_mock_confidence()),
            patch(_ROUTE, return_value=_mock_routing("proceed_to_draft")),
            patch(_REVIEW, new_callable=AsyncMock, return_value=_mock_review(approved=True)),
            patch(_COMPLIANCE, new_callable=AsyncMock, return_value=_mock_compliance(compliant=True)),
        ):
            erp = AsyncMock()
            graph = build_agent_graph(
                MagicMock(), session_factory, erp,
                _make_settings_mock(),
            )
            result = await graph.ainvoke(state)

        assert result.get("error") is not None
        assert "odoo_id" in result["error"]
        assert result.get("draft_result") is None
        erp.create_draft_quote.assert_not_called()
