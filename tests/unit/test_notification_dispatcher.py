"""Tests for notification dispatcher — coordination layer between nodes and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from quote_agent.adapters.notification.models import NotificationPayload, NotificationResult
from quote_agent.services.notification_dispatcher import dispatch_quote_notification
from quote_agent.services.notification_throttle import NotificationBatcher, NotificationThrottle


def _make_payload(**overrides: Any) -> NotificationPayload:
    """Create a test notification payload."""
    defaults: dict[str, Any] = {
        "title": "Test",
        "message": "Test message",
        "card_type": "quote-ready",
        "data": {"client": "Acme"},
    }
    defaults.update(overrides)
    return NotificationPayload(**defaults)


def _make_result(success: bool = True) -> NotificationResult:
    return NotificationResult(success=success, status_code=200, timestamp=datetime.now(tz=UTC))


class TestDispatchQuoteNotification:
    """AC-1, AC-2: Dispatcher coordinates throttle + batcher before sending."""

    async def test_normal_flow_sends_immediately(self) -> None:
        """AC-2: When not rate-limited and not bursting, send immediately."""
        adapter = AsyncMock()
        adapter.hostname = "webhook.example.com"
        adapter.send_notification = AsyncMock(return_value=_make_result())

        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        payload = _make_payload()

        result = await dispatch_quote_notification(
            payload=payload, adapter=adapter, throttle=throttle, batcher=batcher
        )

        assert result["sent"] is True
        adapter.send_notification.assert_awaited_once_with(payload)

    async def test_rate_limited_flow_defers(self) -> None:
        """AC-2: When rate-limited, notification is deferred (not sent)."""
        adapter = AsyncMock()
        adapter.hostname = "webhook.example.com"

        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        throttle.record_send("webhook.example.com")

        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        payload = _make_payload()

        result = await dispatch_quote_notification(
            payload=payload, adapter=adapter, throttle=throttle, batcher=batcher
        )

        assert result["sent"] is False
        assert result["reason"] == "rate-limited"
        adapter.send_notification.assert_not_awaited()

    async def test_burst_flow_defers_to_batch(self) -> None:
        """AC-1: When burst threshold exceeded, notification is batched (not sent individually)."""
        adapter = AsyncMock()
        adapter.hostname = "webhook.example.com"

        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)

        # Simulate 6 prior events (over threshold)
        for _ in range(6):
            batcher.record_event("webhook.example.com")

        payload = _make_payload()

        result = await dispatch_quote_notification(
            payload=payload, adapter=adapter, throttle=throttle, batcher=batcher
        )

        assert result["sent"] is False
        assert result["reason"] == "batched"
        adapter.send_notification.assert_not_awaited()

    async def test_records_event_on_every_dispatch(self) -> None:
        """AC-1: Every dispatch call records an event for burst detection."""
        adapter = AsyncMock()
        adapter.hostname = "webhook.example.com"
        adapter.send_notification = AsyncMock(return_value=_make_result())

        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        payload = _make_payload()

        await dispatch_quote_notification(
            payload=payload, adapter=adapter, throttle=throttle, batcher=batcher
        )

        assert batcher.get_pending_count("webhook.example.com") == 1

    async def test_records_send_after_successful_dispatch(self) -> None:
        """AC-2: After successful send, throttle records the send timestamp."""
        adapter = AsyncMock()
        adapter.hostname = "webhook.example.com"
        adapter.send_notification = AsyncMock(return_value=_make_result())

        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        payload = _make_payload()

        await dispatch_quote_notification(
            payload=payload, adapter=adapter, throttle=throttle, batcher=batcher
        )

        # Now should be rate-limited
        assert throttle.can_send("webhook.example.com") is False

    async def test_silence_principle_no_notification_when_nothing_to_process(self) -> None:
        """AC-3: When payload is None, no notification is sent."""
        adapter = AsyncMock()
        adapter.hostname = "webhook.example.com"

        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)

        result = await dispatch_quote_notification(
            payload=None, adapter=adapter, throttle=throttle, batcher=batcher
        )

        assert result["sent"] is False
        assert result["reason"] == "no-payload"
        adapter.send_notification.assert_not_awaited()

    async def test_adapter_exception_caught_gracefully(self) -> None:
        """AC-2: Fire-and-forget — adapter exceptions don't propagate."""
        adapter = AsyncMock()
        adapter.hostname = "webhook.example.com"
        adapter.send_notification = AsyncMock(side_effect=Exception("boom"))

        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        payload = _make_payload()

        result = await dispatch_quote_notification(
            payload=payload, adapter=adapter, throttle=throttle, batcher=batcher
        )

        assert result["sent"] is False
        assert result["reason"] == "error"
