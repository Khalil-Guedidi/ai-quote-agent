"""Typed DTOs for the notification adapter layer."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, Field


class TeamsWebhookInfo(BaseModel):
    """Diagnostic info for Teams webhook (never exposes the full URL)."""

    hostname: str


class NotificationPayload(BaseModel):
    """Payload for sending a notification via any channel."""

    title: str
    message: str
    card_type: str = "test"
    data: dict[str, Any] = Field(default_factory=dict)


class NotificationResult(BaseModel):
    """Result of a notification delivery attempt."""

    success: bool
    status_code: int | None = None
    error: str | None = None
    timestamp: datetime
