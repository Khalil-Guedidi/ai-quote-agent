"""Tests for notification scheduler — asyncio background tasks for daily/weekly sends."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from quote_agent.services.notification_scheduler import NotificationScheduler, seconds_until


class TestSecondsUntil:
    """AC-4, AC-5: Correct time calculation for scheduled sends."""

    def test_same_day_future(self) -> None:
        """AC-4: Target time later today returns correct seconds."""
        now = datetime(2026, 3, 22, 6, 0, 0, tzinfo=UTC)
        with patch("quote_agent.services.notification_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = seconds_until(8, 0)
        assert result == 2 * 3600  # 2 hours

    def test_next_day_when_time_passed(self) -> None:
        """AC-4: Target time already passed today returns seconds until tomorrow."""
        now = datetime(2026, 3, 22, 10, 0, 0, tzinfo=UTC)
        with patch("quote_agent.services.notification_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = seconds_until(8, 0)
        assert result == 22 * 3600  # 22 hours until next 08:00

    def test_specific_weekday_future(self) -> None:
        """AC-5: Target weekday in the future returns correct seconds."""
        # 2026-03-22 is a Sunday (weekday=6), target Monday (weekday=0)
        now = datetime(2026, 3, 22, 8, 0, 0, tzinfo=UTC)
        with patch("quote_agent.services.notification_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = seconds_until(8, 0, target_weekday=0)
        assert result == 24 * 3600  # Monday is 1 day away

    def test_same_weekday_time_passed(self) -> None:
        """AC-5: If target weekday is today but time has passed, returns next week."""
        # 2026-03-23 is a Monday (weekday=0), time already past 08:00
        now = datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC)
        with patch("quote_agent.services.notification_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = seconds_until(8, 0, target_weekday=0)
        assert result == 7 * 24 * 3600 - 2 * 3600  # next Monday 08:00 minus 2h already elapsed

    def test_exact_time_returns_next_day(self) -> None:
        """AC-4: If exactly at target time, schedule for next occurrence."""
        now = datetime(2026, 3, 22, 8, 0, 0, tzinfo=UTC)
        with patch("quote_agent.services.notification_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = seconds_until(8, 0)
        assert result == 24 * 3600  # next day


class TestNotificationSchedulerLifecycle:
    """AC-4, AC-5: Scheduler start/stop lifecycle management."""

    def _make_scheduler(self, **overrides: object) -> NotificationScheduler:
        """Create a scheduler with mocked dependencies."""
        settings = MagicMock()
        settings.batch_summary_hour = 8
        settings.batch_summary_minute = 0
        settings.weekly_report_day = 0
        settings.weekly_report_hour = 8
        settings.weekly_report_minute = 0
        for key, val in overrides.items():
            setattr(settings, key, val)
        return NotificationScheduler(
            schedule_settings=settings,
            session_factory=AsyncMock(),
            adapter=AsyncMock(),
            erp_settings=MagicMock(),
        )

    async def test_start_creates_tasks(self) -> None:
        """AC-4, AC-5: start() spawns background tasks."""
        scheduler = self._make_scheduler()
        with patch("quote_agent.services.notification_scheduler.seconds_until", return_value=3600.0):
            scheduler.start()
        assert scheduler._daily_task is not None
        assert scheduler._weekly_task is not None
        scheduler.stop()

    async def test_stop_cancels_tasks(self) -> None:
        """AC-4, AC-5: stop() cancels background tasks."""
        scheduler = self._make_scheduler()
        with patch("quote_agent.services.notification_scheduler.seconds_until", return_value=3600.0):
            scheduler.start()
        scheduler.stop()
        assert scheduler._daily_task is None or scheduler._daily_task.cancelled()
        assert scheduler._weekly_task is None or scheduler._weekly_task.cancelled()

    async def test_double_start_is_safe(self) -> None:
        """AC-4: Starting an already running scheduler is idempotent."""
        scheduler = self._make_scheduler()
        with patch("quote_agent.services.notification_scheduler.seconds_until", return_value=3600.0):
            scheduler.start()
            scheduler.start()  # Should not crash
        scheduler.stop()

    async def test_double_stop_is_safe(self) -> None:
        """AC-4: Stopping an already stopped scheduler is idempotent."""
        scheduler = self._make_scheduler()
        scheduler.stop()  # Should not crash
        scheduler.stop()


class TestSchedulerSkip:
    """AC-4, AC-5: Scheduler skip conditions."""

    def test_skip_when_scheduler_disabled(self) -> None:
        """AC-4: Scheduler does not start when scheduler_enabled=False."""
        schedule_settings = MagicMock()
        schedule_settings.scheduler_enabled = False
        scheduler = NotificationScheduler(
            schedule_settings=schedule_settings,
            session_factory=AsyncMock(),
            adapter=AsyncMock(),
            erp_settings=MagicMock(),
        )
        # When disabled, should_run returns False
        assert scheduler.should_run() is False

    def test_skip_when_webhook_empty(self) -> None:
        """AC-4: Scheduler does not start when webhook URL is empty."""
        schedule_settings = MagicMock()
        schedule_settings.scheduler_enabled = True
        adapter = MagicMock()
        adapter.hostname = ""
        scheduler = NotificationScheduler(
            schedule_settings=schedule_settings,
            session_factory=AsyncMock(),
            adapter=adapter,
            erp_settings=MagicMock(),
        )
        assert scheduler.should_run() is False

    def test_should_run_when_enabled_and_configured(self) -> None:
        """AC-4: Scheduler should run when enabled and webhook is configured."""
        schedule_settings = MagicMock()
        schedule_settings.scheduler_enabled = True
        adapter = MagicMock()
        adapter.hostname = "webhook.office.com"
        scheduler = NotificationScheduler(
            schedule_settings=schedule_settings,
            session_factory=AsyncMock(),
            adapter=adapter,
            erp_settings=MagicMock(),
        )
        assert scheduler.should_run() is True
