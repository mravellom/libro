"""CLI commands for market intelligence module."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.database import get_session
from libro.models.niche import Niche

app = typer.Typer(help="Market intelligence — discover and score niches")
console = Console()


@app.command()
def discover(
    keyword: str = typer.Argument(help="Keyword to search on Amazon"),
    max_pages: int = typer.Option(3, help="Max search result pages to scrape"),
    no_details: bool = typer.Option(False, help="Skip scraping individual product pages"),
    no_headless: bool = typer.Option(False, help="Show browser window (for debugging)"),
):
    """Scrape Amazon for a keyword and store products."""
    from libro.intelligence.discovery import run_discovery

    console.print(f"[yellow]Discovering niche:[/yellow] {keyword}")
    console.print(f"  Pages: {max_pages} | Details: {not no_details} | Headless: {not no_headless}")

    try:
        with console.status("[bold green]Scraping Amazon..."):
            result = run_discovery(
                keyword=keyword,
                max_pages=max_pages,
                enrich_details=not no_details,
                headless=not no_headless,
            )

        console.print(f"\n[green]Niche discovered:[/green] {result.keyword} (#{result.niche_id})")
        console.print(f"  Products found: {result.products_count}")
        console.print(f"  Avg BSR: {result.avg_bsr:,.0f}" if result.avg_bsr else "  Avg BSR: —")
        console.print(f"  Avg Price: ${result.avg_price:.2f}" if result.avg_price else "  Avg Price: —")
        console.print(f"  Avg Reviews: {result.avg_reviews:.0f}" if result.avg_reviews else "  Avg Reviews: —")
        console.print(f"\n[dim]Run 'libro intel show {result.niche_id}' for full details[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def enrich(niche_id: Optional[int] = typer.Option(None, help="Niche ID to enrich with Keepa data")):
    """Fetch Keepa data for scraped products."""
    console.print(f"[yellow]Enriching niche:[/yellow] {niche_id or 'all'}")
    console.print("[red]Not yet implemented — coming in Phase 2[/red]")


@app.command()
def score(
    niche_id: Optional[int] = typer.Option(None, help="Specific niche to score"),
    all_niches: bool = typer.Option(False, "--all", help="Score all unscored niches"),
):
    """Run scoring algorithm on niches."""
    console.print("[red]Not yet implemented — coming in Phase 2[/red]")


@app.command("list")
def list_niches(status: Optional[str] = typer.Option(None, help="Filter by status")):
    """List niches with their scores."""
    with get_session() as session:
        query = session.query(Niche)
        if status:
            query = query.filter(Niche.status == status)
        niches = query.order_by(Niche.opportunity_score.desc()).all()

        if not niches:
            console.print("[dim]No niches found.[/dim]")
            return

        table = Table(title="Niches")
        table.add_column("ID", style="cyan")
        table.add_column("Keyword")
        table.add_column("Score", justify="right")
        table.add_column("Demand", justify="right")
        table.add_column("Competition", justify="right")
        table.add_column("Trend", justify="right")
        table.add_column("Status", style="green")

        for n in niches:
            table.add_row(
                str(n.id),
                n.keyword,
                f"{n.opportunity_score:.2f}",
                f"{n.demand_score:.2f}",
                f"{n.competition_score:.2f}",
                f"{n.trend_score:.2f}",
                n.status,
            )
        console.print(table)


@app.command()
def show(niche_id: int = typer.Argument(help="Niche ID to display")):
    """Show detailed info about a niche and its products."""
    with get_session() as session:
        niche = session.get(Niche, niche_id)
        if not niche:
            console.print(f"[red]Niche #{niche_id} not found[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold]{niche.keyword}[/bold] (#{niche.id})")
        console.print(f"  Status: {niche.status}")
        console.print(f"  Opportunity: {niche.opportunity_score:.2f}")
        console.print(f"  Demand: {niche.demand_score:.2f} | Competition: {niche.competition_score:.2f}")
        console.print(f"  Trend: {niche.trend_score:.2f} | Stability: {niche.stability_score:.2f}")
        console.print(f"  Avg BSR: {niche.avg_bsr} | Avg Price: ${niche.avg_price or 0:.2f}")
        console.print(f"  Products tracked: {niche.top_products_count}")

        if niche.products:
            table = Table(title="Top Products")
            table.add_column("ASIN")
            table.add_column("Title", max_width=40)
            table.add_column("BSR", justify="right")
            table.add_column("Price", justify="right")
            table.add_column("Reviews", justify="right")
            table.add_column("Trend")

            for p in niche.products[:10]:
                table.add_row(
                    p.asin,
                    p.title[:40],
                    str(p.bsr or "—"),
                    f"${p.price:.2f}" if p.price else "—",
                    str(p.reviews_count),
                    p.bsr_trend or "—",
                )
            console.print(table)
