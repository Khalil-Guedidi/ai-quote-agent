"""CLI erp-read command — read client data, product details, or order history from Odoo."""

from __future__ import annotations

import json

import typer


async def _read_client(client_id: str) -> dict[str, object]:
    """Fetch client data from Odoo."""
    from quote_agent.adapters.erp import get_erp_adapter

    adapter = get_erp_adapter()
    client = await adapter.get_client(client_id)
    result: dict[str, object] = json.loads(client.model_dump_json())
    return result


async def _read_product(product_id: int) -> dict[str, object]:
    """Fetch product data from Odoo."""
    from quote_agent.adapters.erp import get_erp_adapter

    adapter = get_erp_adapter()
    product = await adapter.get_product_by_id(product_id)
    result: dict[str, object] = json.loads(product.model_dump_json())
    return result


async def _read_orders(client_id: str, limit: int) -> list[dict[str, object]]:
    """Fetch order history from Odoo."""
    from quote_agent.adapters.erp import get_erp_adapter

    adapter = get_erp_adapter()
    orders = await adapter.get_client_orders(client_id, limit=limit)
    return [json.loads(o.model_dump_json()) for o in orders]


def _format_client(data: dict[str, object]) -> None:
    """Display client data as formatted output."""
    typer.echo(typer.style("Client Details", bold=True))
    typer.echo(f"  Odoo ID:  {data['odoo_id']}")
    typer.echo(f"  Name:     {data['name']}")
    typer.echo(f"  Ref:      {data.get('ref', '-')}")
    typer.echo(f"  Email:    {data.get('email', '-')}")
    typer.echo(f"  Phone:    {data.get('phone', '-')}")
    typer.echo(f"  Address:  {data.get('address', '-')}")
    typer.echo(f"  VAT:      {data.get('vat', '-')}")
    typer.echo(f"  Active:   {data.get('is_active', True)}")
    metadata = data.get("metadata", {})
    if metadata:
        typer.echo(f"  Metadata: {metadata}")


def _format_product(data: dict[str, object]) -> None:
    """Display product data as formatted output."""
    typer.echo(typer.style("Product Details", bold=True))
    typer.echo(f"  Odoo ID:     {data['odoo_id']}")
    typer.echo(f"  Reference:   {data['reference']}")
    typer.echo(f"  Name:        {data['name']}")
    typer.echo(f"  Category:    {data['category']}")
    typer.echo(f"  Unit Price:  {data['unit_price']}")
    typer.echo(f"  Active:      {data['is_active']}")
    description = data.get("description")
    if description:
        typer.echo(f"  Description: {description}")


def _format_orders(orders: list[dict[str, object]]) -> None:
    """Display order history as formatted output."""
    if not orders:
        typer.echo("No orders found.")
        return
    typer.echo(typer.style(f"Order History ({len(orders)} lines)", bold=True))
    for order in orders:
        typer.echo(
            f"  [{order['order_id']}] {order['date']} — "
            f"{order['product_name']} x{order['quantity']} "
            f"@ {order['unit_price']} = {order['total']} ({order['state']})"
        )


async def erp_read(
    client: str | None = None,
    product: int | None = None,
    orders: str | None = None,
    limit: int = 20,
    json_output: bool = False,
) -> None:
    """Read client data, product details, or order history from Odoo ERP."""
    if not any([client, product is not None, orders]):
        typer.echo(typer.style("Error: Specify --client, --product, or --orders", fg=typer.colors.RED))
        raise typer.Exit(code=1)

    try:
        if client:
            data = await _read_client(client)
            if json_output:
                typer.echo(json.dumps(data, indent=2))
            else:
                _format_client(data)

        elif product is not None:
            data = await _read_product(product)
            if json_output:
                typer.echo(json.dumps(data, indent=2))
            else:
                _format_product(data)

        elif orders:
            order_list = await _read_orders(orders, limit)
            if json_output:
                typer.echo(json.dumps(order_list, indent=2))
            else:
                _format_orders(order_list)

    except ValueError as exc:
        typer.echo(typer.style(f"Not found: {exc}", fg=typer.colors.YELLOW))
        raise typer.Exit(code=1) from None
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None
