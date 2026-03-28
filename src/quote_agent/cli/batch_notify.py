"""CLI commands for batch summary, weekly report, and on-demand manager stats."""

from __future__ import annotations

import json as json_lib
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.adapters.notification.models import NotificationResult


async def _run_batch_summary() -> tuple[NotificationResult | None, str]:
    """Execute batch summary notification and return result + hostname."""
    from quote_agent.adapters.notification import get_notification_adapter
    from quote_agent.models.base import _get_session_factory
    from quote_agent.services.scheduled_notifications import send_batch_summary

    adapter = get_notification_adapter()
    factory = _get_session_factory()
    async with factory() as session:
        result = await send_batch_summary(session, adapter)
    return result, getattr(adapter, "hostname", "unknown")


async def _run_weekly_report() -> tuple[NotificationResult | None, str]:
    """Execute weekly report notification and return result + hostname."""
    from quote_agent.adapters.notification import get_notification_adapter
    from quote_agent.models.base import _get_session_factory
    from quote_agent.services.scheduled_notifications import send_weekly_report

    adapter = get_notification_adapter()
    factory = _get_session_factory()
    async with factory() as session:
        result = await send_weekly_report(session, adapter)
    return result, getattr(adapter, "hostname", "unknown")


async def _run_manager_stats() -> tuple[NotificationResult | None, str]:
    """Execute on-demand manager stats and return result + hostname."""
    from quote_agent.adapters.notification import get_notification_adapter
    from quote_agent.models.base import _get_session_factory
    from quote_agent.services.scheduled_notifications import send_manager_stats

    adapter = get_notification_adapter()
    factory = _get_session_factory()
    async with factory() as session:
        result = await send_manager_stats(session, adapter)
    return result, getattr(adapter, "hostname", "unknown")


def _display_result(result: NotificationResult | None, hostname: str, json_output: bool) -> None:
    """Display notification result to CLI."""
    if result is None:
        if json_output:
            typer.echo(json_lib.dumps({"skipped": True, "reason": "no data to report"}, indent=2))
        else:
            typer.echo(typer.style("Skipped", fg=typer.colors.YELLOW, bold=True) + " — no data to report")
        return

    if json_output:
        data = result.model_dump(mode="json")
        data["webhook_hostname"] = hostname
        typer.echo(json_lib.dumps(data, indent=2))
    else:
        if result.success:
            status_text = typer.style("success", fg=typer.colors.GREEN, bold=True)
        else:
            status_text = typer.style("failure", fg=typer.colors.RED, bold=True)

        typer.echo(f"Delivery: {status_text}")
        if result.status_code is not None:
            typer.echo(f"HTTP:     {result.status_code}")
        typer.echo(f"Webhook:  {hostname}")
        if result.error:
            typer.echo(f"Error:    {result.error}")

    if result is not None and not result.success:
        raise typer.Exit(code=1)


async def batch_summary(
    json_output: bool = False,
) -> None:
    """Send a batch summary notification for today's processed quotes."""
    try:
        result, hostname = await _run_batch_summary()
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    _display_result(result, hostname, json_output)


async def weekly_report(
    json_output: bool = False,
) -> None:
    """Send a weekly report notification for the last 7 days."""
    try:
        result, hostname = await _run_weekly_report()
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    _display_result(result, hostname, json_output)


async def manager_stats(
    json_output: bool = False,
) -> None:
    """Send an on-demand manager stats notification."""
    try:
        result, hostname = await _run_manager_stats()
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    _display_result(result, hostname, json_output)
