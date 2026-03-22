"""Notification adapter package — Teams webhook integration."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from quote_agent.adapters.notification.models import (
    NotificationPayload,
    NotificationResult,
    TeamsWebhookInfo,
)
from quote_agent.adapters.notification.protocol import NotificationAdapter

if TYPE_CHECKING:
    from quote_agent.adapters.notification.teams import TeamsAdapter

__all__ = [
    "NotificationAdapter",
    "NotificationPayload",
    "NotificationResult",
    "TeamsWebhookInfo",
    "get_notification_adapter",
]


@lru_cache(maxsize=1)
def get_notification_adapter() -> TeamsAdapter:
    """Create and return a cached notification adapter singleton."""
    from quote_agent.adapters.notification.teams import TeamsAdapter
    from quote_agent.config import get_settings

    return TeamsAdapter(get_settings().notification)
