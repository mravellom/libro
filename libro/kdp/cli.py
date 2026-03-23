"""CLI commands for KDP semi-automated uploader."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from libro.database import get_session
from libro.models.variant import Variant

app = typer.Typer(help="KDP semi-automated uploader — fill forms, you confirm")
console = Console()


@app.command()
def login():
    """Open browser for manual KDP login."""
    from libro.kdp.uploader import KDPUploader
    from libro.config import get_settings

    settings = get_settings()
    uploader = KDPUploader(
        headless=False,
        delay_min=settings.kdp_delay_min,
        delay_max=settings.kdp_delay_max,
    )

    async def _run():
        ok = await uploader.start()
        if ok:
            console.print("[green]Login exitoso. Browser abierto.[/green]")
            console.print("[dim]Presiona Ctrl+C para cerrar[/dim]")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            console.print("[red]Login fallido[/red]")
        await uploader.close()

    asyncio.run(_run())


@app.command()
def upload(
    variant_id: int = typer.Argument(help="Variant ID to upload"),
):
    """Upload a single variant to KDP (semi-automated)."""
    from libro.kdp.uploader import KDPUploader
    from libro.config import get_settings

    settings = get_settings()

    # Validate variant exists and is ready
    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant:
            console.print(f"[red]Variant #{variant_id} not found[/red]")
            raise typer.Exit(1)
        if not variant.interior_pdf_path or not variant.cover_pdf_path:
            console.print(f"[red]Variant #{variant_id} missing PDF files[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold]Preparando upload:[/bold] {variant.title[:50]}")
        console.print(f"  Interior: {variant.interior_type} | Size: {variant.trim_size} | Pages: {variant.page_count}")

    uploader = KDPUploader(
        headless=False,
        delay_min=settings.kdp_delay_min,
        delay_max=settings.kdp_delay_max,
    )

    async def _run():
        ok = await uploader.start()
        if not ok:
            console.print("[red]Login fallido — abortando[/red]")
            await uploader.close()
            return

        with get_session() as session:
            result = await uploader.upload_variant(session, variant_id)

            if result.published:
                console.print(f"\n[green]Publicado exitosamente: variant #{variant_id}[/green]")
            elif result.skipped:
                console.print(f"\n[yellow]Saltado: variant #{variant_id}[/yellow]")
            elif result.error:
                console.print(f"\n[red]Error: {result.error}[/red]")

        await uploader.close()

    asyncio.run(_run())


@app.command()
def batch(
    limit: int = typer.Option(10, help="Max books to upload in this session"),
):
    """Upload a batch of ready variants to KDP."""
    from libro.kdp.uploader import KDPUploader
    from libro.config import get_settings

    settings = get_settings()

    # Get ready variants
    with get_session() as session:
        variants = (
            session.query(Variant)
            .filter(
                Variant.status == "ready",
                Variant.interior_pdf_path.isnot(None),
                Variant.cover_pdf_path.isnot(None),
            )
            .limit(limit)
            .all()
        )

        if not variants:
            console.print("[yellow]No hay variantes listas para subir[/yellow]")
            raise typer.Exit(0)

        variant_ids = [v.id for v in variants]

        console.print(f"\n[bold]Batch Upload — {len(variant_ids)} libros[/bold]")
        for v in variants:
            console.print(f"  #{v.id} | {v.title[:45]} | {v.interior_type}")

        console.print()

    uploader = KDPUploader(
        headless=False,
        delay_min=settings.kdp_delay_min,
        delay_max=settings.kdp_delay_max,
    )

    async def _run():
        ok = await uploader.start()
        if not ok:
            console.print("[red]Login fallido — abortando[/red]")
            await uploader.close()
            return

        with get_session() as session:
            result = await uploader.upload_batch(session, variant_ids)

        await uploader.close()

        # Summary
        console.print(f"\n{'=' * 60}")
        console.print(f"[bold]Resumen del Batch[/bold]")
        console.print(f"  Total: {result.total}")
        console.print(f"  [green]Publicados: {result.published}[/green]")
        console.print(f"  [yellow]Saltados: {result.skipped}[/yellow]")
        console.print(f"  [red]Errores: {result.errors}[/red]")

        if result.details:
            table = Table(title="Detalle")
            table.add_column("Variant", style="cyan")
            table.add_column("Estado")
            table.add_column("Nota")

            for d in result.details:
                if d.published:
                    estado = "[green]Publicado[/green]"
                elif d.skipped:
                    estado = "[yellow]Saltado[/yellow]"
                else:
                    estado = "[red]Error[/red]"
                table.add_row(
                    f"#{d.variant_id}",
                    estado,
                    d.error or "—",
                )
            console.print(table)

    asyncio.run(_run())


@app.command("status")
def upload_status():
    """Show upload pipeline status."""
    from libro.models.publication import Publication

    with get_session() as session:
        ready = (
            session.query(Variant)
            .filter(
                Variant.status == "ready",
                Variant.interior_pdf_path.isnot(None),
                Variant.cover_pdf_path.isnot(None),
            )
            .count()
        )
        published = session.query(Variant).filter(Variant.status == "published").count()
        draft = session.query(Variant).filter(Variant.status == "draft").count()
        total_pubs = session.query(Publication).count()

        console.print(f"\n[bold]KDP Upload Pipeline[/bold]")
        console.print(f"  [green]Listos para subir:  {ready}[/green]")
        console.print(f"  [blue]Ya publicados:      {published}[/blue]")
        console.print(f"  [dim]Borradores:         {draft}[/dim]")
        console.print(f"  [cyan]Publicaciones DB:   {total_pubs}[/cyan]")

        if ready > 0:
            console.print(f"\n  [dim]Subir con: libro kdp batch --limit {min(ready, 10)}[/dim]")
