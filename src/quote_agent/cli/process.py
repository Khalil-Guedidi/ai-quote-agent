"""CLI process command — runs the full LangGraph agent pipeline end-to-end."""

from __future__ import annotations

import json
import logging
from typing import Any

import typer

from quote_agent.services.extraction_models import ExtractedQuoteRequest, QuoteLineItem

logger = logging.getLogger(__name__)


def _format_state(state: dict[str, Any]) -> None:
    """Display the final agent state as formatted CLI output."""
    # Classification
    classification = state.get("classification")
    if classification is not None:
        typer.echo(
            f"Classification: {typer.style(str(classification.complexity), bold=True)}"
            f"  (confidence: {classification.confidence:.2f})"
        )

    # Reasoning
    reasoning = state.get("reasoning")
    if reasoning is not None:
        typer.echo(
            f"Strategy:       {typer.style(str(reasoning.strategy), bold=True)}"
            f"  ({reasoning.reasoning_duration_ms}ms,"
            f" {len(reasoning.search_result.results)} results)"
        )

    # Confidence & routing
    confidence = state.get("confidence")
    routing = state.get("routing_decision")
    if confidence is not None and routing is not None:
        tier_colors: dict[str, str] = {
            "high": typer.colors.GREEN,
            "medium": typer.colors.YELLOW,
            "low": typer.colors.RED,
            "out_of_scope": typer.colors.MAGENTA,
        }
        action_colors: dict[str, str] = {
            "proceed_to_draft": typer.colors.GREEN,
            "generate_proposals": typer.colors.YELLOW,
            "escalate": typer.colors.RED,
            "notify_out_of_scope": typer.colors.MAGENTA,
        }
        tier_color = tier_colors.get(str(routing.tier), typer.colors.WHITE)
        action_color = action_colors.get(str(routing.action), typer.colors.WHITE)
        typer.echo(
            f"Confidence:     {confidence.overall_confidence:.2f}"
            f"  | Tier: {typer.style(str(routing.tier), fg=tier_color, bold=True)}"
        )
        typer.echo(f"Action:         {typer.style(str(routing.action), fg=action_color, bold=True)}")

    # Self-review
    review = state.get("self_review")
    if review is not None:
        verdict = "APPROVED" if review.approved else "REJECTED"
        color = typer.colors.GREEN if review.approved else typer.colors.RED
        typer.echo(f"Review:         {typer.style(verdict, fg=color, bold=True)}")

    # Compliance
    compliance = state.get("compliance")
    if compliance is not None:
        if compliance.is_compliant:
            typer.echo(f"Compliance:     {typer.style('COMPLIANT', fg=typer.colors.GREEN, bold=True)}")
        else:
            has_block = any(f.severity == "block" for f in compliance.flags)
            label = "BLOCKED" if has_block else "FLAGGED"
            color = typer.colors.RED if has_block else typer.colors.YELLOW
            typer.echo(f"Compliance:     {typer.style(label, fg=color, bold=True)}")

    # Draft result
    draft = state.get("draft_result")
    if draft is not None:
        typer.echo()
        typer.echo(
            f"Draft created:  {typer.style(str(draft.order_reference), fg=typer.colors.GREEN, bold=True)}"
            f"  (Odoo ID: {draft.odoo_id})"
        )

    # Error
    error = state.get("error")
    if error:
        typer.echo()
        typer.echo(typer.style(f"Error: {error}", fg=typer.colors.RED))

    # Final action
    final = state.get("final_action", "")
    if final:
        typer.echo()
        typer.echo(f"Final action:   {final}")


def _state_to_json(state: dict[str, Any]) -> str:
    """Serialize the final state to JSON, converting Pydantic models."""
    output: dict[str, Any] = {}
    for key, value in state.items():
        if value is None:
            output[key] = None
        elif hasattr(value, "model_dump_json"):
            output[key] = json.loads(value.model_dump_json())
        else:
            output[key] = value
    return json.dumps(output, indent=2, default=str)


async def _send_error_notification(error: str) -> None:
    """Send a fire-and-forget error notification after pipeline failure (Option B).

    Delegates to shared helper in services.error_notifier.
    """
    from quote_agent.services.error_notifier import send_error_notification

    await send_error_notification(error)


async def _run_process(
    description: str,
    *,
    client: str | None,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
) -> dict[str, Any]:
    """Build initial state and run the LangGraph agent pipeline."""
    from quote_agent.agent.graph import get_agent_graph
    from quote_agent.agent.state import create_initial_state

    line_item = QuoteLineItem(
        description=description,
        quantity=quantity,
        reference=reference,
    )
    request = ExtractedQuoteRequest(
        client_name=client,
        client_identifier=client,
        line_items=[line_item],
        urgency=urgency,
        raw_text=description,
    )

    initial_state = create_initial_state(request)
    graph = get_agent_graph()
    return await graph.ainvoke(initial_state)


async def process(
    description: str,
    *,
    client: str | None,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
    json_output: bool,
) -> None:
    """Run the full LangGraph agent pipeline end-to-end."""
    try:
        result: dict[str, Any] = await _run_process(
            description,
            client=client,
            quantity=quantity,
            reference=reference,
            urgency=urgency,
        )
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    # Post-pipeline error notification (Option B — Story 5.5.5)
    error = result.get("error")
    if error:
        await _send_error_notification(error)

    if json_output:
        typer.echo(_state_to_json(result))
    else:
        _format_state(result)
