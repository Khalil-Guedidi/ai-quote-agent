"""Notification scheduler — asyncio background tasks for daily batch summary and weekly report.

Pure asyncio (sleep + loop) pattern — no APScheduler/Celery dependency.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from quote_agent.adapters.notification.protocol import NotificationAdapter
    from quote_agent.config import NotificationScheduleSettings

logger = logging.getLogger(__name__)


def seconds_until(hour: int, minute: int, *, target_weekday: int | None = None) -> float:
    """Calculate seconds from now until the next occurrence of hour:minute (UTC).

    If the target time has already passed today (or this week for weekday targets),
    returns seconds until the next occurrence.

    Args:
        hour: Target hour (0-23).
        minute: Target minute (0-59).
        target_weekday: 0=Monday, 6=Sunday. If None, targets daily.

    Returns:
        Seconds until the next target time (always > 0).
    """
    now = datetime.now(UTC)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target_weekday is not None:
        # Advance to the target weekday
        days_ahead = target_weekday - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        target = target + timedelta(days=days_ahead)

    # If target is now or in the past, push to next occurrence
    if target <= now:
        if target_weekday is not None:
            target += timedelta(weeks=1)
        else:
            target += timedelta(days=1)

    return (target - now).total_seconds()


class NotificationScheduler:
    """Manages background asyncio tasks for scheduled notification sends.

    Call ``start()`` to spawn daily + weekly loops, ``stop()`` to cancel them.
    """

    def __init__(
        self,
        *,
        schedule_settings: NotificationScheduleSettings,
        session_factory: async_sessionmaker[AsyncSession],
        adapter: NotificationAdapter,
    ) -> None:
        self._settings = schedule_settings
        self._session_factory = session_factory
        self._adapter = adapter
        self._daily_task: asyncio.Task[None] | None = None
        self._weekly_task: asyncio.Task[None] | None = None

    def should_run(self) -> bool:
        """Return True if the scheduler should start (enabled + webhook configured)."""
        if not self._settings.scheduler_enabled:
            return False
        return bool(getattr(self._adapter, "hostname", ""))

    def start(self) -> None:
        """Spawn background tasks for daily and weekly sends."""
        if self._daily_task is not None and not self._daily_task.done():
            logger.info("Scheduler already running — skipping start")
            return

        logger.info(
            "Starting notification scheduler (daily=%02d:%02d, weekly=%s %02d:%02d)",
            self._settings.batch_summary_hour,
            self._settings.batch_summary_minute,
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][self._settings.weekly_report_day],
            self._settings.weekly_report_hour,
            self._settings.weekly_report_minute,
        )

        self._daily_task = asyncio.create_task(self._run_daily_loop())
        self._weekly_task = asyncio.create_task(self._run_weekly_loop())

    def stop(self) -> None:
        """Cancel background tasks gracefully."""
        if self._daily_task is not None:
            self._daily_task.cancel()
            self._daily_task = None
        if self._weekly_task is not None:
            self._weekly_task.cancel()
            self._weekly_task = None
        logger.info("Notification scheduler stopped")

    def next_daily_in_seconds(self) -> float:
        """Return seconds until the next daily batch summary."""
        return seconds_until(self._settings.batch_summary_hour, self._settings.batch_summary_minute)

    def next_weekly_in_seconds(self) -> float:
        """Return seconds until the next weekly report."""
        return seconds_until(
            self._settings.weekly_report_hour,
            self._settings.weekly_report_minute,
            target_weekday=self._settings.weekly_report_day,
        )

    async def _run_daily_loop(self) -> None:
        """Run the daily batch summary on schedule, forever."""
        while True:
            wait = seconds_until(self._settings.batch_summary_hour, self._settings.batch_summary_minute)
            logger.info("Daily batch summary scheduled in %.0f seconds", wait)
            await asyncio.sleep(wait)
            try:
                from quote_agent.services.scheduled_notifications import send_batch_summary

                async with self._session_factory() as session:
                    await send_batch_summary(session, self._adapter)
                logger.info("Daily batch summary sent successfully")
            except Exception:
                logger.warning("Scheduled batch summary failed", exc_info=True)

    async def _run_weekly_loop(self) -> None:
        """Run the weekly manager report on schedule, forever."""
        while True:
            wait = seconds_until(
                self._settings.weekly_report_hour,
                self._settings.weekly_report_minute,
                target_weekday=self._settings.weekly_report_day,
            )
            logger.info("Weekly report scheduled in %.0f seconds", wait)
            await asyncio.sleep(wait)
            try:
                from quote_agent.services.scheduled_notifications import send_weekly_report

                async with self._session_factory() as session:
                    await send_weekly_report(session, self._adapter)
                logger.info("Weekly report sent successfully")
            except Exception:
                logger.warning("Scheduled weekly report failed", exc_info=True)
