"""CLI commands for market intelligence module."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.database import get_session
from libro.models.niche import Niche
from libro.models.product import Product

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
def enrich(
    niche_id: Optional[int] = typer.Option(None, help="Niche ID to enrich"),
    all_niches: bool = typer.Option(False, "--all", help="Enrich all niches"),
    max_tokens: int = typer.Option(50, help="Max Keepa tokens to spend"),
):
    """Fetch Keepa BSR history and trend data for products."""
    from libro.intelligence.keepa_client import KeepaClient

    try:
        keepa = KeepaClient()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    with get_session() as session:
        if niche_id:
            niches = [session.get(Niche, niche_id)]
            if not niches[0]:
                console.print(f"[red]Niche #{niche_id} not found[/red]")
                raise typer.Exit(1)
        elif all_niches:
            niches = session.query(Niche).all()
        else:
            console.print("[red]Specify --niche-id or --all[/red]")
            raise typer.Exit(1)

        for niche in niches:
            products = (
                session.query(Product)
                .filter(Product.niche_id == niche.id)
                .all()
            )

            if not products:
                console.print(f"[dim]Niche #{niche.id} has no products, skipping[/dim]")
                continue

            console.print(f"\n[yellow]Enriching:[/yellow] {niche.keyword} ({len(products)} products)")

            # Bulk fetch (more token-efficient)
            asins = [p.asin for p in products]
            # Process in batches of 100 (Keepa limit)
            for i in range(0, len(asins), 100):
                batch = asins[i:i + 100]

                # Check token budget
                if keepa.tokens_remaining is not None and keepa.tokens_remaining < 5:
                    console.print("[red]Keepa token budget exhausted[/red]")
                    keepa.close()
                    return

                with console.status(f"  Fetching Keepa data for {len(batch)} products..."):
                    keepa_products = keepa.get_products_bulk(batch)

                # Map Keepa data back to DB products
                keepa_map = {kp.asin: kp for kp in keepa_products}
                enriched = 0
                for product in products:
                    kp = keepa_map.get(product.asin)
                    if not kp:
                        continue

                    if kp.bsr_current is not None:
                        product.bsr = kp.bsr_current
                    product.bsr_30d_avg = kp.bsr_30d_avg
                    product.bsr_90d_avg = kp.bsr_90d_avg
                    product.bsr_trend = kp.bsr_trend
                    if kp.bsr_history:
                        product.bsr_history_json = json.dumps(kp.bsr_history[-100:])
                    if kp.review_count is not None:
                        product.reviews_count = kp.review_count
                    enriched += 1

                console.print(f"  [green]Enriched {enriched}/{len(batch)} products[/green]")

            # Recalculate niche aggregates
            _update_niche_aggregates(session, niche)

        tokens = keepa.tokens_remaining
        console.print(f"\n[dim]Keepa tokens remaining: {tokens}[/dim]")
        keepa.close()


@app.command()
def score(
    niche_id: Optional[int] = typer.Option(None, help="Specific niche to score"),
    all_niches: bool = typer.Option(False, "--all", help="Score all niches"),
):
    """Run scoring algorithm on niches."""
    from libro.intelligence.scorer import score_niche_in_db

    with get_session() as session:
        if niche_id:
            niches_to_score = [session.get(Niche, niche_id)]
            if not niches_to_score[0]:
                console.print(f"[red]Niche #{niche_id} not found[/red]")
                raise typer.Exit(1)
        elif all_niches:
            niches_to_score = session.query(Niche).all()
        else:
            # Score all unscored niches by default
            niches_to_score = (
                session.query(Niche)
                .filter(Niche.status == "discovered")
                .all()
            )

        if not niches_to_score:
            console.print("[dim]No niches to score.[/dim]")
            return

        for niche in niches_to_score:
            result = score_niche_in_db(session, niche.id)
            if result is None:
                continue

            # Color based on score
            if result.opportunity >= 0.7:
                color = "green"
            elif result.opportunity >= 0.4:
                color = "yellow"
            else:
                color = "red"

            console.print(f"\n[bold]{niche.keyword}[/bold] (#{niche.id})")
            console.print(f"  [{color}]Opportunity: {result.opportunity:.2f}[/{color}]")
            console.print(f"  Demand: {result.demand:.2f} | Competition: {result.competition:.2f}")
            console.print(f"  Trend: {result.trend:.2f} | Stability: {result.stability:.2f} | Price: {result.price:.2f}")
            for reason in result.reasons:
                console.print(f"  [dim]→ {reason}[/dim]")


@app.command()
def keywords(niche_id: int = typer.Argument(help="Niche ID to analyze")):
    """Analyze competitor titles for keyword opportunities."""
    from libro.intelligence.keyword_analyzer import analyze_titles

    with get_session() as session:
        niche = session.get(Niche, niche_id)
        if not niche:
            console.print(f"[red]Niche #{niche_id} not found[/red]")
            raise typer.Exit(1)

        products = (
            session.query(Product)
            .filter(Product.niche_id == niche_id)
            .all()
        )

        titles = [p.title for p in products]
        insight = analyze_titles(titles)

        console.print(f"\n[bold]Keyword Analysis:[/bold] {niche.keyword} ({len(titles)} titles)")

        # Top words
        if insight.top_words:
            table = Table(title="Top Words")
            table.add_column("Word")
            table.add_column("Count", justify="right")
            for word, count in insight.top_words[:15]:
                table.add_row(word, str(count))
            console.print(table)

        # Top bigrams
        if insight.top_bigrams:
            table = Table(title="Top Phrases")
            table.add_column("Phrase")
            table.add_column("Count", justify="right")
            for bigram, count in insight.top_bigrams:
                table.add_row(bigram, str(count))
            console.print(table)

        # Patterns
        if insight.common_patterns:
            console.print("\n[bold]Patterns detected:[/bold]")
            for p in insight.common_patterns:
                console.print(f"  → {p}")

        # Suggested keywords
        if insight.suggested_keywords:
            console.print(f"\n[bold]Suggested KDP keywords ({len(insight.suggested_keywords)}/7):[/bold]")
            for i, kw in enumerate(insight.suggested_keywords, 1):
                console.print(f"  {i}. {kw}")


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


def _update_niche_aggregates(session, niche: Niche) -> None:
    """Recalculate niche aggregate stats after enrichment."""
    products = (
        session.query(Product)
        .filter(Product.niche_id == niche.id)
        .all()
    )
    if not products:
        return

    niche.top_products_count = len(products)

    bsrs = [p.bsr for p in products if p.bsr is not None]
    niche.avg_bsr = sum(bsrs) / len(bsrs) if bsrs else None

    prices = [p.price for p in products if p.price is not None]
    niche.avg_price = sum(prices) / len(prices) if prices else None

    reviews = [p.reviews_count for p in products]
    niche.avg_reviews = sum(reviews) / len(reviews) if reviews else None

    # Review velocity (reviews/30 days from Keepa data)
    velocities = [p.review_velocity_30d for p in products if p.review_velocity_30d is not None]
    niche.avg_review_velocity = sum(velocities) / len(velocities) if velocities else None
