"""CLI entry point — Typer application with sub-commands."""

from __future__ import annotations

import typer

from quote_agent.cli.logs import logs
from quote_agent.cli.status import status

app = typer.Typer(name="agent", help="AI Quote Agent CLI")
app.command()(status)
app.command()(logs)
