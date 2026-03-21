"""CLI entry point — Typer application with sub-commands."""

from __future__ import annotations

import typer

from quote_agent.cli.logs import logs
from quote_agent.cli.status import status

app = typer.Typer(name="agent", help="AI Quote Agent CLI")
app.command()(status)
app.command()(logs)


@app.command()
def classify(
    description: str = typer.Argument(..., help="Quote request description to classify"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Classify the complexity of a quote request."""
    from quote_agent.cli.classify import classify as _classify_impl

    _classify_impl(
        description=description,
        quantity=quantity,
        reference=reference,
        urgency=urgency,
        json_output=json_output,
    )


@app.command()
def score(
    description: str = typer.Argument(..., help="Quote request description to score"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of search results to score"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Score confidence of product matches and route by tier."""
    from quote_agent.cli.score import score as _score_impl

    _score_impl(
        description=description,
        quantity=quantity,
        reference=reference,
        urgency=urgency,
        limit=limit,
        json_output=json_output,
    )


@app.command()
def reason(
    description: str = typer.Argument(..., help="Quote request description to reason about"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Apply adaptive reasoning strategy and score confidence."""
    from quote_agent.cli.reason import reason as _reason_impl

    _reason_impl(
        description=description,
        quantity=quantity,
        reference=reference,
        urgency=urgency,
        json_output=json_output,
    )


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
