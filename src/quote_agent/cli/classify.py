"""CLI classify command — classifies quote request complexity."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.agent.nodes.classifier import ClassificationResult


def _format_result(result: ClassificationResult) -> None:
    """Display classification result as formatted output."""
    color_map = {
        "simple": typer.colors.GREEN,
        "ambiguous": typer.colors.YELLOW,
        "complex": typer.colors.RED,
        "out_of_scope": typer.colors.MAGENTA,
    }
    color = color_map.get(result.complexity, typer.colors.WHITE)

    typer.echo(f"Complexity: {typer.style(result.complexity, fg=color, bold=True)}")
    typer.echo(f"Confidence: {result.confidence:.2f}")
    typer.echo(f"Duration:   {result.classification_duration_ms}ms")
    typer.echo()
    typer.echo("Reasons:")
    for reason in result.reasons:
        typer.echo(f"  - {reason}")


async def _run_classify(
    description: str,
    *,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
) -> ClassificationResult:
    """Execute classification using the classifier node."""
    try:
        from quote_agent.adapters.llm import get_llm_adapter
        from quote_agent.agent.nodes.classifier import classify_request
        from quote_agent.services.extraction_models import (
            ExtractedQuoteRequest,
            QuoteLineItem,
        )

        line_item = QuoteLineItem(
            description=description,
            quantity=quantity,
            reference=reference,
        )
        request = ExtractedQuoteRequest(
            line_items=[line_item],
            urgency=urgency,
            raw_text=description,
        )

        adapter = get_llm_adapter()
        return await classify_request(request, adapter)
    except ImportError:
        typer.echo(
            typer.style(
                "Error: Missing LLM dependencies. Ensure LLM__API_KEY is configured.",
                fg=typer.colors.RED,
            )
        )
        sys.exit(1)


async def classify(
    description: str,
    *,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
    json_output: bool,
) -> None:
    """Classify the complexity of a quote request."""
    try:
        result = await _run_classify(
            description,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
        )
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
    else:
        _format_result(result)
