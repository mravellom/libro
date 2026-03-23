"""CLI commands for publication preparation module."""

from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.config import get_settings
from libro.database import get_session
from libro.models.publication import Publication
from libro.models.variant import Variant

app = typer.Typer(help="Prepare and track KDP publications")
console = Console()


@app.command()
def prepare(
    variant_id: int = typer.Argument(help="Variant ID to package"),
    author: Optional[str] = typer.Option(None, help="Author name (uses brand name if not specified)"),
):
    """Bundle everything for KDP upload."""
    from libro.publication.packager import package_variant

    with get_session() as session:
        with console.status("[green]Packaging for KDP..."):
            result = package_variant(session, variant_id, author=author or "")

        if result.checklist_passed:
            console.print(f"\n[green]Package ready![/green] {result.output_dir}")
        else:
            console.print(f"\n[yellow]Package created with issues:[/yellow] {result.output_dir}")

        console.print(f"\nFiles:")
        if result.interior_path:
            console.print(f"  [green]✓[/green] {result.interior_path.name}")
        else:
            console.print(f"  [red]✗[/red] manuscript.pdf — missing")

        if result.cover_path:
            console.print(f"  [green]✓[/green] {result.cover_path.name}")
        else:
            console.print(f"  [red]✗[/red] cover — missing")

        console.print(f"  [green]✓[/green] metadata.txt")
        console.print(f"  [green]✓[/green] checklist.txt")
        console.print(f"  [green]✓[/green] INSTRUCTIONS.txt")

        if result.errors:
            console.print(f"\n[red]Errors:[/red]")
            for err in result.errors:
                console.print(f"  → {err}")

        console.print(f"\n[dim]Review INSTRUCTIONS.txt for upload steps[/dim]")


@app.command()
def checklist(variant_id: int = typer.Argument(help="Variant ID to validate")):
    """Validate readiness for KDP upload."""
    from libro.publication.checklist import run_checklist

    with get_session() as session:
        result = run_checklist(session, variant_id)

        console.print(f"\n[bold]Checklist for variant #{variant_id}[/bold]\n")

        for check in result.checks:
            if check.passed:
                console.print(f"  [green]✓[/green] {check.name}: {check.message}")
            elif check.severity == "warning":
                console.print(f"  [yellow]![/yellow] {check.name}: {check.message}")
            else:
                console.print(f"  [red]✗[/red] {check.name}: {check.message}")

        console.print()
        if result.passed:
            console.print("[green]READY for publication[/green]")
        else:
            console.print(f"[red]NOT READY — {len(result.errors)} error(s)[/red]")


@app.command("mark-published")
def mark_published(
    variant_id: int = typer.Argument(help="Variant ID"),
    asin: Optional[str] = typer.Option(None, help="ASIN once available"),
):
    """Record that a variant has been published to KDP."""
    settings = get_settings()
    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant:
            console.print(f"[red]Variant #{variant_id} not found[/red]")
            raise typer.Exit(1)

        # Check if already published
        existing = session.query(Publication).filter(Publication.variant_id == variant_id).first()
        if existing:
            console.print(f"[yellow]Variant #{variant_id} already published (publication #{existing.id})[/yellow]")
            if asin and not existing.asin:
                existing.asin = asin
                console.print(f"[green]Updated ASIN to {asin}[/green]")
            return

        now = datetime.utcnow()
        pub = Publication(
            variant_id=variant_id,
            asin=asin,
            published_at=now,
            evaluation_start=now,
            evaluation_end=now + timedelta(days=settings.evaluation_period_days),
        )
        session.add(pub)
        variant.status = "published"

        if variant.niche:
            variant.niche.status = "testing"

        session.flush()
        console.print(
            f"[green]Variant #{variant_id} marked as published (publication #{pub.id})[/green]"
        )
        console.print(f"  Evaluation period: {settings.evaluation_period_days} days")
        console.print(f"  Evaluation ends: {pub.evaluation_end.date()}")
        if asin:
            console.print(f"  ASIN: {asin}")
        else:
            console.print(f"  [dim]Add ASIN later: libro publish mark-published {variant_id} --asin <ASIN>[/dim]")


@app.command("list")
def list_publications(status: Optional[str] = typer.Option(None, help="Filter by decision")):
    """List publications."""
    with get_session() as session:
        query = session.query(Publication)
        if status:
            query = query.filter(Publication.decision == status)
        pubs = query.all()

        if not pubs:
            console.print("[dim]No publications found.[/dim]")
            return

        table = Table(title="Publications")
        table.add_column("ID", style="cyan")
        table.add_column("Title", max_width=35)
        table.add_column("ASIN")
        table.add_column("Published")
        table.add_column("Eval Ends")
        table.add_column("Decision", style="green")

        for p in pubs:
            title = p.variant.title[:35] if p.variant else "?"
            pub_date = p.published_at.strftime("%Y-%m-%d") if p.published_at else "—"
            eval_end = p.evaluation_end.strftime("%Y-%m-%d") if p.evaluation_end else "—"
            table.add_row(
                str(p.id),
                title,
                p.asin or "—",
                pub_date,
                eval_end,
                p.decision or "pending",
            )
        console.print(table)
