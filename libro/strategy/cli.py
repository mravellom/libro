"""CLI commands for strategy module — flooding, optimization, scaling."""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from libro.database import get_session

app = typer.Typer(help="KDP scaling strategy — flood, optimize, scale")
console = Console()


@app.command()
def flood(
    target: int = typer.Option(None, help="Daily book target (default from config)"),
    brand_id: Optional[int] = typer.Option(None, help="Brand ID to use for covers"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only, don't generate files"),
):
    """Execute flooding pipeline: produce books at scale.

    Generates variants, interiors, covers, and packages in batch.
    70% evergreen niches, 30% trending (configurable).
    """
    from libro.strategy.flood import flood_pipeline

    mode = "[yellow]DRY RUN[/yellow]" if dry_run else "[green]LIVE[/green]"
    console.print(f"\n[bold]Flood Pipeline[/bold] {mode}")

    with get_session() as session:
        with console.status("[bold green]Running flood pipeline..."):
            result = flood_pipeline(
                session,
                daily_target=target,
                brand_id=brand_id,
                dry_run=dry_run,
            )

    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Niches processed:    {result.niches_processed}")
    console.print(f"  Variants created:    {result.variants_created}")
    console.print(f"  Interiors generated: {result.interiors_generated}")
    console.print(f"  Covers generated:    {result.covers_generated}")
    console.print(f"  Packages ready:      {result.packages_ready}")

    if result.skipped_bsr:
        console.print(f"  [yellow]Skipped (BSR > threshold): {result.skipped_bsr}[/yellow]")

    if result.errors:
        console.print(f"\n  [red]Errors ({len(result.errors)}):[/red]")
        for err in result.errors:
            console.print(f"    → {err}")


@app.command("auto-kill")
def auto_kill(
    days: Optional[int] = typer.Option(None, help="Days without activity before kill (default 21)"),
):
    """Auto-kill publications without impressions after N days."""
    from libro.strategy.optimizer import auto_kill_check

    with get_session() as session:
        with console.status("[bold yellow]Checking publications for auto-kill..."):
            result = auto_kill_check(session, days=days)

    console.print(f"\n[bold]Auto-Kill Results:[/bold]")
    console.print(f"  Checked:  {result.checked}")
    console.print(f"  [red]Killed:   {result.killed}[/red]")
    console.print(f"  [green]Spared:   {result.spared}[/green]")

    if result.details:
        console.print(f"\n  [bold]Details:[/bold]")
        for detail in result.details:
            if "KILL" in detail:
                console.print(f"    [red]{detail}[/red]")
            else:
                console.print(f"    [green]{detail}[/green]")


@app.command()
def series(
    pub_id: int = typer.Argument(help="Publication ID of the winning book"),
    count: int = typer.Option(4, help="Number of series variants to create"),
):
    """Generate a product line from a winning publication.

    Takes a book with 'scale' decision and creates related variants
    with the same aesthetic for cross-selling on Amazon.
    """
    from libro.strategy.optimizer import generate_series

    with get_session() as session:
        with console.status("[bold green]Generating series..."):
            result = generate_series(session, pub_id, count=count)

    if result.variants_created:
        console.print(f"\n[green]Series created: {result.series_name}[/green]")
        console.print(f"  Variants generated: {result.variants_created}")
        for detail in result.details:
            console.print(f"    → {detail}")
        console.print(f"\n[dim]Generate interiors/covers with: libro strategy flood[/dim]")
    else:
        console.print(f"[yellow]No series created[/yellow]")
        for detail in result.details:
            console.print(f"  → {detail}")


@app.command("cover-ab")
def cover_ab(
    variant_id: int = typer.Argument(help="Variant ID to test"),
    count: int = typer.Option(3, help="Number of cover variants to generate"),
):
    """Generate A/B cover variants with different color palettes.

    Use when a book has impressions but low conversion (CTR).
    Creates multiple covers for manual A/B testing on Amazon.
    """
    from libro.strategy.optimizer import generate_cover_variants

    with get_session() as session:
        with console.status("[bold green]Generating A/B covers..."):
            result = generate_cover_variants(session, variant_id, count=count)

    if result.covers_generated:
        console.print(f"\n[green]A/B Covers generated for variant #{variant_id}:[/green]")
        for i, (path, palette) in enumerate(zip(result.paths, result.palettes_used)):
            console.print(f"  {i+1}. [{palette}] {path}")
        console.print(f"\n[dim]Upload each cover to Amazon and compare CTR[/dim]")
    else:
        console.print("[yellow]No covers generated[/yellow]")


@app.command()
def clone(
    variant_id: int = typer.Argument(help="Variant ID to clone"),
    marketplace: str = typer.Option(..., "--marketplace", "-m", help="Target marketplace (de, co.jp, co.uk)"),
):
    """Clone a variant for a different Amazon marketplace.

    Adapts the title for local discoverability. Interior PDFs
    are reused since low-content books are language-independent.
    """
    from libro.strategy.scaler import clone_for_marketplace

    with get_session() as session:
        result = clone_for_marketplace(session, variant_id, marketplace)

    if result.new_variant_id:
        console.print(f"\n[green]Cloned variant #{variant_id} → #{result.new_variant_id}[/green]")
        console.print(f"  Marketplace: {result.marketplace}")
        for note in result.notes:
            console.print(f"  → {note}")
        console.print(f"\n[dim]Generate cover: libro brand cover {result.new_variant_id}[/dim]")
    else:
        console.print("[red]Clone failed[/red]")
        for note in result.notes:
            console.print(f"  → {note}")


@app.command()
def status():
    """Show catalog dashboard with metrics and revenue targets."""
    from libro.strategy.dashboard import get_catalog_metrics

    with get_session() as session:
        m = get_catalog_metrics(session)

    # Header
    console.print(Panel("[bold]KDP Catalog Dashboard[/bold]", style="cyan"))

    # Catalog overview
    table = Table(title="Catalog Overview", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Total Niches", str(m.total_niches))
    table.add_row("Total Variants", str(m.total_variants))
    table.add_row("Published", str(m.total_published))
    table.add_row("Ready to Publish", str(m.total_ready))
    table.add_row("Drafts", str(m.total_draft))
    table.add_row("Series", str(m.total_series))
    table.add_row("", "")
    table.add_row("Evergreen Niches", str(m.evergreen_count))
    table.add_row("Trending Niches", str(m.trending_count))
    console.print(table)

    # Decisions
    table = Table(title="Publication Decisions")
    table.add_column("Decision", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Rate", justify="right")
    table.add_row("[green]Scale[/green]", str(m.decisions_scale), f"{m.scale_rate_pct}%")
    table.add_row("[yellow]Iterate[/yellow]", str(m.decisions_iterate), "—")
    table.add_row("[red]Kill[/red]", str(m.decisions_kill), f"{m.kill_rate_pct}%")
    table.add_row("Pending", str(m.decisions_pending), "—")
    console.print(table)

    # Revenue
    table = Table(title="Revenue Estimates")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Est. Monthly Revenue", f"${m.estimated_monthly_revenue:,.2f}")
    table.add_row("Est. Annual Revenue", f"${m.estimated_annual_revenue:,.2f}")
    table.add_row("Avg Revenue/Book/Month", f"${m.avg_revenue_per_book:.2f}")
    console.print(table)

    # Targets
    table = Table(title="Targets (The Math)")
    table.add_column("Metric", style="cyan")
    table.add_column("Current", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Progress", justify="right")

    pub_count = m.decisions_scale + m.decisions_iterate + m.decisions_pending
    table.add_row(
        "Catalog Size",
        str(pub_count),
        str(m.target_catalog_size),
        f"{m.catalog_progress_pct}%",
    )
    table.add_row(
        "Net/Book/Month",
        f"${m.avg_revenue_per_book:.2f}",
        f"${m.target_net_per_book:.2f}",
        f"{'OK' if m.avg_revenue_per_book >= m.target_net_per_book else 'below'}",
    )
    table.add_row(
        "Monthly Revenue",
        f"${m.estimated_monthly_revenue:,.2f}",
        f"${m.target_monthly_revenue:,.2f}",
        f"{m.estimated_monthly_revenue / m.target_monthly_revenue * 100:.1f}%" if m.target_monthly_revenue > 0 else "—",
    )
    console.print(table)

    # Marketplace breakdown
    if m.marketplace_counts:
        table = Table(title="By Marketplace")
        table.add_column("Marketplace", style="cyan")
        table.add_column("Publications", justify="right")
        for mp, count in sorted(m.marketplace_counts.items()):
            table.add_row(f"amazon.{mp}", str(count))
        console.print(table)
