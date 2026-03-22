"""Stats query service for batch summary and weekly report notifications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import func, select

from quote_agent.models.email_request import EmailRequest
from quote_agent.models.quote_request import QuoteRequest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RepStats(BaseModel):
    """Per-rep breakdown for weekly report."""

    rep_name: str
    quotes_count: int
    avg_confidence_pct: int


class DailySummary(BaseModel):
    """Aggregated daily summary of processed quotes by confidence tier."""

    total: int
    high_count: int
    medium_count: int
    low_count: int
    date: datetime


class WeeklyReport(BaseModel):
    """Aggregated weekly report with per-rep breakdown and trend."""

    total: int
    avg_confidence: int
    rep_breakdown: list[RepStats]
    trend_pct: int
    trend_direction: str
    period_start: datetime
    period_end: datetime


async def get_daily_summary(
    session: AsyncSession,
    *,
    high_threshold: float = 0.85,
    low_threshold: float = 0.50,
) -> DailySummary:
    """Query quote_requests processed today, grouped by confidence tier.

    Thresholds default to ConfidenceScoringSettings values but can be overridden.
    - high: confidence >= high_threshold
    - medium: low_threshold <= confidence < high_threshold
    - low: confidence < low_threshold OR confidence IS NULL
    """
    now = datetime.now(tz=UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = select(QuoteRequest).where(
        QuoteRequest.status != "pending",
        QuoteRequest.updated_at >= today_start,
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    high = 0
    medium = 0
    low = 0
    for row in rows:
        if row.confidence is not None and row.confidence >= high_threshold:
            high += 1
        elif row.confidence is not None and row.confidence >= low_threshold:
            medium += 1
        else:
            low += 1

    return DailySummary(
        total=len(rows),
        high_count=high,
        medium_count=medium,
        low_count=low,
        date=now,
    )


async def get_weekly_report(session: AsyncSession) -> WeeklyReport:
    """Query quote_requests from last 7 days with per-rep breakdown and trend.

    Uses email_requests.sender as the rep identifier via FK join.
    """
    now = datetime.now(tz=UTC)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    # Current week quotes
    stmt = (
        select(QuoteRequest, EmailRequest.sender)
        .join(EmailRequest, QuoteRequest.email_request_id == EmailRequest.id)
        .where(
            QuoteRequest.status != "pending",
            QuoteRequest.updated_at >= week_start,
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    total = len(rows)
    confidences = [r[0].confidence for r in rows if r[0].confidence is not None]
    avg_conf = int(sum(confidences) / len(confidences) * 100) if confidences else 0

    # Per-rep breakdown
    rep_data: dict[str, list[float | None]] = {}
    for quote, sender in rows:
        rep_data.setdefault(sender, []).append(quote.confidence)

    rep_breakdown = []
    for rep_name, confs in sorted(rep_data.items()):
        valid_confs = [c for c in confs if c is not None]
        avg_pct = int(sum(valid_confs) / len(valid_confs) * 100) if valid_confs else 0
        rep_breakdown.append(RepStats(
            rep_name=rep_name,
            quotes_count=len(confs),
            avg_confidence_pct=avg_pct,
        ))

    # Previous week count for trend
    prev_stmt = (
        select(func.count())
        .select_from(QuoteRequest)
        .where(
            QuoteRequest.status != "pending",
            QuoteRequest.updated_at >= prev_week_start,
            QuoteRequest.updated_at < week_start,
        )
    )
    prev_result = await session.execute(prev_stmt)
    prev_total = prev_result.scalar() or 0

    trend_pct = int((total - prev_total) / prev_total * 100) if prev_total > 0 else 0

    trend_direction = "up" if trend_pct > 0 else "down" if trend_pct < 0 else "stable"

    return WeeklyReport(
        total=total,
        avg_confidence=avg_conf,
        rep_breakdown=rep_breakdown,
        trend_pct=trend_pct,
        trend_direction=trend_direction,
        period_start=week_start,
        period_end=now,
    )
