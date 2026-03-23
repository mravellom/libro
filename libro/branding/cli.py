"""CLI commands for branding module."""

import json

import typer
from rich.console import Console
from rich.table import Table

from libro.database import get_session
from libro.models.brand import Brand

app = typer.Typer(help="Manage brands and generate covers")
console = Console()


@app.command()
def create(
    name: str = typer.Argument(help="Brand name"),
    font: str = typer.Option("Helvetica", help="Primary font"),
    primary_color: str = typer.Option("#1a1a1a", help="Primary color hex"),
    secondary_color: str = typer.Option("#f5f5f5", help="Secondary color hex"),
):
    """Register a new brand."""
    with get_session() as session:
        style = {
            "font": font,
            "primary_color": primary_color,
            "secondary_color": secondary_color,
        }
        brand = Brand(name=name, style_config_json=json.dumps(style))
        session.add(brand)
        session.flush()
        console.print(f"[green]Brand '{name}' created (#{brand.id})[/green]")


@app.command("list")
def list_brands():
    """List all brands."""
    with get_session() as session:
        brands = session.query(Brand).all()
        if not brands:
            console.print("[dim]No brands found.[/dim]")
            return

        table = Table(title="Brands")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Style")

        for b in brands:
            table.add_row(str(b.id), b.name, b.style_config_json or "—")
        console.print(table)


@app.command()
def cover(variant_id: int = typer.Argument(help="Variant ID")):
    """Generate cover for a variant."""
    console.print(f"[yellow]Generating cover for variant #{variant_id}[/yellow]")
    console.print("[red]Not yet implemented — coming in Phase 4[/red]")


@app.command()
def assign(
    variant_id: int = typer.Argument(help="Variant ID"),
    brand_id: int = typer.Argument(help="Brand ID"),
):
    """Assign a brand to a variant."""
    from libro.models.variant import Variant

    with get_session() as session:
        variant = session.get(Variant, variant_id)
        brand = session.get(Brand, brand_id)
        if not variant or not brand:
            console.print("[red]Variant or brand not found[/red]")
            raise typer.Exit(1)
        variant.brand_id = brand.id
        console.print(f"[green]Assigned brand '{brand.name}' to variant #{variant.id}[/green]")
