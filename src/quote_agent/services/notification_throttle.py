"""Notification throttle and batcher — rate limiting and burst detection.

In-memory state (no database). Single-tenant MVP — if the app restarts,
throttle/batch windows reset (acceptable behavior).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class NotificationThrottle:
    """Per-recipient rate limiter — enforces minimum interval between sends.

    Uses ``time.monotonic()`` for clock-immune timing.
    """

    def __init__(self, rate_limit_seconds: float = 60.0) -> None:
        self._rate_limit = rate_limit_seconds
        self._last_send: dict[str, float] = {}

    def can_send(self, recipient: str) -> bool:
        """Return True if the recipient is allowed to receive a notification now."""
        last = self._last_send.get(recipient)
        if last is None:
            return True
        return (time.monotonic() - last) >= self._rate_limit

    def record_send(self, recipient: str) -> None:
        """Record that a notification was sent to the recipient."""
        self._last_send[recipient] = time.monotonic()

    def time_until_allowed(self, recipient: str) -> float:
        """Return seconds remaining until the next allowed send (0.0 if allowed now)."""
        last = self._last_send.get(recipient)
        if last is None:
            return 0.0
        elapsed = time.monotonic() - last
        remaining = self._rate_limit - elapsed
        return max(0.0, remaining)


class NotificationBatcher:
    """Burst detection — tracks notification events per recipient.

    When a recipient receives more than ``burst_threshold`` events within
    ``burst_window_seconds``, individual notifications should be batched.
    """

    def __init__(self, burst_threshold: int = 5, burst_window_seconds: float = 600.0) -> None:
        self._threshold = burst_threshold
        self._window = burst_window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def record_event(self, recipient: str) -> None:
        """Record a notification event for the recipient and prune old entries."""
        self._events[recipient].append(time.monotonic())
        self._prune(recipient)

    def should_batch(self, recipient: str) -> bool:
        """Return True if the recipient has exceeded the burst threshold in the window."""
        self._prune(recipient)
        return len(self._events[recipient]) > self._threshold

    def get_pending_count(self, recipient: str) -> int:
        """Return count of events in the current burst window."""
        self._prune(recipient)
        return len(self._events[recipient])

    def flush(self, recipient: str) -> int:
        """Clear the recipient's event deque and return the count that was flushed."""
        events = self._events.get(recipient)
        if events is None:
            return 0
        count = len(events)
        events.clear()
        return count

    def _prune(self, recipient: str) -> None:
        """Remove events older than the burst window."""
        cutoff = time.monotonic() - self._window
        events = self._events[recipient]
        while events and events[0] < cutoff:
            events.popleft()
