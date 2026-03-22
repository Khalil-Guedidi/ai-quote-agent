"""CLI command for checking notification scheduler status."""

from __future__ import annotations

import json as json_lib

import typer


def scheduler_status(
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Check if the notification scheduler would run and when next sends are due."""
    from quote_agent.config import get_settings
    from quote_agent.services.notification_scheduler import seconds_until

    settings = get_settings()
    schedule = settings.notification_schedule
    enabled = schedule.scheduler_enabled
    has_webhook = bool(settings.notification.teams_webhook_url)
    would_run = enabled and has_webhook

    next_daily = seconds_until(schedule.batch_summary_hour, schedule.batch_summary_minute)
    next_weekly = seconds_until(
        schedule.weekly_report_hour, schedule.weekly_report_minute,
        target_weekday=schedule.weekly_report_day,
    )

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if json_output:
        data = {
            "scheduler_enabled": enabled,
            "webhook_configured": has_webhook,
            "would_run": would_run,
            "daily_schedule": f"{schedule.batch_summary_hour:02d}:{schedule.batch_summary_minute:02d} UTC",
            "weekly_schedule": (
                f"{days[schedule.weekly_report_day]} "
                f"{schedule.weekly_report_hour:02d}:{schedule.weekly_report_minute:02d} UTC"
            ),
            "next_daily_seconds": round(next_daily),
            "next_weekly_seconds": round(next_weekly),
        }
        typer.echo(json_lib.dumps(data, indent=2))
    else:
        if would_run:
            status_icon = typer.style("ON", fg=typer.colors.GREEN, bold=True)
        else:
            status_icon = typer.style("OFF", fg=typer.colors.RED, bold=True)
        typer.echo(f"Scheduler:    {status_icon}")
        typer.echo(f"Enabled:      {enabled}")
        typer.echo(f"Webhook:      {'configured' if has_webhook else 'not configured'}")
        daily_time = f"{schedule.batch_summary_hour:02d}:{schedule.batch_summary_minute:02d}"
        typer.echo(f"Daily:        {daily_time} UTC (in {_format_duration(next_daily)})")
        weekly_time = f"{schedule.weekly_report_hour:02d}:{schedule.weekly_report_minute:02d}"
        typer.echo(
            f"Weekly:       {days[schedule.weekly_report_day]} "
            f"{weekly_time} UTC (in {_format_duration(next_weekly)})"
        )


def _format_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m"
