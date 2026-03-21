"""CLI review command — runs full pipeline with self-review validation gate."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.agent.nodes.self_reviewer import SelfReviewResult


def _format_review_result(review: SelfReviewResult) -> None:
    """Display self-review result as formatted output."""
    verdict_color = typer.colors.GREEN if review.approved else typer.colors.RED
    verdict_text = "APPROVED" if review.approved else "REJECTED"

    typer.echo(f"Review Verdict: {typer.style(verdict_text, fg=verdict_color, bold=True)}")
    typer.echo(f"Review Duration: {review.review_duration_ms}ms")
    typer.echo()

    if review.steps:
        typer.echo("Validation Steps:")
        for step in review.steps:
            status_icon = (
                typer.style("PASS", fg=typer.colors.GREEN)
                if step.passed
                else typer.style("FAIL", fg=typer.colors.RED)
            )
            typer.echo(f"  [{step.step_name}] {status_icon} ({step.duration_ms}ms)")
            typer.echo(f"    {step.detail}")
        typer.echo()

    if review.failure_reasons:
        typer.echo(typer.style("Failure Reasons:", fg=typer.colors.RED))
        for reason in review.failure_reasons:
            typer.echo(f"  - {reason}")
        typer.echo()

    if review.anomaly_flags:
        typer.echo(typer.style("Anomaly Flags:", fg=typer.colors.MAGENTA, bold=True))
        for flag in review.anomaly_flags:
            typer.echo(f"  !! {flag}")


async def _run_review(
    description: str,
    *,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
    json_output: bool = False,
) -> SelfReviewResult:
    """Execute the full pipeline with self-review: classify → reason → score → route → review."""
    try:
        from quote_agent.adapters.llm import get_llm_adapter
        from quote_agent.agent.nodes.self_reviewer import self_review
        from quote_agent.cli.reason import _run_reason
        from quote_agent.config import get_settings
        from quote_agent.models.base import _get_session_factory

        adapter = get_llm_adapter()
        get_settings()  # validate settings early

        # Steps 1-4: classify → reason → score → route
        reasoning, confidence, decision = await _run_reason(
            description,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
            json_output=json_output,
        )

        if not json_output:
            typer.echo(f"Confidence: {confidence.overall_confidence:.2f} | "
                        f"Tier: {decision.tier} | Action: {decision.action}")
            typer.echo()

        # Step 5: Self-review
        factory = _get_session_factory()
        async with factory() as session:
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

            review_result = await self_review(reasoning, request, adapter, session)

        return review_result
    except ImportError:
        typer.echo(
            typer.style(
                "Error: Missing dependencies. Ensure LLM__API_KEY and DATABASE__URL are configured.",
                fg=typer.colors.RED,
            )
        )
        sys.exit(1)


def review(
    description: str = typer.Argument(..., help="Quote request description to review"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Run full pipeline with self-review validation gate."""
    try:
        review_result = asyncio.run(
            _run_review(
                description,
                quantity=quantity,
                reference=reference,
                urgency=urgency,
                json_output=json_output,
            )
        )
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    if json_output:
        import json

        output = json.loads(review_result.model_dump_json())
        typer.echo(json.dumps(output, indent=2))
    else:
        _format_review_result(review_result)
