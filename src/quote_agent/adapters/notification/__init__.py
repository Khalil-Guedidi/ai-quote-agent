"""Notification adapter package — multi-channel notification integration."""

from __future__ import annotations

from functools import lru_cache

from quote_agent.adapters.notification.models import (
    NotificationPayload,
    NotificationResult,
    TeamsWebhookInfo,
)
from quote_agent.adapters.notification.protocol import NotificationAdapter

__all__ = [
    "NotificationAdapter",
    "NotificationPayload",
    "NotificationResult",
    "TeamsWebhookInfo",
    "get_notification_adapter",
]


@lru_cache(maxsize=1)
def get_notification_adapter() -> NotificationAdapter:
    """Create and return a cached notification adapter singleton.

    Routes to the appropriate adapter based on ``settings.notification.channel``.
    Supported channels: ``"teams"``, ``"log"``.
    """
    from quote_agent.config import get_settings
    from quote_agent.exceptions import ConfigurationError

    settings = get_settings().notification
    if settings.channel == "teams":
        from quote_agent.adapters.notification.teams import TeamsAdapter

        return TeamsAdapter(settings)
    if settings.channel == "log":
        from quote_agent.adapters.notification.log import LogAdapter

        return LogAdapter()
    msg = f"Unknown notification channel: {settings.channel}"
    raise ConfigurationError(msg)
