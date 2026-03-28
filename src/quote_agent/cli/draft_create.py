"""CLI draft-create command — create a draft quote in Odoo ERP."""

from __future__ import annotations

import typer

from quote_agent.adapters.erp.models import QuoteDraftResult, UniversalQuote, UniversalQuoteLine


async def _create_draft(
    client: str,
    product: int,
    quantity: float,
    price: float | None,
    description: str | None,
) -> QuoteDraftResult:
    """Build a UniversalQuote and create a draft in Odoo."""
    from quote_agent.adapters.erp import get_erp_adapter

    adapter = get_erp_adapter()

    line = UniversalQuoteLine(
        product_id=product,
        product_name="",  # CLI doesn't resolve product name; Odoo fills it
        quantity=quantity,
        unit_price=price if price is not None else 0.0,
        description=description,
    )

    quote = UniversalQuote(
        client_id=client,
        client_name="",  # Resolved by adapter via get_client
        lines=[line],
    )

    return await adapter.create_draft_quote(quote)


async def draft_create(
    client: str,
    product: int,
    quantity: float,
    price: float | None = None,
    description: str | None = None,
    json_output: bool = False,
) -> None:
    """Create a draft quote in Odoo ERP."""
    try:
        result = await _create_draft(client, product, quantity, price, description)

        if json_output:
            typer.echo(result.model_dump_json(indent=2))
        else:
            typer.echo(typer.style("Draft Quote Created", bold=True))
            typer.echo(f"  Odoo ID:    {result.odoo_id}")
            typer.echo(f"  Reference:  {result.order_reference}")
            typer.echo(f"  State:      {result.state}")
            typer.echo(f"  Lines:      {result.line_count}")

    except ValueError as exc:
        typer.echo(typer.style(f"Not found: {exc}", fg=typer.colors.YELLOW))
        raise typer.Exit(code=1) from None
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None
