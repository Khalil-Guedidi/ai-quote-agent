"""Scheduled notification service — batch summary and weekly report sending."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from quote_agent.adapters.notification.models import NotificationPayload, NotificationResult
from quote_agent.services.notification_stats import get_daily_summary, get_weekly_report

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from quote_agent.adapters.notification.teams import TeamsAdapter
    from quote_agent.config import ConfidenceScoringSettings, ERPSettings

logger = logging.getLogger(__name__)


async def send_batch_summary(
    session: AsyncSession,
    adapter: TeamsAdapter,
    erp_settings: ERPSettings,
    confidence_settings: ConfidenceScoringSettings | None = None,
) -> NotificationResult | None:
    """Send the daily batch summary notification.

    Returns None if no quotes to report (silence principle).
    Fire-and-forget: catches all exceptions, logs warnings, never crashes.
    """
    try:
        if confidence_settings is None:
            from quote_agent.config import get_settings

            confidence_settings = get_settings().confidence_scoring
        summary = await get_daily_summary(
            session,
            high_threshold=confidence_settings.high_threshold,
            low_threshold=confidence_settings.low_threshold,
        )

        if summary.total == 0:
            logger.info("No quotes processed today — skipping batch summary notification")
            return None

        erp_url = f"{erp_settings.url}/web#model=sale.order&view_type=list"
        message = (
            f"Bonjour ! J'ai traité {summary.total} devis. "
            f"{summary.high_count} prêts, "
            f"{summary.medium_count} besoin de ton choix, "
            f"{summary.low_count} besoin de ton expertise"
        )

        payload = NotificationPayload(
            title="Résumé du jour",
            message=message,
            card_type="batch-summary",
            data={
                "total": summary.total,
                "high": summary.high_count,
                "medium": summary.medium_count,
                "low": summary.low_count,
                "erp_url": erp_url,
            },
        )

        return await adapter.send_notification(payload)

    except Exception:
        logger.warning("Failed to send batch summary notification", exc_info=True)
        return None


async def send_weekly_report(
    session: AsyncSession,
    adapter: TeamsAdapter,
    erp_settings: ERPSettings,
) -> NotificationResult | None:
    """Send the weekly manager report notification.

    Returns None if no quotes to report (silence principle).
    Fire-and-forget: catches all exceptions, logs warnings, never crashes.
    """
    try:
        report = await get_weekly_report(session)

        if report.total == 0:
            logger.info("No quotes processed this week — skipping weekly report notification")
            return None

        erp_url = f"{erp_settings.url}/web#model=sale.order&view_type=list"
        message = (
            f"Voici le récap de la semaine. "
            f"{report.total} devis traités, confiance moyenne {report.avg_confidence}%"
        )

        payload = NotificationPayload(
            title="Rapport hebdomadaire",
            message=message,
            card_type="manager-weekly",
            data={
                "total": report.total,
                "avg_confidence": report.avg_confidence,
                "trend_pct": report.trend_pct,
                "trend_direction": report.trend_direction,
                "rep_breakdown": [rep.model_dump() for rep in report.rep_breakdown],
                "erp_url": erp_url,
            },
        )

        return await adapter.send_notification(payload)

    except Exception:
        logger.warning("Failed to send weekly report notification", exc_info=True)
        return None


async def send_manager_stats(
    session: AsyncSession,
    adapter: TeamsAdapter,
    confidence_settings: ConfidenceScoringSettings | None = None,
) -> NotificationResult | None:
    """Send on-demand manager stats notification.

    Fire-and-forget: catches all exceptions, logs warnings, never crashes.
    """
    try:
        if confidence_settings is None:
            from quote_agent.config import get_settings

            confidence_settings = get_settings().confidence_scoring
        summary = await get_daily_summary(
            session,
            high_threshold=confidence_settings.high_threshold,
            low_threshold=confidence_settings.low_threshold,
        )
        weekly = await get_weekly_report(session)

        message = f"Stats du jour : {summary.total} devis traités"

        payload = NotificationPayload(
            title="Stats manager",
            message=message,
            card_type="manager-stats",
            data={
                "total": summary.total,
                "high": summary.high_count,
                "medium": summary.medium_count,
                "low": summary.low_count,
                "avg_confidence": weekly.avg_confidence,
            },
        )

        return await adapter.send_notification(payload)

    except Exception:
        logger.warning("Failed to send manager stats notification", exc_info=True)
        return None
