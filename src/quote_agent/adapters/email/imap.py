"""IMAP email adapter implementation."""

from __future__ import annotations

import asyncio
import contextlib
import imaplib
import logging
import time
from typing import TYPE_CHECKING

from quote_agent.api.health import ServiceHealth

if TYPE_CHECKING:
    from quote_agent.config import EmailSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0


class IMAPAdapter:
    """Email adapter for IMAP (health check only for now)."""

    def __init__(self, settings: EmailSettings) -> None:
        self._settings = settings
        self._last_health: ServiceHealth | None = None
        self._last_health_time: float = 0.0

    async def health_check(self) -> ServiceHealth:
        """Check IMAP connectivity and authentication with 30s caching."""
        now = time.monotonic()
        if self._last_health and (now - self._last_health_time) < _HEALTH_CACHE_TTL:
            return self._last_health

        try:
            health = await asyncio.wait_for(
                self._perform_health_check(),
                timeout=_HEALTH_CHECK_TIMEOUT,
            )
        except TimeoutError:
            health = ServiceHealth(status="unhealthy", error="Health check timed out")
        except (imaplib.IMAP4.error, ConnectionRefusedError, OSError) as exc:
            logger.warning("Email health check failed: %s", exc)
            health = ServiceHealth(status="unhealthy", error=str(exc))

        self._last_health = health
        self._last_health_time = time.monotonic()
        return health

    async def _perform_health_check(self) -> ServiceHealth:
        """Execute IMAP connect-login-select-logout sequence."""
        health = await asyncio.to_thread(self._imap_health_sync)
        return health

    def _imap_health_sync(self) -> ServiceHealth:
        """Synchronous IMAP health check — run via asyncio.to_thread."""
        conn = imaplib.IMAP4_SSL(
            self._settings.imap_server,
            self._settings.imap_port,
        )
        try:
            conn.login(
                self._settings.username,
                self._settings.password.get_secret_value(),
            )
            conn.select(self._settings.folder)
        finally:
            with contextlib.suppress(Exception):
                conn.logout()
        return ServiceHealth(status="healthy")
