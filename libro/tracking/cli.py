"""CLI commands for tracking module."""

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.database import get_session
from libro.models.publication import Publication

app = typer.Typer(help="Track published books and make decisions")
console = Console()


@app.command()
def snapshot(pub_id: Optional[int] = typer.Option(None, help="Publication ID")):
    """Capture current BSR/reviews for published books."""
    console.print("[red]Not yet implemented — coming in Phase 6[/red]")


@app.command()
def evaluate(pub_id: int = typer.Argument(help="Publication ID")):
    """Run decision logic on a publication."""
    console.print("[red]Not yet implemented — coming in Phase 6[/red]")


@app.command()
def decide(
    pub_id: int = typer.Argument(help="Publication ID"),
    decision: str = typer.Argument(help="scale | iterate | kill"),
):
    """Record a decision for a publication."""
    if decision not in ("scale", "iterate", "kill"):
        console.print("[red]Decision must be: scale, iterate, or kill[/red]")
        raise typer.Exit(1)

    with get_session() as session:
        pub = session.get(Publication, pub_id)
        if not pub:
            console.print(f"[red]Publication #{pub_id} not found[/red]")
            raise typer.Exit(1)

        pub.decision = decision
        pub.decided_at = datetime.utcnow()
        if pub.variant:
            pub.variant.niche.status = "scaled" if decision == "scale" else "killed"
        console.print(f"[green]Publication #{pub_id} → {decision}[/green]")


@app.command()
def report(pub_id: Optional[int] = typer.Option(None, help="Publication ID")):
    """Show performance summary."""
    with get_session() as session:
        query = session.query(Publication)
        if pub_id:
            query = query.filter(Publication.id == pub_id)
        pubs = query.all()

        for p in pubs:
            console.print(f"\n[bold]Publication #{p.id}[/bold] — {p.variant.title if p.variant else '?'}")
            console.print(f"  ASIN: {p.asin or '—'} | Decision: {p.decision or 'pending'}")

            if p.snapshots:
                table = Table()
                table.add_column("Date")
                table.add_column("BSR", justify="right")
                table.add_column("Reviews", justify="right")
                table.add_column("Est. Daily Sales", justify="right")
                table.add_column("Est. Monthly Rev", justify="right")

                for s in p.snapshots[-10:]:
                    table.add_row(
                        s.captured_at.strftime("%Y-%m-%d %H:%M"),
                        str(s.bsr or "—"),
                        str(s.reviews_count),
                        f"{s.estimated_daily_sales:.1f}" if s.estimated_daily_sales else "—",
                        f"${s.estimated_monthly_revenue:.0f}" if s.estimated_monthly_revenue else "—",
                    )
                console.print(table)
            else:
                console.print("  [dim]No snapshots yet[/dim]")


@app.command("cron-tick")
def cron_tick():
    """Entry point for cron: snapshot all active publications."""
    console.print("[red]Not yet implemented — coming in Phase 6[/red]")
