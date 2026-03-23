"""CLI commands for publication preparation module."""

from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console

from libro.config import get_settings
from libro.database import get_session
from libro.models.publication import Publication
from libro.models.variant import Variant

app = typer.Typer(help="Prepare and track KDP publications")
console = Console()


@app.command()
def prepare(variant_id: int = typer.Argument(help="Variant ID to package")):
    """Bundle everything for KDP upload."""
    console.print(f"[yellow]Preparing variant #{variant_id} for KDP[/yellow]")
    console.print("[red]Not yet implemented — coming in Phase 5[/red]")


@app.command()
def checklist(variant_id: int = typer.Argument(help="Variant ID to validate")):
    """Validate readiness for KDP upload."""
    console.print("[red]Not yet implemented — coming in Phase 5[/red]")


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
        session.flush()
        console.print(
            f"[green]Variant #{variant_id} marked as published. "
            f"Evaluation ends {pub.evaluation_end.date()}[/green]"
        )


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

        for p in pubs:
            v = p.variant
            console.print(
                f"  #{p.id} | {v.title[:40] if v else '?'} | "
                f"ASIN: {p.asin or '—'} | Decision: {p.decision or 'pending'}"
            )
