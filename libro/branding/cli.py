"""CLI commands for branding module."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.config import get_settings
from libro.database import get_session
from libro.models.brand import Brand
from libro.models.variant import Variant

app = typer.Typer(help="Manage brands and generate covers")
console = Console()


@app.command()
def create(
    name: str = typer.Argument(help="Brand name"),
    palette: Optional[str] = typer.Option(None, help="Color palette (midnight, forest, ocean, sunset, minimal, sage, blush, slate)"),
    font: str = typer.Option("Sans", help="Font family (Sans, Serif)"),
    primary_color: Optional[str] = typer.Option(None, "--primary", help="Primary color hex"),
    secondary_color: Optional[str] = typer.Option(None, "--secondary", help="Secondary color hex"),
    accent_color: Optional[str] = typer.Option(None, "--accent", help="Accent color hex"),
):
    """Register a new brand with a color palette."""
    from libro.branding.brand_manager import create_brand

    with get_session() as session:
        brand = create_brand(
            session, name,
            palette=palette, font=font,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
        )
        console.print(f"[green]Brand '{name}' created (#{brand.id})[/green]")
        console.print(f"  Style: {brand.style_config_json}")


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
def palettes():
    """Show available color palettes."""
    from libro.branding.brand_manager import COLOR_PALETTES

    table = Table(title="Color Palettes")
    table.add_column("Name", style="cyan")
    table.add_column("Primary")
    table.add_column("Secondary")
    table.add_column("Accent")
    table.add_column("Description")

    for name, p in COLOR_PALETTES.items():
        table.add_row(
            name,
            p["primary_color"],
            p["secondary_color"],
            p["accent_color"],
            p["description"],
        )
    console.print(table)


@app.command()
def cover(
    variant_id: int = typer.Argument(help="Variant ID"),
    brand_id: Optional[int] = typer.Option(None, help="Brand ID (uses variant's brand if not specified)"),
    author: Optional[str] = typer.Option(None, help="Author name for cover"),
    template_path: Optional[str] = typer.Option(None, "--template", help="Path to background image template"),
):
    """Generate a KDP-compliant cover for a variant."""
    from libro.branding.brand_manager import BrandStyle
    from libro.branding.cover import CoverGenerator

    settings = get_settings()

    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant:
            console.print(f"[red]Variant #{variant_id} not found[/red]")
            raise typer.Exit(1)

        # Get brand style
        bid = brand_id or variant.brand_id
        if bid:
            brand = session.get(Brand, bid)
            if not brand:
                console.print(f"[red]Brand #{bid} not found[/red]")
                raise typer.Exit(1)
            style = BrandStyle.from_brand(brand)
            author_name = author or brand.name
        else:
            style = BrandStyle(
                font="Sans",
                primary_color="#2C3E50",
                secondary_color="#ECF0F1",
                accent_color="#E74C3C",
            )
            author_name = author or ""

        output_dir = settings.output_dir / f"variant_{variant_id}"
        output_path = output_dir / "cover.pdf"

        tpl = Path(template_path) if template_path else None

        with console.status("[green]Generating cover..."):
            generator = CoverGenerator()
            path = generator.generate(
                title=variant.title,
                subtitle=variant.subtitle,
                author=author_name,
                trim_size=variant.trim_size,
                page_count=variant.page_count,
                output_path=output_path,
                primary_color=style.primary_color,
                secondary_color=style.secondary_color,
                accent_color=style.accent_color,
                font_name=style.font,
                template_path=tpl,
            )

        variant.cover_pdf_path = str(path)
        if variant.interior_pdf_path:
            variant.status = "ready"

        console.print(f"[green]Cover generated:[/green] {path}")
        console.print(f"  Title: {variant.title}")
        console.print(f"  Size: {variant.trim_size} | Pages: {variant.page_count}")


@app.command()
def assign(
    variant_id: int = typer.Argument(help="Variant ID"),
    brand_id: int = typer.Argument(help="Brand ID"),
):
    """Assign a brand to a variant."""
    with get_session() as session:
        variant = session.get(Variant, variant_id)
        brand = session.get(Brand, brand_id)
        if not variant or not brand:
            console.print("[red]Variant or brand not found[/red]")
            raise typer.Exit(1)
        variant.brand_id = brand.id
        console.print(f"[green]Assigned brand '{brand.name}' to variant #{variant.id}[/green]")
