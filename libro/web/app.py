"""FastAPI web dashboard for Libro KDP system."""

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from libro.database import get_session

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="Libro KDP Dashboard", version="0.1.0")


# --- Pydantic schemas for request bodies ---

class FloodRequest(BaseModel):
    target: int = 15
    dry_run: bool = False
    brand_id: int | None = None

class AutoKillRequest(BaseModel):
    days: int = 21

class SeriesRequest(BaseModel):
    count: int = 4

class CloneRequest(BaseModel):
    marketplace: str = "de"

class CoverABRequest(BaseModel):
    count: int = 3


# --- HTML Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main dashboard page."""
    return templates.TemplateResponse(request, "dashboard.html")


# --- API Endpoints ---

@app.get("/api/metrics")
def get_metrics():
    """Get catalog metrics."""
    from libro.strategy.dashboard import get_catalog_metrics
    with get_session() as session:
        metrics = get_catalog_metrics(session)
    return asdict(metrics)


@app.get("/api/niches")
def get_niches():
    """List all niches with scores."""
    from libro.models.niche import Niche
    with get_session() as session:
        niches = session.query(Niche).order_by(Niche.opportunity_score.desc()).all()
        return [
            {
                "id": n.id,
                "keyword": n.keyword,
                "niche_type": n.niche_type,
                "marketplace": n.marketplace,
                "opportunity_score": round(n.opportunity_score, 2),
                "demand_score": round(n.demand_score, 2),
                "competition_score": round(n.competition_score, 2),
                "trend_score": round(n.trend_score, 2),
                "avg_bsr": int(n.avg_bsr) if n.avg_bsr else None,
                "avg_price": round(n.avg_price, 2) if n.avg_price else None,
                "status": n.status,
            }
            for n in niches
        ]


@app.get("/api/variants")
def get_variants():
    """List all variants."""
    from libro.models.variant import Variant
    with get_session() as session:
        variants = session.query(Variant).order_by(Variant.created_at.desc()).all()
        return [
            {
                "id": v.id,
                "niche": v.niche.keyword if v.niche else "?",
                "title": v.title,
                "interior_type": v.interior_type,
                "trim_size": v.trim_size,
                "page_count": v.page_count,
                "has_interior": bool(v.interior_pdf_path),
                "has_cover": bool(v.cover_pdf_path),
                "series_name": v.series_name,
                "status": v.status,
            }
            for v in variants
        ]


@app.get("/api/publications")
def get_publications():
    """List all publications."""
    from libro.models.publication import Publication
    with get_session() as session:
        pubs = session.query(Publication).all()
        return [
            {
                "id": p.id,
                "title": p.variant.title[:50] if p.variant else "?",
                "asin": p.asin,
                "marketplace": p.marketplace,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "evaluation_end": p.evaluation_end.isoformat() if p.evaluation_end else None,
                "decision": p.decision or "pending",
                "impressions_detected": p.impressions_detected,
                "snapshot_count": len(p.snapshots) if p.snapshots else 0,
            }
            for p in pubs
        ]


# --- Action Endpoints ---

@app.post("/api/flood")
def run_flood(req: FloodRequest):
    """Execute flood pipeline."""
    from libro.strategy.flood import flood_pipeline
    with get_session() as session:
        result = flood_pipeline(
            session,
            daily_target=req.target,
            brand_id=req.brand_id,
            dry_run=req.dry_run,
        )
    return asdict(result)


@app.post("/api/auto-kill")
def run_auto_kill(req: AutoKillRequest):
    """Execute auto-kill check."""
    from libro.strategy.optimizer import auto_kill_check
    with get_session() as session:
        result = auto_kill_check(session, days=req.days)
    return asdict(result)


@app.post("/api/series/{pub_id}")
def run_series(pub_id: int, req: SeriesRequest):
    """Generate series from a winning publication."""
    from libro.strategy.optimizer import generate_series
    with get_session() as session:
        result = generate_series(session, pub_id, count=req.count)
    return asdict(result)


@app.post("/api/cover-ab/{variant_id}")
def run_cover_ab(variant_id: int, req: CoverABRequest):
    """Generate A/B cover variants."""
    from libro.strategy.optimizer import generate_cover_variants
    with get_session() as session:
        result = generate_cover_variants(session, variant_id, count=req.count)
    return asdict(result)


@app.post("/api/clone/{variant_id}")
def run_clone(variant_id: int, req: CloneRequest):
    """Clone variant for another marketplace."""
    from libro.strategy.scaler import clone_for_marketplace
    with get_session() as session:
        result = clone_for_marketplace(session, variant_id, req.marketplace)
    return asdict(result)


# --- KDP Deploy Pipeline ---

class DeployRequest(BaseModel):
    limit: int = 10


@app.get("/api/deploy/status")
def deploy_status():
    """Get KDP deploy pipeline status."""
    from libro.models.variant import Variant
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

        # Get list of ready variants for the deploy queue
        ready_variants = (
            session.query(Variant)
            .filter(
                Variant.status == "ready",
                Variant.interior_pdf_path.isnot(None),
                Variant.cover_pdf_path.isnot(None),
            )
            .order_by(Variant.id)
            .limit(50)
            .all()
        )

        queue = [
            {
                "id": v.id,
                "title": v.title[:50],
                "niche": v.niche.keyword if v.niche else "?",
                "interior_type": v.interior_type,
                "trim_size": v.trim_size,
                "page_count": v.page_count,
            }
            for v in ready_variants
        ]

        return {
            "ready": ready,
            "published": published,
            "draft": draft,
            "total_publications": total_pubs,
            "queue": queue,
        }


@app.post("/api/deploy/launch")
def launch_deploy(req: DeployRequest):
    """Launch KDP deploy process in a new terminal window.

    This opens a terminal with the semi-automated uploader because
    it requires a visible browser + user interaction (login, confirm publish).
    """
    import subprocess
    import shutil

    limit = req.limit
    cmd = f"cd /home/fabian/workSpace/Libro && source .venv/bin/activate && libro kdp batch --limit {limit}"

    # Try to open in a new terminal window
    terminal = None
    for term in ["gnome-terminal", "xfce4-terminal", "konsole", "xterm"]:
        if shutil.which(term):
            terminal = term
            break

    if terminal == "gnome-terminal":
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"{cmd}; echo ''; echo 'Presiona Enter para cerrar...'; read"])
    elif terminal == "xfce4-terminal":
        subprocess.Popen(["xfce4-terminal", "-e", f"bash -c \"{cmd}; echo ''; echo 'Presiona Enter para cerrar...'; read\""])
    elif terminal == "konsole":
        subprocess.Popen(["konsole", "-e", "bash", "-c", f"{cmd}; echo ''; echo 'Presiona Enter para cerrar...'; read"])
    elif terminal == "xterm":
        subprocess.Popen(["xterm", "-e", f"bash -c \"{cmd}; echo ''; echo 'Presiona Enter para cerrar...'; read\""])
    else:
        return {"launched": False, "error": "No terminal emulator found", "manual_command": f"libro kdp batch --limit {limit}"}

    return {
        "launched": True,
        "terminal": terminal,
        "limit": limit,
        "message": f"Deploy launched in {terminal} — {limit} books",
    }
