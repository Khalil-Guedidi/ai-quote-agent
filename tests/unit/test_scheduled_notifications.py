"""Tests for scheduled notification service — batch summary and weekly report sending."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quote_agent.adapters.notification.models import NotificationResult
from quote_agent.services.notification_stats import DailySummary, RepStats, WeeklyReport
from quote_agent.services.scheduled_notifications import (
    send_batch_summary,
    send_manager_stats,
    send_weekly_report,
)


@pytest.fixture()
def mock_adapter() -> MagicMock:
    """Create a mock TeamsAdapter."""
    adapter = MagicMock()
    adapter.send_notification = AsyncMock(
        return_value=NotificationResult(
            success=True,
            status_code=200,
            timestamp=datetime.now(tz=UTC),
        )
    )
    return adapter


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    return AsyncMock()


# --- send_batch_summary() Tests ---


@patch("quote_agent.services.scheduled_notifications.get_daily_summary")
async def test_send_batch_summary_success(
    mock_get_daily: AsyncMock,
    mock_adapter: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """AC-1: send_batch_summary sends notification with correct card type."""
    mock_get_daily.return_value = DailySummary(
        total=5,
        high_count=2,
        medium_count=2,
        low_count=1,
        date=datetime.now(tz=UTC),
    )

    result = await send_batch_summary(mock_session, mock_adapter)

    assert result is not None
    assert result.success is True
    mock_adapter.send_notification.assert_called_once()
    payload = mock_adapter.send_notification.call_args[0][0]
    assert payload.card_type == "batch-summary"
    assert "5 devis" in payload.message
    assert "2 prêts" in payload.message
    assert payload.data["erp_url"].endswith("/erp/sale-orders")


@patch("quote_agent.services.scheduled_notifications.get_daily_summary")
async def test_send_batch_summary_skips_when_no_quotes(
    mock_get_daily: AsyncMock,
    mock_adapter: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """AC-1: send_batch_summary returns None when no quotes processed (silence principle)."""
    mock_get_daily.return_value = DailySummary(
        total=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        date=datetime.now(tz=UTC),
    )

    result = await send_batch_summary(mock_session, mock_adapter)

    assert result is None
    mock_adapter.send_notification.assert_not_called()


@patch("quote_agent.services.scheduled_notifications.get_daily_summary")
async def test_send_batch_summary_fire_and_forget_on_error(
    mock_get_daily: AsyncMock,
    mock_adapter: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """AC-1: send_batch_summary catches exceptions and returns None (fire-and-forget)."""
    mock_get_daily.side_effect = RuntimeError("DB connection failed")

    result = await send_batch_summary(mock_session, mock_adapter)

    assert result is None


# --- send_weekly_report() Tests ---


@patch("quote_agent.services.scheduled_notifications.get_weekly_report")
async def test_send_weekly_report_success(
    mock_get_weekly: AsyncMock,
    mock_adapter: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """AC-2: send_weekly_report sends notification with correct card type and rep data."""
    now = datetime.now(tz=UTC)
    mock_get_weekly.return_value = WeeklyReport(
        total=15,
        avg_confidence=82,
        rep_breakdown=[
            RepStats(rep_name="alice@test.com", quotes_count=8, avg_confidence_pct=88),
            RepStats(rep_name="bob@test.com", quotes_count=7, avg_confidence_pct=75),
        ],
        trend_pct=10,
        trend_direction="up",
        period_start=now,
        period_end=now,
    )

    result = await send_weekly_report(mock_session, mock_adapter)

    assert result is not None
    assert result.success is True
    mock_adapter.send_notification.assert_called_once()
    payload = mock_adapter.send_notification.call_args[0][0]
    assert payload.card_type == "manager-weekly"
    assert "15 devis" in payload.message
    assert "82%" in payload.message
    assert len(payload.data["rep_breakdown"]) == 2


@patch("quote_agent.services.scheduled_notifications.get_weekly_report")
async def test_send_weekly_report_skips_when_no_quotes(
    mock_get_weekly: AsyncMock,
    mock_adapter: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """AC-2: send_weekly_report returns None when no quotes processed (silence principle)."""
    now = datetime.now(tz=UTC)
    mock_get_weekly.return_value = WeeklyReport(
        total=0,
        avg_confidence=0,
        rep_breakdown=[],
        trend_pct=0,
        trend_direction="stable",
        period_start=now,
        period_end=now,
    )

    result = await send_weekly_report(mock_session, mock_adapter)

    assert result is None
    mock_adapter.send_notification.assert_not_called()


@patch("quote_agent.services.scheduled_notifications.get_weekly_report")
async def test_send_weekly_report_fire_and_forget_on_error(
    mock_get_weekly: AsyncMock,
    mock_adapter: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """AC-2: send_weekly_report catches exceptions and returns None (fire-and-forget)."""
    mock_get_weekly.side_effect = RuntimeError("DB connection failed")

    result = await send_weekly_report(mock_session, mock_adapter)

    assert result is None


# --- send_manager_stats() Tests ---


@patch("quote_agent.services.scheduled_notifications.get_weekly_report")
@patch("quote_agent.services.scheduled_notifications.get_daily_summary")
async def test_send_manager_stats_success(
    mock_get_daily: AsyncMock,
    mock_get_weekly: AsyncMock,
    mock_adapter: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """AC-3: send_manager_stats sends notification with correct card type and real avg_confidence."""
    now = datetime.now(tz=UTC)
    mock_get_daily.return_value = DailySummary(
        total=8,
        high_count=3,
        medium_count=3,
        low_count=2,
        date=now,
    )
    mock_get_weekly.return_value = WeeklyReport(
        total=8,
        avg_confidence=78,
        rep_breakdown=[],
        trend_pct=0,
        trend_direction="stable",
        period_start=now,
        period_end=now,
    )

    result = await send_manager_stats(mock_session, mock_adapter)

    assert result is not None
    assert result.success is True
    mock_adapter.send_notification.assert_called_once()
    payload = mock_adapter.send_notification.call_args[0][0]
    assert payload.card_type == "manager-stats"
    assert "8 devis" in payload.message
    assert payload.data["avg_confidence"] == 78
