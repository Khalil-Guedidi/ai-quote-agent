"""Odoo ERP adapter implementation using XML-RPC."""

from __future__ import annotations

import asyncio
import logging
import time
import xmlrpc.client
from typing import TYPE_CHECKING

from quote_agent.api.health import ServiceHealth

if TYPE_CHECKING:
    from quote_agent.config import ERPSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0


class OdooAdapter:
    """ERP adapter for Odoo via XML-RPC (health check only for now)."""

    def __init__(self, settings: ERPSettings) -> None:
        self._settings = settings
        self._last_health: ServiceHealth | None = None
        self._last_health_time: float = 0.0

    async def health_check(self) -> ServiceHealth:
        """Check Odoo connectivity and authentication with 30s caching."""
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
        except (ConnectionRefusedError, OSError, xmlrpc.client.Error) as exc:
            logger.warning("ERP health check failed: %s", exc)
            health = ServiceHealth(status="unhealthy", error=str(exc))

        self._last_health = health
        self._last_health_time = time.monotonic()
        return health

    async def _perform_health_check(self) -> ServiceHealth:
        """Execute XML-RPC version + authenticate calls."""
        url = self._settings.url
        proxy = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")

        # Step 1: Check connectivity (no auth needed)
        await asyncio.to_thread(proxy.version)

        # Step 2: Verify credentials
        uid = await asyncio.to_thread(
            proxy.authenticate,
            self._settings.database,
            self._settings.username,
            self._settings.api_key.get_secret_value(),
            {},
        )

        if not uid:
            return ServiceHealth(
                status="unhealthy",
                error="Authentication failed: invalid credentials",
            )

        return ServiceHealth(status="healthy")
