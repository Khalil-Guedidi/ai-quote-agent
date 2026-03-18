"""Microsoft Teams notification adapter — webhook-based integration."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from quote_agent.api.health import ServiceHealth
from quote_agent.exceptions import ConfigurationError

if TYPE_CHECKING:
    from quote_agent.config import NotificationSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0


class TeamsAdapter:
    """Notification adapter for Microsoft Teams via incoming webhooks (health check only)."""

    def __init__(self, settings: NotificationSettings) -> None:
        url = settings.teams_webhook_url
        if not url:
            msg = "NOTIFICATION__TEAMS_WEBHOOK_URL must not be empty"
            raise ConfigurationError(msg)
        if not url.startswith("https://"):
            msg = "NOTIFICATION__TEAMS_WEBHOOK_URL must be an HTTPS URL"
            raise ConfigurationError(msg)

        self._settings = settings
        self._webhook_url = url
        self._hostname = urlparse(url).hostname or "unknown"
        self._last_health: ServiceHealth | None = None
        self._last_health_time: float = 0.0

    async def health_check(self) -> ServiceHealth:
        """Check Teams webhook reachability with 30s caching."""
        now = time.monotonic()
        if self._last_health and (now - self._last_health_time) < _HEALTH_CACHE_TTL:
            return self._last_health

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._webhook_url,
                    json={},
                    timeout=_HEALTH_CHECK_TIMEOUT,
                )
            # Any response (2xx, 4xx) means the server is reachable
            health = ServiceHealth(status="healthy")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.InvalidURL, OSError) as exc:
            logger.warning("Notification health check failed (%s): %s", self._hostname, exc)
            health = ServiceHealth(status="unhealthy", error=str(exc))

        self._last_health = health
        self._last_health_time = time.monotonic()
        return health
