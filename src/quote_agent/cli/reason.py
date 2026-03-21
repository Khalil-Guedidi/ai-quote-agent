"""CLI reason command — runs classification + reasoning + scoring + routing pipeline."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.agent.nodes.confidence_scorer import ConfidenceResult
    from quote_agent.agent.nodes.reasoning_strategy import ReasoningResult
    from quote_agent.agent.nodes.router import RoutingDecision


def _format_result(
    reasoning: ReasoningResult,
    confidence: ConfidenceResult,
    decision: RoutingDecision,
) -> None:
    """Display reasoning, confidence scoring, and routing result as formatted output."""
    strategy_colors: dict[str, str] = {
        "direct_match": typer.colors.GREEN,
        "exploration": typer.colors.YELLOW,
        "deep_analysis": typer.colors.RED,
        "out_of_scope_skip": typer.colors.MAGENTA,
    }
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

    strategy_color = strategy_colors.get(reasoning.strategy, typer.colors.WHITE)
    tier_color = tier_colors.get(decision.tier, typer.colors.WHITE)
    action_color = action_colors.get(decision.action, typer.colors.WHITE)

    typer.echo(f"Strategy:   {typer.style(reasoning.strategy, fg=strategy_color, bold=True)}")
    typer.echo(f"Duration:   {reasoning.reasoning_duration_ms}ms")
    typer.echo()

    if reasoning.steps:
        typer.echo("Reasoning Steps:")
        for step in reasoning.steps:
            typer.echo(f"  [{step.step_name}] ({step.duration_ms}ms) {step.description}")
            typer.echo(f"    -> {step.outcome}")
        typer.echo()

    typer.echo(f"Confidence: {confidence.overall_confidence:.2f}")
    typer.echo(f"Tier:       {typer.style(decision.tier, fg=tier_color, bold=True)}")
    typer.echo(f"Action:     {typer.style(decision.action, fg=action_color, bold=True)}")

    if confidence.product_scores:
        typer.echo()
        typer.echo("Product Scores:")
        for ps in confidence.product_scores:
            typer.echo(f"  #{ps.rank} {ps.reference} — {ps.name}")
            typer.echo(f"      Confidence: {ps.confidence:.2f} | {ps.match_quality}")

    if confidence.reasoning:
        typer.echo()
        typer.echo("Reasoning:")
        for r in confidence.reasoning:
            typer.echo(f"  - {r}")

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
        for next_step in decision.escalation_context.suggested_next_steps:
            typer.echo(f"    - {next_step}")


async def _run_reason(
    description: str,
    *,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
    json_output: bool = False,
) -> tuple[ReasoningResult, ConfidenceResult, RoutingDecision]:
    """Execute the full reasoning pipeline: classify → reason → score → route."""
    try:
        from quote_agent.adapters.llm import get_llm_adapter
        from quote_agent.agent.nodes.classifier import classify_request
        from quote_agent.agent.nodes.confidence_scorer import score_confidence
        from quote_agent.agent.nodes.reasoning_strategy import apply_reasoning_strategy
        from quote_agent.agent.nodes.router import route_by_confidence
        from quote_agent.config import get_settings
        from quote_agent.models.base import _get_session_factory
        from quote_agent.search import get_search_engine
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
        if not json_output:
            typer.echo(f"Classification: {classification.complexity} (confidence: {classification.confidence:.2f})")

        # Step 2: Reason (does search internally)
        factory = _get_session_factory()
        async with factory() as session:
            engine = get_search_engine(session)
            reasoning = await apply_reasoning_strategy(classification, request, adapter, engine)
        if not json_output:
            typer.echo(f"Strategy: {reasoning.strategy} ({reasoning.reasoning_duration_ms}ms, "
                        f"{len(reasoning.search_result.results)} results)")
            typer.echo()

        # Step 3: Score confidence
        confidence = await score_confidence(classification, reasoning.search_result, request, adapter)

        # Step 4: Route
        decision = route_by_confidence(confidence, classification, settings.confidence_scoring)

        return reasoning, confidence, decision
    except ImportError:
        typer.echo(
            typer.style(
                "Error: Missing dependencies. Ensure LLM__API_KEY and DATABASE__URL are configured.",
                fg=typer.colors.RED,
            )
        )
        sys.exit(1)


def reason(
    description: str = typer.Argument(..., help="Quote request description to reason about"),
    quantity: float | None = typer.Option(None, "--quantity", "-q", help="Requested quantity"),
    reference: str | None = typer.Option(None, "--reference", "-r", help="Product reference"),
    urgency: str | None = typer.Option(None, "--urgency", "-u", help="Urgency level"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Apply adaptive reasoning strategy and score confidence."""
    try:
        reasoning, confidence, decision = asyncio.run(
            _run_reason(
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

        output = {
            "reasoning": json.loads(reasoning.model_dump_json()),
            "confidence": json.loads(confidence.model_dump_json()),
            "routing": json.loads(decision.model_dump_json()),
        }
        typer.echo(json.dumps(output, indent=2))
    else:
        _format_result(reasoning, confidence, decision)
