"""Email adapter package — IMAP integration."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from quote_agent.adapters.email.models import IMAPHealthInfo, IncomingEmail
from quote_agent.adapters.email.protocol import EmailAdapter

if TYPE_CHECKING:
    from quote_agent.adapters.email.imap import IMAPAdapter

__all__ = [
    "EmailAdapter",
    "IMAPHealthInfo",
    "IncomingEmail",
    "get_email_adapter",
]


@lru_cache(maxsize=1)
def get_email_adapter() -> IMAPAdapter:
    """Create and return a cached email adapter singleton."""
    from quote_agent.adapters.email.imap import IMAPAdapter
    from quote_agent.config import get_settings

    return IMAPAdapter(get_settings().email)
