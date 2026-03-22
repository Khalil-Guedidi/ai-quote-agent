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

    @property
    def hostname(self) -> str:
        """Public accessor for the webhook hostname."""
        return self._hostname

    def _build_adaptive_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build a Teams Adaptive Card JSON from a NotificationPayload."""
        if payload.card_type == "quote-ready":
            card = self._build_quote_ready_card(payload)
        elif payload.card_type == "multi-proposal":
            card = self._build_multi_proposal_card(payload)
        elif payload.card_type == "escalation":
            card = self._build_escalation_card(payload)
        elif payload.card_type == "batch-summary":
            card = self._build_batch_summary_card(payload)
        elif payload.card_type == "manager-weekly":
            card = self._build_manager_weekly_card(payload)
        elif payload.card_type == "manager-stats":
            card = self._build_manager_stats_card(payload)
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

    def _build_multi_proposal_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build a multi-proposal Adaptive Card with amber accent and proposal rows."""
        data = payload.data
        proposals = data.get("proposals", [])
        proposal_rows: list[dict[str, Any]] = []
        for proposal in proposals:
            proposal_rows.append(
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": proposal.get("name", ""),
                                    "weight": "Bolder",
                                    "wrap": True,
                                },
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": proposal.get("match_quality", ""),
                                    "isSubtle": True,
                                    "wrap": True,
                                },
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{proposal.get('confidence_pct', '')}%",
                                    "weight": "Bolder",
                                },
                            ],
                        },
                    ],
                }
            )

        return {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "warning",
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
                *proposal_rows,
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Voir dans l'ERP",
                    "url": data.get("erp_url", ""),
                },
            ],
        }

    def _build_escalation_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build an escalation Adaptive Card with red accent and context sections."""
        data = payload.data
        suggested_steps = data.get("suggested_next_steps", [])
        step_blocks: list[dict[str, Any]] = [
            {"type": "TextBlock", "text": f"• {step}", "wrap": True}
            for step in suggested_steps
        ]

        return {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "attention",
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
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Ce que j'ai compris",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": data.get("understood", ""),
                            "wrap": True,
                        },
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Ce qui est flou",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": data.get("uncertain", ""),
                            "wrap": True,
                            "isSubtle": True,
                        },
                    ],
                },
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Prochaines étapes suggérées",
                            "weight": "Bolder",
                        },
                        *step_blocks,
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

    def _build_batch_summary_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build a batch summary Adaptive Card with accent bar and tier counts."""
        data = payload.data
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
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Prêts", "value": str(data.get("high", 0))},
                        {"title": "Choix nécessaire", "value": str(data.get("medium", 0))},
                        {"title": "Expertise nécessaire", "value": str(data.get("low", 0))},
                        {"title": "Total", "value": str(data.get("total", 0))},
                    ],
                },
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Voir la file ERP",
                    "url": data.get("erp_url", ""),
                },
            ],
        }

    def _build_manager_weekly_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build a manager weekly report Adaptive Card with per-rep breakdown."""
        data = payload.data
        rep_breakdown = data.get("rep_breakdown", [])
        rep_rows: list[dict[str, Any]] = []
        for rep in rep_breakdown:
            rep_rows.append(
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": rep.get("rep_name", ""),
                                    "weight": "Bolder",
                                },
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": str(rep.get("quotes_count", 0)),
                                },
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{rep.get('avg_confidence_pct', 0)}%",
                                },
                            ],
                        },
                    ],
                }
            )

        trend_pct = data.get("trend_pct", 0)
        trend_direction = data.get("trend_direction", "stable")
        trend_arrow = "\u25b2" if trend_direction == "up" else "\u25bc" if trend_direction == "down" else "\u25b6"
        trend_text = f"{trend_arrow} {'+' if trend_pct > 0 else ''}{trend_pct}% vs semaine précédente"

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
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Total traités", "value": str(data.get("total", 0))},
                        {"title": "Confiance moyenne", "value": f"{data.get('avg_confidence', 0)}%"},
                        {"title": "Tendance", "value": trend_text},
                    ],
                },
                *rep_rows,
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Voir la file ERP",
                    "url": data.get("erp_url", ""),
                },
            ],
        }

    def _build_manager_stats_card(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build a manager on-demand stats Adaptive Card."""
        data = payload.data
        facts: list[dict[str, str]] = []
        if "total" in data:
            facts.append({"title": "Total traités", "value": str(data["total"])})
        if "avg_confidence" in data:
            facts.append({"title": "Confiance moyenne", "value": f"{data['avg_confidence']}%"})
        if "high" in data:
            facts.append({"title": "Prêts", "value": str(data["high"])})
        if "medium" in data:
            facts.append({"title": "Choix nécessaire", "value": str(data["medium"])})
        if "low" in data:
            facts.append({"title": "Expertise nécessaire", "value": str(data["low"])})

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
                {
                    "type": "FactSet",
                    "facts": facts,
                },
                {
                    "type": "TextBlock",
                    "text": "Commandes disponibles: stats jour, stats semaine, stats mois",
                    "size": "Small",
                    "isSubtle": True,
                    "wrap": True,
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
