"""CLI entry point — Typer application with sub-commands."""

from __future__ import annotations

import typer

from quote_agent.cli.logs import logs
from quote_agent.cli.status import status

app = typer.Typer(name="agent", help="AI Quote Agent CLI")
app.command()(status)
app.command()(logs)


@app.command()
def search(
    query: str = typer.Argument(..., help="Product search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of results"),
    method: str = typer.Option(
        "hybrid",
        "--method",
        "-m",
        help="Search method: hybrid, semantic, or keyword",
    ),
    no_filter: bool = typer.Option(False, "--no-filter", help="Disable proposability filter"),
    include_stale: bool = typer.Option(False, "--include-stale", help="Include stale products"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
) -> None:
    """Search the product catalog and display results."""
    from quote_agent.cli.search import search as _search_impl

    _search_impl(
        query=query,
        limit=limit,
        method=method,
        no_filter=no_filter,
        include_stale=include_stale,
        json_output=json_output,
    )
