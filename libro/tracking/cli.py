"""CLI commands for tracking module."""

from datetime import UTC, datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.database import get_session
from libro.models.publication import Publication

app = typer.Typer(help="Track published books and make decisions")
console = Console()


@app.command()
def snapshot(
    pub_id: Optional[int] = typer.Option(None, help="Publication ID"),
    all_active: bool = typer.Option(False, "--all", help="Snapshot all active publications"),
):
    """Capture current BSR/reviews for published books."""
    from libro.tracking.monitor import capture_snapshot, capture_all_active

    with get_session() as session:
        if pub_id:
            with console.status(f"[green]Capturing snapshot for publication #{pub_id}..."):
                snap = capture_snapshot(session, pub_id)
            if snap:
                console.print(f"[green]Snapshot captured:[/green]")
                console.print(f"  BSR: {snap.bsr or '—'}")
                console.print(f"  Reviews: {snap.reviews_count}")
                console.print(f"  Est. daily sales: {snap.estimated_daily_sales:.1f}" if snap.estimated_daily_sales else "  Est. daily sales: —")
                console.print(f"  Est. monthly rev: ${snap.estimated_monthly_revenue:.0f}" if snap.estimated_monthly_revenue else "  Est. monthly rev: —")
            else:
                console.print("[yellow]No snapshot captured (check ASIN)[/yellow]")

        elif all_active:
            with console.status("[green]Capturing snapshots for all active publications..."):
                snaps = capture_all_active(session)
            console.print(f"[green]{len(snaps)} snapshots captured[/green]")
            for s in snaps:
                console.print(f"  Pub #{s.publication_id}: BSR={s.bsr or '—'}, reviews={s.reviews_count}")

        else:
            console.print("[red]Specify --pub-id or --all[/red]")
            raise typer.Exit(1)


@app.command()
def evaluate(pub_id: int = typer.Argument(help="Publication ID")):
    """Run decision logic on a publication."""
    from libro.tracking.evaluator import evaluate_publication

    with get_session() as session:
        result = evaluate_publication(session, pub_id)
        if result is None:
            console.print(f"[red]Publication #{pub_id} not found[/red]")
            raise typer.Exit(1)

        pub = session.get(Publication, pub_id)
        title = pub.variant.title[:40] if pub and pub.variant else "?"

        # Color based on recommendation
        colors = {"scale": "green", "iterate": "yellow", "kill": "red"}
        color = colors.get(result.recommendation, "white")

        console.print(f"\n[bold]Evaluation: {title}[/bold]")
        console.print(f"  [{color}]Recommendation: {result.recommendation.upper()}[/{color}]")
        console.print(f"  Confidence: {result.confidence:.0%}")

        console.print(f"\n  [bold]Analysis:[/bold]")
        for reason in result.reasons:
            console.print(f"    → {reason}")

        if result.metrics:
            console.print(f"\n  [bold]Metrics:[/bold]")
            for key, val in result.metrics.items():
                if isinstance(val, float):
                    console.print(f"    {key}: {val:.2f}")
                else:
                    console.print(f"    {key}: {val}")


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
        pub.decided_at = datetime.now(UTC)

        # Update niche status
        if pub.variant and pub.variant.niche:
            if decision == "scale":
                pub.variant.niche.status = "scaled"
            elif decision == "kill":
                pub.variant.niche.status = "killed"

        colors = {"scale": "green", "iterate": "yellow", "kill": "red"}
        color = colors.get(decision, "white")
        console.print(f"[{color}]Publication #{pub_id} → {decision.upper()}[/{color}]")


@app.command()
def report(pub_id: Optional[int] = typer.Option(None, help="Publication ID")):
    """Show performance summary with tracking history."""
    with get_session() as session:
        query = session.query(Publication)
        if pub_id:
            query = query.filter(Publication.id == pub_id)
        pubs = query.all()

        if not pubs:
            console.print("[dim]No publications found.[/dim]")
            return

        for p in pubs:
            title = p.variant.title if p.variant else "?"
            console.print(f"\n[bold]Publication #{p.id}[/bold] — {title}")
            console.print(f"  ASIN: {p.asin or '—'} | Decision: {p.decision or 'pending'}")

            eval_status = ""
            if p.evaluation_end:
                if datetime.now(UTC) > p.evaluation_end:
                    eval_status = " [red](evaluation period ended)[/red]"
                else:
                    days_left = (p.evaluation_end - datetime.now(UTC)).days
                    eval_status = f" [dim]({days_left} days left)[/dim]"
            console.print(f"  Evaluation: {p.evaluation_start} → {p.evaluation_end}{eval_status}")

            if p.snapshots:
                table = Table()
                table.add_column("Date")
                table.add_column("BSR", justify="right")
                table.add_column("Reviews", justify="right")
                table.add_column("Est. Sales/day", justify="right")
                table.add_column("Est. Rev/month", justify="right")

                for s in sorted(p.snapshots, key=lambda x: x.captured_at)[-14:]:
                    table.add_row(
                        s.captured_at.strftime("%Y-%m-%d %H:%M"),
                        f"{s.bsr:,}" if s.bsr else "—",
                        str(s.reviews_count),
                        f"{s.estimated_daily_sales:.1f}" if s.estimated_daily_sales else "—",
                        f"${s.estimated_monthly_revenue:.0f}" if s.estimated_monthly_revenue else "—",
                    )
                console.print(table)
            else:
                console.print("  [dim]No snapshots yet. Run: libro track snapshot --pub-id {p.id}[/dim]")


@app.command("cron-tick")
def cron_tick():
    """Entry point for cron: snapshot all active publications."""
    from libro.tracking.cron import cron_tick as _cron_tick

    count = _cron_tick()
    console.print(f"[green]Cron tick complete: {count} snapshots[/green]")
