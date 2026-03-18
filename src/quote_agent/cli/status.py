"""CLI status command — displays per-service health from /health endpoint."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen

import typer


def status(
    host: str = typer.Option("localhost", help="API server host"),
    port: int = typer.Option(8000, help="API server port"),
) -> None:
    """Show per-service health status."""
    url = f"http://{host}:{port}/health"

    try:
        with urlopen(url, timeout=5) as response:
            body = json.loads(response.read().decode())
    except (URLError, OSError) as exc:
        typer.echo(typer.style("Error: Could not connect to the agent.", fg=typer.colors.RED))
        typer.echo(f"  Ensure the app is running at {url}")
        typer.echo(f"  Details: {exc}")
        raise typer.Exit(code=1) from None

    data = body.get("data", {})
    overall = data.get("status", "unknown")
    services: dict[str, dict[str, str | None]] = data.get("services", {})

    overall_color = typer.colors.GREEN if overall == "healthy" else typer.colors.YELLOW
    typer.echo(typer.style("Agent Status", bold=True))
    typer.echo("─" * 40)
    typer.echo(f"Overall: {typer.style(overall, fg=overall_color)}")
    typer.echo()
    typer.echo("Services:")

    for name, info in services.items():
        svc_status = info.get("status", "unknown")
        error = info.get("error")
        if svc_status == "healthy":
            indicator = typer.style("healthy ✓", fg=typer.colors.GREEN)
        else:
            indicator = typer.style("unhealthy ✗", fg=typer.colors.RED)
        line = f"  {name:<15} {indicator}"
        if error:
            line += f"  {error}"
        typer.echo(line)
