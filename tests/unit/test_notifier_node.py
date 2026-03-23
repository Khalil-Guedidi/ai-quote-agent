"""Tests for the notify_quote_ready node — success, failure, and missing draft_result."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from quote_agent.adapters.notification.models import NotificationResult
from quote_agent.agent.nodes.notifier import (
    notify_escalation,
    notify_multi_proposal,
    notify_quote_ready,
    notify_rejection,
)
from quote_agent.agent.state import AgentState, create_initial_state
from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem


def _make_state(
    *,
    with_draft: bool = True,
    confidence_score: float = 0.92,
) -> AgentState:
    """Build a realistic AgentState for notifier tests."""
    request = ExtractedQuoteRequest(
        client_name="Durand",
        client_identifier="DUR-001",
        line_items=[QuoteLineItem(description="Tube Inox 304L", quantity=100.0)],
        raw_text="Tube Inox 304L",
    )
    state = create_initial_state(request)

    if with_draft:
        draft = MagicMock()
        draft.odoo_id = 42
        draft.order_reference = "SO042"
        state["draft_result"] = draft

    confidence = MagicMock()
    confidence.overall_confidence = confidence_score
    state["confidence"] = confidence

    return state  # type: ignore[return-value]


class TestNotifyQuoteReadySuccess:
    """AC-1, AC-4: Notification sent successfully after draft creation."""

    @pytest.mark.asyncio
    async def test_sends_notification_with_correct_payload(self) -> None:
        """AC-4: notify node calls send_notification with quote-ready payload."""
        state = _make_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_quote_ready(state, adapter)

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "quote-ready"
        assert payload.data["client"] == "Durand"
        assert payload.data["product"] == "Tube Inox 304L"
        assert payload.data["quantity"] == "100.0"
        assert payload.data["confidence_pct"] == "92"
        assert "/erp/sale-order/42" in payload.data["erp_url"]
        assert "/erp/sale-order" in payload.data["erp_url"] or payload.data["erp_url"].endswith("/erp/sale-orders")

    @pytest.mark.asyncio
    async def test_returns_notification_result_in_state(self) -> None:
        """AC-4: Successful notification result stored in state."""
        state = _make_state()
        expected_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(return_value=expected_result)

        result = await notify_quote_ready(state, adapter)

        assert result["notification_result"] is expected_result
        assert result["current_node"] == "notify"


class TestNotifyQuoteReadyFailure:
    """AC-3: Notification failure must not block the pipeline."""

    @pytest.mark.asyncio
    async def test_adapter_error_does_not_set_state_error(self) -> None:
        """AC-3: Notification send failure → state has no error key."""
        state = _make_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(
                success=False, error="Connection refused", timestamp=datetime.now(tz=UTC)
            )
        )

        result = await notify_quote_ready(state, adapter)

        assert "error" not in result
        assert result["notification_result"] is not None
        assert result["notification_result"].success is False
        assert result["current_node"] == "notify"

    @pytest.mark.asyncio
    async def test_adapter_exception_does_not_propagate(self) -> None:
        """AC-3: Exception from adapter is caught, not propagated."""
        state = _make_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(side_effect=RuntimeError("Network error"))

        result = await notify_quote_ready(state, adapter)

        assert "error" not in result
        assert result["notification_result"] is None
        assert result["current_node"] == "notify"


class TestNotifyQuoteReadyMissingDraft:
    """Edge case: no draft_result in state."""

    @pytest.mark.asyncio
    async def test_skips_notification_when_no_draft_result(self) -> None:
        """AC-3: Missing draft_result → graceful skip, no error."""
        state = _make_state(with_draft=False)
        adapter = AsyncMock()

        result = await notify_quote_ready(state, adapter)

        adapter.send_notification.assert_not_called()
        assert result["notification_result"] is None
        assert result["current_node"] == "notify"
        assert "error" not in result


# --- notify_multi_proposal() Tests ---


def _make_proposal_state(
    *,
    with_routing: bool = True,
    num_proposals: int = 3,
) -> AgentState:
    """Build a realistic AgentState for multi-proposal notifier tests."""
    request = ExtractedQuoteRequest(
        client_name="Durand",
        client_identifier="DUR-001",
        line_items=[QuoteLineItem(description="Tube Inox DN50", quantity=50.0)],
        raw_text="Tube Inox DN50",
    )
    state = create_initial_state(request)

    if with_routing:
        proposals = []
        for i in range(num_proposals):
            p = MagicMock()
            p.name = f"Product {i + 1}"
            p.reference = f"REF-{i + 1:03d}"
            p.confidence = 0.78 - (i * 0.15)
            p.match_quality = f"Match quality for product {i + 1}"
            proposals.append(p)

        routing = MagicMock()
        routing.action = "generate_proposals"
        routing.proposals = proposals
        state["routing_decision"] = routing

    return state  # type: ignore[return-value]


class TestNotifyMultiProposalSuccess:
    """AC-3: Multi-proposal notification sent for medium-confidence routing."""

    @pytest.mark.asyncio
    async def test_sends_notification_with_multi_proposal_payload(self) -> None:
        """AC-3: notify_multi_proposal calls send_notification with multi-proposal payload."""
        state = _make_proposal_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_multi_proposal(state, adapter)

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "multi-proposal"
        assert payload.data["client"] == "Durand"
        assert len(payload.data["proposals"]) == 3
        assert payload.data["proposals"][0]["name"] == "Product 1"
        assert payload.data["proposals"][0]["confidence_pct"] == "78"
        assert "/erp/sale-order" in payload.data["erp_url"] or payload.data["erp_url"].endswith("/erp/sale-orders")
        assert payload.data["erp_url"].endswith("/erp/sale-orders")

    @pytest.mark.asyncio
    async def test_returns_notification_result_in_state(self) -> None:
        """AC-3: Successful notification result stored in state."""
        state = _make_proposal_state()
        expected_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(return_value=expected_result)

        result = await notify_multi_proposal(state, adapter)

        assert result["notification_result"] is expected_result
        assert result["current_node"] == "notify_proposals"

    @pytest.mark.asyncio
    async def test_message_includes_proposal_count(self) -> None:
        """AC-1: Message text includes the number of proposals."""
        state = _make_proposal_state(num_proposals=2)
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_multi_proposal(state, adapter)

        payload = adapter.send_notification.call_args[0][0]
        assert "2 options" in payload.message


class TestNotifyMultiProposalFailure:
    """AC-4: Notification failure must not block the pipeline (fire-and-forget)."""

    @pytest.mark.asyncio
    async def test_adapter_error_does_not_set_state_error(self) -> None:
        """AC-4: Notification send failure → state has no error key."""
        state = _make_proposal_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(
                success=False, error="Connection refused", timestamp=datetime.now(tz=UTC)
            )
        )

        result = await notify_multi_proposal(state, adapter)

        assert "error" not in result
        assert result["notification_result"] is not None
        assert result["notification_result"].success is False
        assert result["current_node"] == "notify_proposals"

    @pytest.mark.asyncio
    async def test_adapter_exception_does_not_propagate(self) -> None:
        """AC-4: Exception from adapter is caught, not propagated."""
        state = _make_proposal_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(side_effect=RuntimeError("Network error"))

        result = await notify_multi_proposal(state, adapter)

        assert "error" not in result
        assert result["notification_result"] is None
        assert result["current_node"] == "notify_proposals"


class TestNotifyMultiProposalMissingRouting:
    """Edge case: no routing_decision in state."""

    @pytest.mark.asyncio
    async def test_skips_notification_when_no_routing_decision(self) -> None:
        """AC-4: Missing routing_decision → graceful skip, no error."""
        state = _make_proposal_state(with_routing=False)
        adapter = AsyncMock()

        result = await notify_multi_proposal(state, adapter)

        adapter.send_notification.assert_not_called()
        assert result["notification_result"] is None
        assert result["current_node"] == "notify_proposals"
        assert "error" not in result


# --- notify_escalation() Tests ---


def _make_escalation_state(
    *,
    with_routing: bool = True,
    with_escalation_context: bool = True,
    with_classification: bool = True,
) -> AgentState:
    """Build a realistic AgentState for escalation notifier tests."""
    request = ExtractedQuoteRequest(
        client_name="Durand",
        client_identifier="DUR-001",
        line_items=[QuoteLineItem(description="Pièce spéciale custom", quantity=10.0)],
        raw_text="Pièce spéciale custom",
    )
    state = create_initial_state(request)

    if with_classification:
        classification = MagicMock()
        classification.reasons = ["Demande complexe", "Produit non standard"]
        state["classification"] = classification

    if with_routing:
        routing = MagicMock()
        routing.action = "escalate"
        routing.confidence = 0.28

        if with_escalation_context:
            escalation_ctx = MagicMock()
            escalation_ctx.understood = "Client demande des pièces spéciales"
            escalation_ctx.uncertain = "Spécifications exactes non fournies"
            escalation_ctx.suggested_next_steps = [
                "Demander des precisions au client",
                "Verifier les references",
            ]
            routing.escalation_context = escalation_ctx
        else:
            routing.escalation_context = None

        state["routing_decision"] = routing

    return state  # type: ignore[return-value]


class TestNotifyEscalationSuccess:
    """AC-3: Escalation notification sent for low-confidence routing."""

    @pytest.mark.asyncio
    async def test_sends_notification_with_escalation_payload(self) -> None:
        """AC-1, AC-2: notify_escalation calls send_notification with escalation payload."""
        state = _make_escalation_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_escalation(state, adapter)

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "escalation"
        assert payload.data["client"] == "Durand"
        assert payload.data["understood"] == "Client demande des pièces spéciales"
        assert payload.data["uncertain"] == "Spécifications exactes non fournies"
        assert len(payload.data["suggested_next_steps"]) == 2
        assert payload.data["confidence_pct"] == "28"
        assert "/erp/sale-order" in payload.data["erp_url"] or payload.data["erp_url"].endswith("/erp/sale-orders")
        assert payload.data["erp_url"].endswith("/erp/sale-orders")

    @pytest.mark.asyncio
    async def test_returns_notification_result_in_state(self) -> None:
        """AC-3: Successful notification result stored in state."""
        state = _make_escalation_state()
        expected_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(return_value=expected_result)

        result = await notify_escalation(state, adapter)

        assert result["notification_result"] is expected_result
        assert result["current_node"] == "notify_escalation"

    @pytest.mark.asyncio
    async def test_message_includes_client_name(self) -> None:
        """AC-1: Message text includes the client name."""
        state = _make_escalation_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_escalation(state, adapter)

        payload = adapter.send_notification.call_args[0][0]
        assert "Durand" in payload.message
        assert "Celui-là est compliqué" in payload.message


class TestNotifyEscalationOutOfScope:
    """AC-3: Out-of-scope fallback when escalation_context is None."""

    @pytest.mark.asyncio
    async def test_builds_fallback_context_from_classification(self) -> None:
        """AC-2: out_of_scope with no escalation_context uses classification reasons."""
        state = _make_escalation_state(with_escalation_context=False)
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_escalation(state, adapter)

        payload = adapter.send_notification.call_args[0][0]
        assert "Demande complexe" in payload.data["understood"]
        assert "Produit non standard" in payload.data["understood"]
        assert "périmètre" in payload.data["uncertain"]
        assert len(payload.data["suggested_next_steps"]) == 2

    @pytest.mark.asyncio
    async def test_builds_fallback_without_classification(self) -> None:
        """AC-2: out_of_scope with no escalation_context and no classification uses default."""
        state = _make_escalation_state(with_escalation_context=False, with_classification=False)
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_escalation(state, adapter)

        payload = adapter.send_notification.call_args[0][0]
        assert payload.data["understood"] == "Demande classée hors périmètre"


class TestNotifyEscalationFailure:
    """AC-4: Notification failure must not block the pipeline (fire-and-forget)."""

    @pytest.mark.asyncio
    async def test_adapter_error_does_not_set_state_error(self) -> None:
        """AC-4: Notification send failure → state has no error key."""
        state = _make_escalation_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(
                success=False, error="Connection refused", timestamp=datetime.now(tz=UTC)
            )
        )

        result = await notify_escalation(state, adapter)

        assert "error" not in result
        assert result["notification_result"] is not None
        assert result["notification_result"].success is False
        assert result["current_node"] == "notify_escalation"

    @pytest.mark.asyncio
    async def test_adapter_exception_does_not_propagate(self) -> None:
        """AC-4: Exception from adapter is caught, not propagated."""
        state = _make_escalation_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(side_effect=RuntimeError("Network error"))

        result = await notify_escalation(state, adapter)

        assert "error" not in result
        assert result["notification_result"] is None
        assert result["current_node"] == "notify_escalation"


class TestNotifyEscalationMissingRouting:
    """Edge case: no routing_decision in state (route fallback)."""

    @pytest.mark.asyncio
    async def test_sends_fallback_escalation_when_no_routing_decision(self) -> None:
        """AC-5 (5.5.5): Missing routing_decision → send fallback escalation (not skip)."""
        from datetime import UTC, datetime

        from quote_agent.adapters.notification.models import NotificationResult

        state = _make_escalation_state(with_routing=False)
        mock_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(return_value=mock_result)

        result = await notify_escalation(state, adapter)

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "escalation"
        assert "Échec de routage" in payload.data["uncertain"]
        assert result["current_node"] == "notify_escalation"
        assert result["notification_result"] is mock_result


# --- notify_rejection() Tests ---


def _make_rejection_state(
    *,
    review_approved: bool = False,
    compliance_block: bool = False,
) -> AgentState:
    """Build a realistic AgentState for rejection notifier tests."""
    request = ExtractedQuoteRequest(
        client_name="Durand",
        client_identifier="DUR-001",
        line_items=[QuoteLineItem(description="Tube Inox 304L", quantity=100.0)],
        raw_text="Tube Inox 304L",
    )
    state = create_initial_state(request)

    review = MagicMock()
    review.approved = review_approved
    review.failure_reasons = [] if review_approved else ["Product not in catalog"]
    review.anomaly_flags = [] if review_approved else ["Price anomaly detected"]
    state["self_review"] = review

    compliance = MagicMock()
    if compliance_block:
        flag = MagicMock()
        flag.severity = "block"
        flag.flag_type = "export_control"
        flag.detail = "Export controlled item"
        flag.matched_term = "nuclear"
        compliance.flags = [flag]
    else:
        compliance.flags = []
    state["compliance"] = compliance

    return state  # type: ignore[return-value]


class TestNotifyRejectionReviewRejected:
    """AC-1, AC-3 (5.5.1): Notification sent when self-review rejects a quote."""

    @pytest.mark.asyncio
    async def test_sends_escalation_card_for_review_rejection(self) -> None:
        """AC-1, AC-3: notify_rejection sends escalation card with review rejection context."""
        state = _make_rejection_state(review_approved=False, compliance_block=False)
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        result = await notify_rejection(state, adapter)

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "escalation"
        assert payload.title == "Escalade — Rejet auto-review"
        assert "Durand" in payload.message
        assert "auto-vérification" in payload.message
        assert payload.data["client"] == "Durand"
        assert "Product not in catalog" in payload.data["uncertain"]
        assert payload.data["confidence_pct"] == "0"
        assert "/erp/sale-order" in payload.data["erp_url"] or payload.data["erp_url"].endswith("/erp/sale-orders")
        assert result["current_node"] == "notify_rejection"
        assert result["notification_result"] is not None


class TestNotifyRejectionComplianceBlocked:
    """AC-2, AC-3 (5.5.1): Notification sent when compliance blocks a quote."""

    @pytest.mark.asyncio
    async def test_sends_escalation_card_for_compliance_block(self) -> None:
        """AC-2, AC-3: notify_rejection sends escalation card with compliance block context."""
        state = _make_rejection_state(review_approved=True, compliance_block=True)
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        result = await notify_rejection(state, adapter)

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "escalation"
        assert payload.title == "Escalade — Blocage conformité"
        assert "conformité" in payload.message
        assert "Export controlled item" in payload.data["uncertain"]
        assert payload.data["confidence_pct"] == "0"
        assert result["current_node"] == "notify_rejection"


class TestNotifyRejectionDispatchIntegration:
    """AC-4 (5.5.1): Notification dispatched through throttle+batcher when available."""

    @pytest.mark.asyncio
    async def test_dispatches_through_throttle_batcher(self) -> None:
        """AC-4: notify_rejection uses dispatch_quote_notification when throttle+batcher provided."""
        from unittest.mock import patch

        state = _make_rejection_state()
        adapter = AsyncMock()
        throttle = MagicMock()
        batcher = MagicMock()

        mock_dispatch_result = {"notification_result": NotificationResult(
            success=True, status_code=200, timestamp=datetime.now(tz=UTC)
        )}

        with patch(
            "quote_agent.services.notification_dispatcher.dispatch_quote_notification",
            new_callable=AsyncMock,
            return_value=mock_dispatch_result,
        ) as mock_dispatch:
            result = await notify_rejection(
                state, adapter, throttle=throttle, batcher=batcher
            )

        mock_dispatch.assert_called_once()
        adapter.send_notification.assert_not_called()
        assert result["notification_result"] is not None

    @pytest.mark.asyncio
    async def test_direct_send_without_throttle_batcher(self) -> None:
        """AC-4: notify_rejection sends directly when no throttle/batcher."""
        state = _make_rejection_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        result = await notify_rejection(state, adapter)

        adapter.send_notification.assert_called_once()
        assert result["notification_result"] is not None


class TestNotifyRejectionFireAndForget:
    """AC-4 (5.5.1): Notification failure must not block the pipeline."""

    @pytest.mark.asyncio
    async def test_adapter_exception_does_not_propagate(self) -> None:
        """AC-4: Exception from adapter is caught, not propagated."""
        state = _make_rejection_state()
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(side_effect=RuntimeError("Network error"))

        result = await notify_rejection(state, adapter)

        assert "error" not in result
        assert result["notification_result"] is None
        assert result["current_node"] == "notify_rejection"


class TestNotifyRejectionCompliancePrecedence:
    """AC-3 (5.5.1): Compliance block takes precedence when both review and compliance fail."""

    @pytest.mark.asyncio
    async def test_compliance_block_takes_precedence_over_review_rejection(self) -> None:
        """AC-3: When both self_review rejected and compliance blocked, compliance message shown."""
        state = _make_rejection_state(review_approved=False, compliance_block=True)
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(
            return_value=NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        )

        await notify_rejection(state, adapter)

        payload = adapter.send_notification.call_args[0][0]
        assert payload.title == "Escalade — Blocage conformité"
        assert "conformité" in payload.message
