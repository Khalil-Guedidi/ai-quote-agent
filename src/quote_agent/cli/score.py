"""CLI score command — runs classification + search + confidence scoring + routing pipeline."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.agent.nodes.confidence_scorer import ConfidenceResult
    from quote_agent.agent.nodes.router import RoutingDecision


def _format_result(
    confidence: ConfidenceResult,
    decision: RoutingDecision,
) -> None:
    """Display confidence scoring and routing result as formatted output."""
    tier_colors = {
        "high": typer.colors.GREEN,
        "medium": typer.colors.YELLOW,
        "low": typer.colors.RED,
        "out_of_scope": typer.colors.MAGENTA,
    }
    action_colors = {
        "proceed_to_draft": typer.colors.GREEN,
        "generate_proposals": typer.colors.YELLOW,
        "escalate": typer.colors.RED,
        "notify_out_of_scope": typer.colors.MAGENTA,
    }

    tier_color = tier_colors.get(decision.tier, typer.colors.WHITE)
    action_color = action_colors.get(decision.action, typer.colors.WHITE)

    typer.echo(f"Confidence: {confidence.overall_confidence:.2f}")
    typer.echo(f"Tier:       {typer.style(decision.tier, fg=tier_color, bold=True)}")
    typer.echo(f"Action:     {typer.style(decision.action, fg=action_color, bold=True)}")
    typer.echo(f"Duration:   {confidence.scoring_duration_ms}ms")
    typer.echo()

    if confidence.product_scores:
        typer.echo("Product Scores:")
        for ps in confidence.product_scores:
            typer.echo(f"  #{ps.rank} {ps.reference} — {ps.name}")
            typer.echo(f"      Confidence: {ps.confidence:.2f} | {ps.match_quality}")
        typer.echo()

    typer.echo("Reasoning:")
    for reason in confidence.reasoning:
        typer.echo(f"  - {reason}")

    if decision.proposals:
        typer.echo()
        typer.echo("Proposals:")
        for p in decision.proposals:
            typer.echo(f"  - {p.reference} — {p.name} (confidence: {p.confidence:.2f})")

    if decision.escalation_context:
        typer.echo()
        typer.echo("Escalation Context:")
        typer.echo(f"  Understood:  {decision.escalation_context.understood}")
        typer.echo(f"  Uncertain:   {decision.escalation_context.uncertain}")
        typer.echo("  Next steps:")
        for step in decision.escalation_context.suggested_next_steps:
            typer.echo(f"    - {step}")


async def _run_score(
    description: str,
    *,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
    limit: int,
) -> tuple[ConfidenceResult, RoutingDecision]:
    """Execute the full scoring pipeline: classify → search → score → route."""
    try:
        from quote_agent.adapters.llm import get_llm_adapter
        from quote_agent.agent.nodes.classifier import classify_request
        from quote_agent.agent.nodes.confidence_scorer import score_confidence
        from quote_agent.agent.nodes.router import route_by_confidence
        from quote_agent.config import get_settings
        from quote_agent.models.base import _get_session_factory
        from quote_agent.search import get_search_engine
        from quote_agent.search.models import SearchRequest
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
        settings = get_settings()

        # Step 1: Classify
        classification = await classify_request(request, adapter)
        typer.echo(f"Classification: {classification.complexity} (confidence: {classification.confidence:.2f})")

        # Step 2: Search
        search_request = SearchRequest(query=description, limit=limit)
        factory = _get_session_factory()
        async with factory() as session:
            engine = get_search_engine(session)
            search_result = await engine.search_hybrid(search_request)
        typer.echo(f"Search: {len(search_result.results)} results ({search_result.duration_seconds:.3f}s)")
        typer.echo()

        # Step 3: Score confidence
        confidence = await score_confidence(classification, search_result, request, adapter)

        # Step 4: Route
        decision = route_by_confidence(confidence, classification, settings.confidence_scoring)

        return confidence, decision
    except ImportError:
        typer.echo(
            typer.style(
                "Error: Missing dependencies. Ensure LLM__API_KEY and DATABASE__URL are configured.",
                fg=typer.colors.RED,
            )
        )
        sys.exit(1)


def score(
    description: str = typer.Argument(..., help="Quote request description to score"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of search results to score"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Score confidence of product matches and route by tier."""
    try:
        confidence, decision = asyncio.run(
            _run_score(
                description,
                quantity=quantity,
                reference=reference,
                urgency=urgency,
                limit=limit,
            )
        )
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    if json_output:
        import json

        output = {
            "confidence": json.loads(confidence.model_dump_json()),
            "routing": json.loads(decision.model_dump_json()),
        }
        typer.echo(json.dumps(output, indent=2))
    else:
        _format_result(confidence, decision)
