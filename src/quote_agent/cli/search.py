"""CLI search command — executes product search and displays formatted results."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.search.models import SearchResult


def _format_results(result: SearchResult) -> None:
    """Display search results as a formatted table."""
    typer.echo(f'Search: "{result.query}"')
    typer.echo(
        f"Method: {result.method} | Results: {len(result.results)} / {result.total_found} | "
        f"Duration: {result.duration_seconds:.4f}s"
    )

    if result.from_cache:
        typer.echo(typer.style("(cached)", fg=typer.colors.CYAN))

    typer.echo()

    # Header
    typer.echo(f"  {'#':<4}{'Reference':<18}{'Name':<32}{'Category':<14}{'Score':<10}{'Source':<10}{'Prop'}")
    typer.echo("  " + "─" * 100)

    for product in result.results:
        name = product.name[:30] + "…" if len(product.name) > 30 else product.name
        source_padded = f"{product.match_source:<10}"
        source = typer.style(source_padded, fg=typer.colors.YELLOW)

        if product.is_proposable:
            prop = typer.style("✓", fg=typer.colors.GREEN)
        else:
            prop = typer.style("✗", fg=typer.colors.RED)

        typer.echo(
            f"  {product.rank:<4}{product.reference:<18}{name:<32}{product.category:<14}"
            f"{product.score:.4f}    {source}{prop}"
        )


async def _run_search(
    query: str,
    *,
    limit: int,
    method: str,
    no_filter: bool,
    include_stale: bool,
) -> SearchResult:
    """Execute a search using the SearchEngine inside an async session."""
    try:
        from quote_agent.models.base import _get_session_factory
        from quote_agent.search import get_search_engine
        from quote_agent.search.models import SearchRequest

        request = SearchRequest(
            query=query,
            limit=limit,
            include_stale=include_stale,
            apply_proposability_filter=not no_filter,
        )

        factory = _get_session_factory()
        async with factory() as session:
            engine = get_search_engine(session)
            if method == "semantic":
                return await engine.search_semantic_only(request)
            if method == "keyword":
                return await engine.search_keyword_only(request)
            return await engine.search_hybrid(request)
    except ImportError:
        typer.echo(
            typer.style(
                "Error: Missing ML dependencies. Install with: uv sync --group ml",
                fg=typer.colors.RED,
            )
        )
        sys.exit(1)


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
    if method not in ("hybrid", "semantic", "keyword"):
        msg = f"Error: Invalid method '{method}'. Use hybrid, semantic, or keyword."
        typer.echo(typer.style(msg, fg=typer.colors.RED))
        raise typer.Exit(code=1)

    try:
        result = asyncio.run(
            _run_search(
                query,
                limit=limit,
                method=method,
                no_filter=no_filter,
                include_stale=include_stale,
            )
        )
    except OSError as exc:
        typer.echo(typer.style("Error: Could not connect to PostgreSQL.", fg=typer.colors.RED))
        typer.echo("  Ensure the database is running and DATABASE__URL is set correctly.")
        typer.echo(f"  Details: {exc}")
        raise typer.Exit(code=1) from None
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
    else:
        _format_results(result)
