"""Tests for the notify_quote_ready node — success, failure, and missing draft_result."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from quote_agent.adapters.notification.models import NotificationResult
from quote_agent.agent.nodes.notifier import notify_multi_proposal, notify_quote_ready
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


def _make_erp_settings(url: str = "https://odoo.example.com") -> MagicMock:
    settings = MagicMock()
    settings.url = url
    return settings


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

        await notify_quote_ready(state, adapter, _make_erp_settings())

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "quote-ready"
        assert payload.data["client"] == "Durand"
        assert payload.data["product"] == "Tube Inox 304L"
        assert payload.data["quantity"] == "100.0"
        assert payload.data["confidence_pct"] == "92"
        assert "id=42" in payload.data["erp_url"]
        assert "sale.order" in payload.data["erp_url"]

    @pytest.mark.asyncio
    async def test_returns_notification_result_in_state(self) -> None:
        """AC-4: Successful notification result stored in state."""
        state = _make_state()
        expected_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(return_value=expected_result)

        result = await notify_quote_ready(state, adapter, _make_erp_settings())

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

        result = await notify_quote_ready(state, adapter, _make_erp_settings())

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

        result = await notify_quote_ready(state, adapter, _make_erp_settings())

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

        result = await notify_quote_ready(state, adapter, _make_erp_settings())

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

        await notify_multi_proposal(state, adapter, _make_erp_settings())

        adapter.send_notification.assert_called_once()
        payload = adapter.send_notification.call_args[0][0]
        assert payload.card_type == "multi-proposal"
        assert payload.data["client"] == "Durand"
        assert len(payload.data["proposals"]) == 3
        assert payload.data["proposals"][0]["name"] == "Product 1"
        assert payload.data["proposals"][0]["confidence_pct"] == "78"
        assert "sale.order" in payload.data["erp_url"]
        assert "view_type=list" in payload.data["erp_url"]

    @pytest.mark.asyncio
    async def test_returns_notification_result_in_state(self) -> None:
        """AC-3: Successful notification result stored in state."""
        state = _make_proposal_state()
        expected_result = NotificationResult(success=True, status_code=200, timestamp=datetime.now(tz=UTC))
        adapter = AsyncMock()
        adapter.send_notification = AsyncMock(return_value=expected_result)

        result = await notify_multi_proposal(state, adapter, _make_erp_settings())

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

        await notify_multi_proposal(state, adapter, _make_erp_settings())

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

        result = await notify_multi_proposal(state, adapter, _make_erp_settings())

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

        result = await notify_multi_proposal(state, adapter, _make_erp_settings())

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

        result = await notify_multi_proposal(state, adapter, _make_erp_settings())

        adapter.send_notification.assert_not_called()
        assert result["notification_result"] is None
        assert result["current_node"] == "notify_proposals"
        assert "error" not in result
