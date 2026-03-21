"""CLI review command — runs full pipeline with self-review and compliance check."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.agent.nodes.compliance_checker import ComplianceCheckResult
    from quote_agent.agent.nodes.self_reviewer import SelfReviewResult


def _format_review_result(
    review: SelfReviewResult,
    compliance: ComplianceCheckResult | None = None,
) -> None:
    """Display self-review and compliance results as formatted output."""
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

    # Compliance section
    if compliance is not None:
        typer.echo()
        if compliance.is_compliant:
            compliance_text = typer.style("COMPLIANT", fg=typer.colors.GREEN, bold=True)
        else:
            has_block = any(f.severity == "block" for f in compliance.flags)
            if has_block:
                compliance_text = typer.style("BLOCKED", fg=typer.colors.RED, bold=True)
            else:
                compliance_text = typer.style("FLAGGED", fg=typer.colors.YELLOW, bold=True)

        typer.echo(f"Compliance: {compliance_text} ({compliance.check_duration_ms}ms)")

        if compliance.flags:
            for cflag in compliance.flags:
                severity_color = typer.colors.RED if cflag.severity == "block" else typer.colors.YELLOW
                severity_text = typer.style(cflag.severity.upper(), fg=severity_color)
                typer.echo(f"  [{cflag.flag_type}] {severity_text}: {cflag.detail}")
                if cflag.matched_term:
                    typer.echo(f"    Matched: \"{cflag.matched_term}\"")


async def _run_review(
    description: str,
    *,
    quantity: float | None,
    reference: str | None,
    urgency: str | None,
    client: str | None = None,
    json_output: bool = False,
) -> tuple[SelfReviewResult, ComplianceCheckResult]:
    """Execute the full pipeline: classify → reason → score → route → review → compliance."""
    try:
        from quote_agent.adapters.llm import get_llm_adapter
        from quote_agent.agent.nodes.compliance_checker import check_compliance
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

        # Build request once for both self-review and compliance
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

        # Step 5: Self-review
        factory = _get_session_factory()
        async with factory() as session:
            review_result = await self_review(reasoning, request, adapter, session)

        # Step 6: Compliance check
        compliance_result = await check_compliance(request, adapter, client_name=client)

        return review_result, compliance_result
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
    client: str | None = typer.Option(None, "--client", "-c", help="Client name for sanctions check"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
) -> None:
    """Run full pipeline with self-review validation gate and compliance check."""
    try:
        review_result, compliance_result = asyncio.run(
            _run_review(
                description,
                quantity=quantity,
                reference=reference,
                urgency=urgency,
                client=client,
                json_output=json_output,
            )
        )
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    if json_output:
        import json

        output = {
            "review": json.loads(review_result.model_dump_json()),
            "compliance": json.loads(compliance_result.model_dump_json()),
        }
        typer.echo(json.dumps(output, indent=2))
    else:
        _format_review_result(review_result, compliance_result)

        # If compliance flags with severity "block", override final message
        if any(f.severity == "block" for f in compliance_result.flags):
            typer.echo()
            typer.echo(typer.style(
                "BLOCKED: Compliance check detected blocking issues. "
                "This request cannot be auto-processed.",
                fg=typer.colors.RED,
                bold=True,
            ))
