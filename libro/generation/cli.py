"""CLI commands for book generation module."""

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(help="Generate book variants and interiors")
console = Console()


@app.command()
def variants(
    niche_id: int = typer.Argument(help="Niche ID to generate variants for"),
    count: int = typer.Option(3, help="Number of variants to create"),
):
    """Create N variant records for a niche."""
    console.print(f"[yellow]Generating {count} variants for niche #{niche_id}[/yellow]")
    console.print("[red]Not yet implemented — coming in Phase 3[/red]")


@app.command()
def interior(variant_id: int = typer.Argument(help="Variant ID")):
    """Generate interior PDF for a variant."""
    console.print(f"[yellow]Generating interior for variant #{variant_id}[/yellow]")
    console.print("[red]Not yet implemented — coming in Phase 3[/red]")


@app.command()
def preview(variant_id: int = typer.Argument(help="Variant ID")):
    """Open generated PDF for quick review."""
    console.print("[red]Not yet implemented — coming in Phase 3[/red]")
