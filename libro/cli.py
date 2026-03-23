"""Libro CLI — main entry point composing all module sub-apps."""

import typer
from rich.console import Console

app = typer.Typer(
    name="libro",
    help="KDP niche detection and book creation system",
    no_args_is_help=True,
)
console = Console()


# Register module sub-apps
from libro.intelligence.cli import app as intel_app
from libro.generation.cli import app as gen_app
from libro.branding.cli import app as brand_app
from libro.publication.cli import app as pub_app
from libro.tracking.cli import app as track_app
from libro.strategy.cli import app as strategy_app
from libro.kdp.cli import app as kdp_app

app.add_typer(intel_app, name="intel")
app.add_typer(gen_app, name="generate")
app.add_typer(brand_app, name="brand")
app.add_typer(pub_app, name="publish")
app.add_typer(track_app, name="track")
app.add_typer(strategy_app, name="strategy")
app.add_typer(kdp_app, name="kdp")


# Database commands
db_app = typer.Typer(help="Database utilities")
app.add_typer(db_app, name="db")


@db_app.command("init")
def db_init():
    """Create all database tables."""
    from libro.database import Base, get_engine
    import libro.models  # noqa: F401 — registers all models

    engine = get_engine()
    Base.metadata.create_all(engine)
    console.print("[green]Database initialized successfully.[/green]")


@db_app.command("reset")
def db_reset(
    confirm: bool = typer.Option(False, "--yes", help="Skip confirmation"),
):
    """Drop and recreate all tables (dev only)."""
    if not confirm:
        typer.confirm("This will DELETE all data. Continue?", abort=True)

    from libro.database import Base, get_engine
    import libro.models  # noqa: F401

    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    console.print("[green]Database reset complete.[/green]")


# Test fixtures
@db_app.command("test-fixtures")
def _init_test_fixtures():
    """Create test fixtures to verify models are working."""
    from libro.database import get_session
    from libro.models import Niche, Product, Brand

    # Create all tables first
    from libro.database import Base, get_engine
    import libro.models  # noqa: F401
    engine = get_engine()
    Base.metadata.create_all(engine)

    with get_session() as session:
        existing = session.query(Niche).filter(Niche.keyword == "test_niche").first()
        if existing:
            console.print("[yellow]Test fixtures already exist.[/yellow]")
            return

        niche = Niche(keyword="test_niche", category="Test")
        session.add(niche)
        session.flush()

        product = Product(
            asin="B0TEST0001",
            niche_id=niche.id,
            title="Test Product",
            bsr=50000,
            price=7.99,
            reviews_count=25,
        )
        session.add(product)

        brand = Brand(name="Test Brand")
        session.add(brand)

    console.print("[green]Test fixtures created.[/green]")


# Web dashboard
@app.command()
def web(
    port: int = typer.Option(8000, help="Port to listen on"),
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
):
    """Start the web dashboard server."""
    import uvicorn
    from libro.web.app import app as fastapi_app

    console.print(f"[green]Starting Libro dashboard at http://{host}:{port}[/green]")
    uvicorn.run(fastapi_app, host=host, port=port)
