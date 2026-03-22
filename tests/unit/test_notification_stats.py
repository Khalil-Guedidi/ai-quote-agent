"""Tests for notification stats query service — daily summary and weekly report."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from quote_agent.services.notification_stats import (
    DailySummary,
    RepStats,
    WeeklyReport,
    get_daily_summary,
    get_weekly_report,
)


def _make_quote_row(
    confidence: float | None = None,
    status: str = "processed",
    updated_at: datetime | None = None,
) -> MagicMock:
    """Create a mock QuoteRequest row."""
    row = MagicMock()
    row.id = uuid.uuid4()
    row.confidence = confidence
    row.status = status
    row.updated_at = updated_at or datetime.now(tz=UTC)
    row.email_request_id = uuid.uuid4()
    return row


def _mock_session_with_rows(rows: list[MagicMock]) -> AsyncMock:
    """Create a mock AsyncSession that returns the given rows from execute()."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    session.execute = AsyncMock(return_value=mock_result)
    return session


# --- get_daily_summary() Tests ---


async def test_daily_summary_groups_by_confidence_tier() -> None:
    """AC-1: get_daily_summary correctly groups quotes by confidence tier."""
    rows = [
        _make_quote_row(confidence=0.92),   # high (>= 0.85)
        _make_quote_row(confidence=0.88),   # high
        _make_quote_row(confidence=0.70),   # medium (>= 0.50)
        _make_quote_row(confidence=0.55),   # medium
        _make_quote_row(confidence=0.30),   # low (< 0.50)
        _make_quote_row(confidence=None),   # low (NULL)
    ]
    session = _mock_session_with_rows(rows)

    result = await get_daily_summary(session)

    assert isinstance(result, DailySummary)
    assert result.total == 6
    assert result.high_count == 2
    assert result.medium_count == 2
    assert result.low_count == 2


async def test_daily_summary_empty_when_no_quotes() -> None:
    """AC-1: get_daily_summary returns zero counts when no quotes processed."""
    session = _mock_session_with_rows([])

    result = await get_daily_summary(session)

    assert result.total == 0
    assert result.high_count == 0
    assert result.medium_count == 0
    assert result.low_count == 0


async def test_daily_summary_all_high_confidence() -> None:
    """AC-1: get_daily_summary handles all-high scenario."""
    rows = [
        _make_quote_row(confidence=0.95),
        _make_quote_row(confidence=0.90),
        _make_quote_row(confidence=0.85),
    ]
    session = _mock_session_with_rows(rows)

    result = await get_daily_summary(session)

    assert result.high_count == 3
    assert result.medium_count == 0
    assert result.low_count == 0


async def test_daily_summary_boundary_confidence_values() -> None:
    """AC-1: get_daily_summary correctly classifies boundary values."""
    rows = [
        _make_quote_row(confidence=0.85),   # high (exactly at threshold)
        _make_quote_row(confidence=0.8499),  # medium (just below high)
        _make_quote_row(confidence=0.50),   # medium (exactly at low threshold)
        _make_quote_row(confidence=0.4999),  # low (just below medium)
    ]
    session = _mock_session_with_rows(rows)

    result = await get_daily_summary(session)

    assert result.high_count == 1
    assert result.medium_count == 2
    assert result.low_count == 1


async def test_daily_summary_has_date_field() -> None:
    """AC-1: get_daily_summary includes the current date."""
    session = _mock_session_with_rows([])

    result = await get_daily_summary(session)

    assert result.date is not None
    assert result.date.tzinfo is not None


# --- get_weekly_report() Tests ---


def _mock_session_for_weekly(
    current_rows: list[tuple[MagicMock, str]],
    prev_count: int = 0,
) -> AsyncMock:
    """Create a mock session that returns current week rows and previous week count."""
    session = AsyncMock()

    # First call returns current week rows, second call returns prev week count
    current_result = MagicMock()
    current_result.all.return_value = current_rows

    prev_result = MagicMock()
    prev_result.scalar.return_value = prev_count

    session.execute = AsyncMock(side_effect=[current_result, prev_result])
    return session


async def test_weekly_report_correct_aggregation() -> None:
    """AC-2: get_weekly_report computes total and avg confidence."""
    rows = [
        (_make_quote_row(confidence=0.90), "alice@test.com"),
        (_make_quote_row(confidence=0.80), "alice@test.com"),
        (_make_quote_row(confidence=0.70), "bob@test.com"),
    ]
    session = _mock_session_for_weekly(rows, prev_count=2)

    result = await get_weekly_report(session)

    assert isinstance(result, WeeklyReport)
    assert result.total == 3
    assert result.avg_confidence == 80  # (90+80+70)/3 = 80%


async def test_weekly_report_rep_breakdown() -> None:
    """AC-2: get_weekly_report groups by sender for per-rep breakdown."""
    rows = [
        (_make_quote_row(confidence=0.90), "alice@test.com"),
        (_make_quote_row(confidence=0.80), "alice@test.com"),
        (_make_quote_row(confidence=0.70), "bob@test.com"),
    ]
    session = _mock_session_for_weekly(rows)

    result = await get_weekly_report(session)

    assert len(result.rep_breakdown) == 2
    alice = next(r for r in result.rep_breakdown if r.rep_name == "alice@test.com")
    assert alice.quotes_count == 2
    assert alice.avg_confidence_pct == 85  # (90+80)/2 = 85%

    bob = next(r for r in result.rep_breakdown if r.rep_name == "bob@test.com")
    assert bob.quotes_count == 1
    assert bob.avg_confidence_pct == 70


async def test_weekly_report_trend_calculation_positive() -> None:
    """AC-2: get_weekly_report computes positive trend correctly."""
    rows = [
        (_make_quote_row(confidence=0.90), "alice@test.com"),
        (_make_quote_row(confidence=0.80), "alice@test.com"),
        (_make_quote_row(confidence=0.70), "bob@test.com"),
    ]
    session = _mock_session_for_weekly(rows, prev_count=2)

    result = await get_weekly_report(session)

    assert result.trend_pct == 50  # (3-2)/2 * 100 = 50%
    assert result.trend_direction == "up"


async def test_weekly_report_trend_calculation_negative() -> None:
    """AC-2: get_weekly_report computes negative trend correctly."""
    rows = [
        (_make_quote_row(confidence=0.90), "alice@test.com"),
    ]
    session = _mock_session_for_weekly(rows, prev_count=4)

    result = await get_weekly_report(session)

    assert result.trend_pct == -75  # (1-4)/4 * 100 = -75%
    assert result.trend_direction == "down"


async def test_weekly_report_trend_zero_when_no_previous() -> None:
    """AC-2: get_weekly_report returns zero trend when no previous week data."""
    rows = [
        (_make_quote_row(confidence=0.90), "alice@test.com"),
    ]
    session = _mock_session_for_weekly(rows, prev_count=0)

    result = await get_weekly_report(session)

    assert result.trend_pct == 0
    assert result.trend_direction == "stable"


async def test_weekly_report_empty() -> None:
    """AC-2: get_weekly_report handles empty data."""
    session = _mock_session_for_weekly([], prev_count=0)

    result = await get_weekly_report(session)

    assert result.total == 0
    assert result.avg_confidence == 0
    assert result.rep_breakdown == []
    assert result.trend_pct == 0
    assert result.trend_direction == "stable"


async def test_weekly_report_null_confidence_excluded_from_avg() -> None:
    """AC-2: get_weekly_report excludes NULL confidence from average calculation."""
    rows = [
        (_make_quote_row(confidence=0.90), "alice@test.com"),
        (_make_quote_row(confidence=None), "bob@test.com"),
    ]
    session = _mock_session_for_weekly(rows)

    result = await get_weekly_report(session)

    assert result.total == 2
    assert result.avg_confidence == 90  # Only the non-null value


async def test_weekly_report_has_period_fields() -> None:
    """AC-2: get_weekly_report includes period start and end."""
    session = _mock_session_for_weekly([])

    result = await get_weekly_report(session)

    assert result.period_start is not None
    assert result.period_end is not None
    assert result.period_end > result.period_start


# --- DTO Tests ---


def test_daily_summary_dto_fields() -> None:
    """AC-1: DailySummary DTO has all required fields."""
    summary = DailySummary(
        total=10, high_count=5, medium_count=3, low_count=2,
        date=datetime.now(tz=UTC),
    )
    assert summary.total == 10
    assert summary.high_count == 5
    assert summary.medium_count == 3
    assert summary.low_count == 2


def test_weekly_report_dto_fields() -> None:
    """AC-2: WeeklyReport DTO has all required fields."""
    now = datetime.now(tz=UTC)
    report = WeeklyReport(
        total=20,
        avg_confidence=85,
        rep_breakdown=[
            RepStats(rep_name="alice@test.com", quotes_count=10, avg_confidence_pct=90),
        ],
        trend_pct=5,
        trend_direction="up",
        period_start=now - timedelta(days=7),
        period_end=now,
    )
    assert report.total == 20
    assert report.avg_confidence == 85
    assert len(report.rep_breakdown) == 1


def test_rep_stats_dto_fields() -> None:
    """AC-2: RepStats DTO has all required fields."""
    rep = RepStats(rep_name="alice@test.com", quotes_count=5, avg_confidence_pct=88)
    assert rep.rep_name == "alice@test.com"
    assert rep.quotes_count == 5
    assert rep.avg_confidence_pct == 88
