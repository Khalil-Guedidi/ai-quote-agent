"""CLI compliance command — runs export control and sanctions compliance check."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from quote_agent.agent.nodes.compliance_checker import ComplianceCheckResult


def _format_compliance_result(result: ComplianceCheckResult) -> None:
    """Display compliance result as formatted output."""
    if result.is_compliant:
        verdict_text = typer.style("COMPLIANT", fg=typer.colors.GREEN, bold=True)
    else:
        has_block = any(f.severity == "block" for f in result.flags)
        if has_block:
            verdict_text = typer.style("BLOCKED", fg=typer.colors.RED, bold=True)
        else:
            verdict_text = typer.style("FLAGGED", fg=typer.colors.YELLOW, bold=True)

    typer.echo(f"Compliance Verdict: {verdict_text}")
    typer.echo(f"Check Duration: {result.check_duration_ms}ms")
    typer.echo()

    if result.flags:
        typer.echo("Flags:")
        for flag in result.flags:
            severity_color = typer.colors.RED if flag.severity == "block" else typer.colors.YELLOW
            severity_text = typer.style(flag.severity.upper(), fg=severity_color)
            typer.echo(f"  [{flag.flag_type}] {severity_text}")
            typer.echo(f"    Detail: {flag.detail}")
            if flag.matched_term:
                typer.echo(f'    Matched: "{flag.matched_term}"')
            typer.echo()
    else:
        typer.echo("No compliance flags detected.")


async def _run_compliance(
    description: str,
    *,
    client_name: str | None = None,
) -> ComplianceCheckResult:
    """Execute compliance check on a description and optional client name."""
    try:
        from quote_agent.adapters.llm import get_llm_adapter
        from quote_agent.agent.nodes.compliance_checker import check_compliance
        from quote_agent.config import get_settings
        from quote_agent.services.extraction_models import (
            ExtractedQuoteRequest,
            QuoteLineItem,
        )

        get_settings()  # validate settings early
        adapter = get_llm_adapter()

        line_item = QuoteLineItem(description=description)
        request = ExtractedQuoteRequest(
            line_items=[line_item],
            raw_text=description,
        )

        return await check_compliance(request, adapter, client_name=client_name)
    except ImportError:
        typer.echo(
            typer.style(
                "Error: Missing dependencies. Ensure LLM__API_KEY is configured.",
                fg=typer.colors.RED,
            )
        )
        sys.exit(1)


async def compliance(
    description: str,
    *,
    client: str | None,
    json_output: bool,
) -> None:
    """Run export control and sanctions compliance check."""
    try:
        result = await _run_compliance(description, client_name=client)
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None

    if json_output:
        import json

        output = json.loads(result.model_dump_json())
        typer.echo(json.dumps(output, indent=2))
    else:
        _format_compliance_result(result)
