"""Typed DTOs for the notification adapter layer."""

from __future__ import annotations

from pydantic import BaseModel


class TeamsWebhookInfo(BaseModel):
    """Diagnostic info for Teams webhook (never exposes the full URL)."""

    hostname: str


# Future DTOs (Epic 5):
# - NotificationPayload: message content, recipient, priority, card template
# - NotificationResult: delivery status, message ID, timestamp
