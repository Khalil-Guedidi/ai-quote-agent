"""Microsoft Teams notification adapter — webhook-based integration."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

from quote_agent.adapters.notification.models import NotificationPayload, NotificationResult
from quote_agent.api.health import ServiceHealth
from quote_agent.exceptions import ConfigurationError

if TYPE_CHECKING:
    from quote_agent.config import NotificationSettings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_TIMEOUT = 5.0
_SEND_TIMEOUT = 5.0
_HEALTH_CACHE_TTL = 30.0


class TeamsAdapter:
    """Notification adapter for Microsoft Teams via incoming webhooks."""

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

    def _build_adaptive_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build a Teams Adaptive Card JSON from a NotificationPayload."""
        if payload.card_type == "quote-ready":
            card = self._build_quote_ready_card(payload)
        else:
            card = self._build_generic_card(payload)
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                },
            ],
        }

    def _build_generic_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build the default generic Adaptive Card."""
        return {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "accent",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Q \u2014 AI Quote Agent",
                            "weight": "Bolder",
                            "color": "Light",
                        },
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC"),
                    "size": "Small",
                    "isSubtle": True,
                },
                {
                    "type": "TextBlock",
                    "text": payload.message,
                    "wrap": True,
                },
            ],
        }

    def _build_quote_ready_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build a quote-ready Adaptive Card with green accent, FactSet, and ERP link."""
        data = payload.data
        return {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "good",
                    "bleed": True,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Q \u2014 AI Quote Agent",
                            "weight": "Bolder",
                            "color": "Light",
                        },
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC"),
                    "size": "Small",
                    "isSubtle": True,
                },
                {
                    "type": "TextBlock",
                    "text": payload.message,
                    "wrap": True,
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Client", "value": data.get("client", "")},
                        {"title": "Produit", "value": data.get("product", "")},
                        {"title": "Quantité", "value": data.get("quantity", "")},
                        {"title": "Confiance", "value": f"{data.get('confidence_pct', '')}%"},
                    ],
                },
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Voir dans l'ERP",
                    "url": data.get("erp_url", ""),
                },
            ],
        }

    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        """Send a notification as a Teams Adaptive Card via the configured webhook."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._webhook_url,
                    json=self._build_adaptive_card(payload),
                    timeout=_SEND_TIMEOUT,
                )
            return NotificationResult(
                success=response.status_code < 400,
                status_code=response.status_code,
                timestamp=datetime.now(tz=UTC),
            )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.InvalidURL, OSError) as exc:
            logger.warning("Notification send failed (%s): %s", self._hostname, exc)
            return NotificationResult(
                success=False,
                error=str(exc),
                timestamp=datetime.now(tz=UTC),
            )

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
