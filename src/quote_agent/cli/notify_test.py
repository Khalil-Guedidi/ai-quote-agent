"""CLI notify-test command — sends a test Teams Adaptive Card via webhook."""

from __future__ import annotations

import asyncio
import json as json_lib

import typer

from quote_agent.adapters.notification.models import NotificationPayload, NotificationResult

_DEFAULT_MESSAGE = "Test notification from AI Quote Agent"


async def _run_notify_test(message: str) -> tuple[NotificationResult, str]:
    """Send a test notification and return the result with the webhook hostname."""
    from quote_agent.adapters.notification import get_notification_adapter

    adapter = get_notification_adapter()
    payload = NotificationPayload(
        title="Test Notification",
        message=message,
    )
    result = await adapter.send_notification(payload)
    return result, adapter._hostname


def _format_result(result: NotificationResult, hostname: str) -> None:
    """Display notification result as formatted output."""
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


def notify_test(
    message: str = typer.Option(_DEFAULT_MESSAGE, "--message", "-m", help="Custom test message"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Send a test notification to Teams via the configured webhook."""
    try:
        result, hostname = asyncio.run(_run_notify_test(message))
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    if json_output:
        data = result.model_dump(mode="json")
        data["webhook_hostname"] = hostname
        typer.echo(json_lib.dumps(data, indent=2))
    else:
        _format_result(result, hostname)

    if not result.success:
        raise typer.Exit(code=1)
