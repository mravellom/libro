"""CLI commands for book generation module."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.config import get_settings, PROJECT_ROOT
from libro.database import get_session
from libro.models.variant import Variant

app = typer.Typer(help="Generate book variants and interiors")
console = Console()


@app.command()
def variants(
    niche_id: int = typer.Argument(help="Niche ID to generate variants for"),
    count: int = typer.Option(3, help="Number of variants to create"),
):
    """Create N variant records for a niche based on competitor analysis."""
    from libro.generation.variant_engine import generate_variants

    with get_session() as session:
        created = generate_variants(session, niche_id, count)

        if not created:
            console.print("[yellow]No variants created (similarity guard may have blocked some)[/yellow]")
            return

        console.print(f"\n[green]Created {len(created)} variants for niche #{niche_id}:[/green]")
        for v in created:
            console.print(f"  #{v.id} | {v.interior_type:10} | {v.trim_size} | {v.title[:50]}")

        console.print(f"\n[dim]Generate interiors with: libro generate interior <variant-id>[/dim]")


@app.command()
def interior(
    variant_id: int = typer.Argument(help="Variant ID"),
    template: Optional[str] = typer.Option(None, help="Override template (lined, dotted, grid, gratitude, planner)"),
):
    """Generate interior PDF for a variant."""
    from libro.generation.interior import generate_interior

    settings = get_settings()

    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant:
            console.print(f"[red]Variant #{variant_id} not found[/red]")
            raise typer.Exit(1)

        template_name = template or variant.interior_type
        output_dir = settings.output_dir / f"variant_{variant_id}"
        output_path = output_dir / "interior.pdf"

        with console.status(f"[green]Generating {template_name} interior ({variant.page_count} pages)..."):
            path = generate_interior(
                template_name=template_name,
                output_path=output_path,
                trim_size=variant.trim_size,
                page_count=variant.page_count,
            )

        variant.interior_pdf_path = str(path)
        variant.status = "ready" if variant.cover_pdf_path else "draft"

        console.print(f"[green]Interior generated:[/green] {path}")
        console.print(f"  Template: {template_name} | Size: {variant.trim_size} | Pages: {variant.page_count}")


@app.command()
def preview(variant_id: int = typer.Argument(help="Variant ID")):
    """Open generated PDF for quick review."""
    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant:
            console.print(f"[red]Variant #{variant_id} not found[/red]")
            raise typer.Exit(1)

        if not variant.interior_pdf_path:
            console.print(f"[red]No interior PDF generated yet. Run: libro generate interior {variant_id}[/red]")
            raise typer.Exit(1)

        path = Path(variant.interior_pdf_path)
        if not path.exists():
            console.print(f"[red]PDF file not found: {path}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]Opening:[/green] {path}")
        # Cross-platform open
        if sys.platform == "linux":
            subprocess.Popen(["xdg-open", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["start", str(path)], shell=True)


@app.command("list")
def list_variants(
    niche_id: Optional[int] = typer.Option(None, help="Filter by niche"),
    status: Optional[str] = typer.Option(None, help="Filter by status"),
):
    """List all variants."""
    with get_session() as session:
        query = session.query(Variant)
        if niche_id:
            query = query.filter(Variant.niche_id == niche_id)
        if status:
            query = query.filter(Variant.status == status)

        variants = query.order_by(Variant.created_at.desc()).all()

        if not variants:
            console.print("[dim]No variants found.[/dim]")
            return

        table = Table(title="Variants")
        table.add_column("ID", style="cyan")
        table.add_column("Niche")
        table.add_column("Title", max_width=40)
        table.add_column("Interior")
        table.add_column("Size")
        table.add_column("Pages", justify="right")
        table.add_column("PDF")
        table.add_column("Status", style="green")

        for v in variants:
            has_pdf = "yes" if v.interior_pdf_path else "—"
            niche_kw = v.niche.keyword if v.niche else "?"
            table.add_row(
                str(v.id),
                niche_kw[:15],
                v.title[:40],
                v.interior_type,
                v.trim_size,
                str(v.page_count),
                has_pdf,
                v.status,
            )
        console.print(table)


@app.command()
def templates():
    """List all available interior templates."""
    from libro.generation.interior import list_templates

    tmps = list_templates()
    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for t in tmps:
        table.add_row(t["name"], t["description"])
    console.print(table)
