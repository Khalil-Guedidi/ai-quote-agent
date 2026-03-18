"""Typed DTOs for the email adapter layer."""

from __future__ import annotations

from pydantic import BaseModel


class IMAPHealthInfo(BaseModel):
    """Basic IMAP connection info for diagnostics."""

    server: str
    port: int
    folder: str


# Future DTOs (Epic 2):
# - IncomingEmail: raw email data from IMAP fetch
# - ParsedEmail: cleaned and structured email content
