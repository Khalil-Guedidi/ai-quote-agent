"""CLI logs command — streams Docker container logs."""

from __future__ import annotations

import subprocess

import typer

CONTAINER_NAME = "quote-agent-app"


def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """Show structured log output from the application container."""
    cmd = ["docker", "logs", "--tail", str(lines)]
    if follow:
        cmd.append("--follow")
    cmd.append(CONTAINER_NAME)

    try:
        result = subprocess.run(cmd, check=False)
        raise typer.Exit(code=result.returncode)
    except FileNotFoundError:
        typer.echo(typer.style("Error: docker is not installed or not in PATH.", fg=typer.colors.RED))
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        raise typer.Exit(code=0) from None
