"""Typed DTOs for the email adapter layer."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime access for model validation

from pydantic import BaseModel


class IMAPHealthInfo(BaseModel):
    """Basic IMAP connection info for diagnostics."""

    server: str
    port: int
    folder: str


class IncomingEmail(BaseModel):
    """Raw email data from IMAP fetch."""

    message_id: str
    subject: str
    sender: str
    recipients: list[str]
    raw_content: str
    received_at: datetime | None = None
