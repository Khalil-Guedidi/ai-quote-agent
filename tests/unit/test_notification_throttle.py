"""Tests for notification throttle and batcher — rate limiting and burst detection."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from quote_agent.config import NotificationBatchSettings
from quote_agent.services.notification_throttle import NotificationBatcher, NotificationThrottle


class TestNotificationThrottle:
    """AC-2: Rate limiting — no more than 1 notification per minute to same recipient."""

    def test_can_send_returns_true_initially(self) -> None:
        """AC-2: First send to any recipient should always be allowed."""
        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        assert throttle.can_send("recipient-a") is True

    def test_can_send_returns_false_after_recent_send(self) -> None:
        """AC-2: Second send within rate window should be blocked."""
        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        throttle.record_send("recipient-a")
        assert throttle.can_send("recipient-a") is False

    def test_can_send_returns_true_after_window_expires(self) -> None:
        """AC-2: Send should be allowed after rate window elapses."""
        throttle = NotificationThrottle(rate_limit_seconds=60.0)

        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1000.0):
            throttle.record_send("recipient-a")

        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1061.0):
            assert throttle.can_send("recipient-a") is True

    def test_can_send_independent_per_recipient(self) -> None:
        """AC-2: Rate limiting is per-recipient — one recipient blocked doesn't affect another."""
        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        throttle.record_send("recipient-a")
        assert throttle.can_send("recipient-a") is False
        assert throttle.can_send("recipient-b") is True

    def test_time_until_allowed_returns_zero_initially(self) -> None:
        """AC-2: No wait time for first send."""
        throttle = NotificationThrottle(rate_limit_seconds=60.0)
        assert throttle.time_until_allowed("recipient-a") == 0.0

    def test_time_until_allowed_returns_remaining_seconds(self) -> None:
        """AC-2: Returns correct remaining seconds after a recent send."""
        throttle = NotificationThrottle(rate_limit_seconds=60.0)

        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1000.0):
            throttle.record_send("recipient-a")

        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1030.0):
            remaining = throttle.time_until_allowed("recipient-a")
            assert remaining == pytest.approx(30.0)

    def test_time_until_allowed_returns_zero_after_window(self) -> None:
        """AC-2: Returns 0 after rate window elapses."""
        throttle = NotificationThrottle(rate_limit_seconds=60.0)

        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1000.0):
            throttle.record_send("recipient-a")

        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1061.0):
            assert throttle.time_until_allowed("recipient-a") == 0.0


class TestNotificationBatcher:
    """AC-1: Burst detection — batch when >5 events in 10 minutes."""

    def test_should_batch_returns_false_for_few_events(self) -> None:
        """AC-1: <=5 events in window should NOT trigger batching."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        for _ in range(5):
            batcher.record_event("recipient-a")
        assert batcher.should_batch("recipient-a") is False

    def test_should_batch_returns_true_for_burst(self) -> None:
        """AC-1: >5 events in window should trigger batching."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        for _ in range(6):
            batcher.record_event("recipient-a")
        assert batcher.should_batch("recipient-a") is True

    def test_events_pruned_outside_window(self) -> None:
        """AC-1: Events older than burst window are pruned."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)

        # Record 6 events at t=1000
        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1000.0):
            for _ in range(6):
                batcher.record_event("recipient-a")

        # At t=1700 (700s later, outside 600s window), old events pruned
        with patch("quote_agent.services.notification_throttle.time.monotonic", return_value=1700.0):
            assert batcher.should_batch("recipient-a") is False

    def test_get_pending_count(self) -> None:
        """AC-1: Returns correct count of events in current window."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        batcher.record_event("recipient-a")
        batcher.record_event("recipient-a")
        batcher.record_event("recipient-a")
        assert batcher.get_pending_count("recipient-a") == 3

    def test_get_pending_count_empty(self) -> None:
        """AC-1: Returns 0 for unknown recipient."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        assert batcher.get_pending_count("unknown") == 0

    def test_flush_clears_deque_and_returns_count(self) -> None:
        """AC-1: Flush clears events and returns the count."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        for _ in range(4):
            batcher.record_event("recipient-a")

        count = batcher.flush("recipient-a")
        assert count == 4
        assert batcher.get_pending_count("recipient-a") == 0
        assert batcher.should_batch("recipient-a") is False

    def test_flush_empty_recipient(self) -> None:
        """AC-1: Flush on unknown recipient returns 0."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        assert batcher.flush("unknown") == 0

    def test_independent_per_recipient(self) -> None:
        """AC-1: Batching state is per-recipient."""
        batcher = NotificationBatcher(burst_threshold=5, burst_window_seconds=600.0)
        for _ in range(6):
            batcher.record_event("recipient-a")
        batcher.record_event("recipient-b")

        assert batcher.should_batch("recipient-a") is True
        assert batcher.should_batch("recipient-b") is False


class TestNotificationBatchSettings:
    """AC-1: Config loads from env vars with __ delimiter."""

    def test_defaults(self) -> None:
        """AC-1: Default values match story spec."""
        settings = NotificationBatchSettings()
        assert settings.burst_threshold == 5
        assert settings.burst_window_seconds == 600
        assert settings.rate_limit_seconds == 60

    def test_custom_values(self) -> None:
        """AC-1: Custom values can be provided."""
        settings = NotificationBatchSettings(burst_threshold=10, burst_window_seconds=300, rate_limit_seconds=30)
        assert settings.burst_threshold == 10
        assert settings.burst_window_seconds == 300
        assert settings.rate_limit_seconds == 30
