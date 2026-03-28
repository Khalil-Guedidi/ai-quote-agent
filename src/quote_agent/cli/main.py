"""CLI entry point — Typer application with sub-commands."""

from __future__ import annotations

import asyncio

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

    asyncio.run(
        _classify_impl(
            description=description,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
            json_output=json_output,
        )
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

    asyncio.run(
        _score_impl(
            description=description,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
            limit=limit,
            json_output=json_output,
        )
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

    asyncio.run(
        _reason_impl(
            description=description,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
            json_output=json_output,
        )
    )


@app.command()
def review(
    description: str = typer.Argument(..., help="Quote request description to review"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    client: str | None = typer.Option(None, "--client", "-c", help="Client name for sanctions check"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Run full pipeline with self-review validation gate and compliance check."""
    from quote_agent.cli.review import review as _review_impl

    asyncio.run(
        _review_impl(
            description=description,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
            client=client,
            json_output=json_output,
        )
    )


@app.command()
def compliance(
    description: str = typer.Argument(..., help="Product description to check for compliance"),
    client: str | None = typer.Option(None, "--client", "-c", help="Client name to check against sanctions lists"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Run export control and sanctions compliance check."""
    from quote_agent.cli.compliance import compliance as _compliance_impl

    asyncio.run(
        _compliance_impl(
            description=description,
            client=client,
            json_output=json_output,
        )
    )


@app.command()
def erp_read(
    client: str | None = typer.Option(None, "--client", "-c", help="Client ID or ref to read from Odoo"),
    product: int | None = typer.Option(None, "--product", "-p", help="Product Odoo ID to read"),
    orders: str | None = typer.Option(None, "--orders", "-o", help="Client ID to fetch order history"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max orders to fetch"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Read client data, product details, or order history from Odoo ERP."""
    from quote_agent.cli.erp_read import erp_read as _erp_read_impl

    asyncio.run(_erp_read_impl(client=client, product=product, orders=orders, limit=limit, json_output=json_output))


@app.command()
def draft_create(
    client: str = typer.Option(..., "--client", "-c", help="Client ID or ref"),
    product: int = typer.Option(..., "--product", "-p", help="Product Odoo ID"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Quantity"),
    price: float | None = typer.Option(None, "--price", help="Unit price override"),
    description: str | None = typer.Option(None, "--description", "-d", help="Line description"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a draft quote in Odoo ERP."""
    from quote_agent.cli.draft_create import draft_create as _draft_create_impl

    asyncio.run(
        _draft_create_impl(
            client=client,
            product=product,
            quantity=quantity,
            price=price,
            description=description,
            json_output=json_output,
        )
    )


@app.command(name="process")
def process_cmd(
    description: str = typer.Argument(..., help="Quote request description to process"),
    client: str | None = typer.Option(None, "--client", "-c", help="Client name or ID"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Process a quote request through the full LangGraph agent pipeline."""
    from quote_agent.cli.process import process as _process_impl

    asyncio.run(
        _process_impl(
            description=description,
            client=client,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
            json_output=json_output,
        )
    )


@app.command(name="notify-test")
def notify_test(
    message: str = typer.Option("Test notification from AI Quote Agent", "--message", "-m", help="Custom test message"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Send a test notification to Teams via the configured webhook."""
    from quote_agent.cli.notify_test import notify_test as _notify_test_impl

    asyncio.run(_notify_test_impl(message=message, json_output=json_output))


@app.command(name="batch-summary")
def batch_summary_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Send a batch summary notification for today's processed quotes."""
    from quote_agent.cli.batch_notify import batch_summary as _batch_summary_impl

    asyncio.run(_batch_summary_impl(json_output=json_output))


@app.command(name="weekly-report")
def weekly_report_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Send a weekly report notification for the last 7 days."""
    from quote_agent.cli.batch_notify import weekly_report as _weekly_report_impl

    asyncio.run(_weekly_report_impl(json_output=json_output))


@app.command(name="manager-stats")
def manager_stats_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Send an on-demand manager stats notification."""
    from quote_agent.cli.batch_notify import manager_stats as _manager_stats_impl

    asyncio.run(_manager_stats_impl(json_output=json_output))


@app.command(name="scheduler-status")
def scheduler_status_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Check notification scheduler status and next scheduled sends."""
    from quote_agent.cli.scheduler_status import scheduler_status as _scheduler_status_impl

    _scheduler_status_impl(json_output=json_output)


@app.command(name="seed-odoo")
def seed_odoo_cmd(
    count: int = typer.Option(200, "--count", "-n", help="Number of products to seed"),
    clean: bool = typer.Option(False, "--clean", help="Remove all seeded data instead of seeding"),
) -> None:
    """Populate test Odoo with realistic industrial data (products, clients, orders)."""
    from quote_agent.cli.seed_odoo import seed_odoo as _seed_odoo_impl

    asyncio.run(_seed_odoo_impl(count=count, clean=clean))


@app.command(name="kb-ingest")
def kb_ingest_cmd(
    file_path: str = typer.Argument(..., help="Path to the document file to ingest (.md or .txt)"),
    title: str | None = typer.Option(None, "--title", "-t", help="Document title (defaults to filename)"),
) -> None:
    """Ingest a document into the industry knowledge base."""
    from quote_agent.cli.knowledge_base import kb_ingest as _kb_ingest_impl

    asyncio.run(_kb_ingest_impl(file_path=file_path, title=title))


@app.command(name="kb-search")
def kb_search_cmd(
    query: str = typer.Argument(..., help="Search query for the knowledge base"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
) -> None:
    """Search the industry knowledge base."""
    from quote_agent.cli.knowledge_base import kb_search as _kb_search_impl

    asyncio.run(_kb_search_impl(query=query, top_k=top_k))


@app.command(name="kb-list")
def kb_list_cmd() -> None:
    """List all documents in the industry knowledge base."""
    from quote_agent.cli.knowledge_base import kb_list as _kb_list_impl

    asyncio.run(_kb_list_impl())


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

    asyncio.run(
        _search_impl(
            query=query,
            limit=limit,
            method=method,
            no_filter=no_filter,
            include_stale=include_stale,
            json_output=json_output,
        )
    )
