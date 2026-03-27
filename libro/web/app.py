"""FastAPI web dashboard for Libro KDP system."""

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from libro.database import get_session, ensure_schema

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="Libro KDP Dashboard", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup_migrate():
    """Auto-migrate DB schema on app startup."""
    ensure_schema()


# --- Pydantic schemas for request bodies ---

class FloodRequest(BaseModel):
    target: int = 3
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

class ReviewRequest(BaseModel):
    action: str  # "approve" or "reject"
    notes: str = ""

class BatchReviewRequest(BaseModel):
    variant_ids: list[int]
    action: str  # "approve" or "reject"

class DecisionRequest(BaseModel):
    decision: str  # "scale", "iterate", "kill", "snooze"
    snooze_days: int = 7

class BatchDecisionRequest(BaseModel):
    decisions: list[dict]  # [{"pub_id": 1, "decision": "scale"}, ...]


# --- HTML Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main dashboard page."""
    return templates.TemplateResponse(request, "dashboard.html")


# --- File Preview ---

@app.get("/api/preview/{variant_id}/interior")
def preview_interior(variant_id: int):
    """Serve interior PDF for in-browser preview."""
    from libro.models.variant import Variant
    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant or not variant.interior_pdf_path:
            return {"error": "Interior PDF not found"}
        pdf_path = Path(variant.interior_pdf_path)
        if not pdf_path.exists():
            return {"error": f"File not found: {pdf_path}"}
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"interior_{variant_id}.pdf")


@app.get("/api/preview/{variant_id}/cover")
def preview_cover(variant_id: int):
    """Serve cover image for preview."""
    from libro.models.variant import Variant
    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant or not variant.cover_pdf_path:
            return {"error": "Cover not found"}
        cover_path = Path(variant.cover_pdf_path)
        if not cover_path.exists():
            return {"error": f"File not found: {cover_path}"}
    suffix = cover_path.suffix.lower()
    media = "image/png" if suffix == ".png" else "image/jpeg" if suffix in (".jpg", ".jpeg") else "application/pdf"
    return FileResponse(cover_path, media_type=media, filename=f"cover_{variant_id}{suffix}")


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


# --- Human Review Gate ---

@app.get("/api/pending-review")
def get_pending_review():
    """List all variants awaiting human review."""
    from libro.models.variant import Variant
    with get_session() as session:
        variants = (
            session.query(Variant)
            .filter(Variant.status == "pending_review")
            .order_by(Variant.created_at.desc())
            .all()
        )
        return [
            {
                "id": v.id,
                "title": v.title,
                "subtitle": v.subtitle,
                "niche": v.niche.keyword if v.niche else "?",
                "interior_type": v.interior_type,
                "trim_size": v.trim_size,
                "page_count": v.page_count,
                "interior_seed": v.interior_seed,
                "has_interior": bool(v.interior_pdf_path),
                "has_cover": bool(v.cover_pdf_path),
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in variants
        ]


@app.post("/api/review/batch")
def batch_review(req: BatchReviewRequest):
    """Approve or reject multiple variants."""
    from libro.models.variant import Variant
    results = []
    with get_session() as session:
        for vid in req.variant_ids:
            variant = session.get(Variant, vid)
            if not variant or variant.status != "pending_review":
                results.append({"variant_id": vid, "error": "not found or not pending"})
                continue
            variant.status = "ready" if req.action == "approve" else "rejected"
            results.append({"variant_id": vid, "new_status": variant.status})
    return {"results": results}


@app.post("/api/review/{variant_id}")
def review_variant(variant_id: int, req: ReviewRequest):
    """Approve or reject a variant."""
    from libro.models.variant import Variant
    with get_session() as session:
        variant = session.get(Variant, variant_id)
        if not variant:
            return {"error": f"Variant #{variant_id} not found"}
        if variant.status != "pending_review":
            return {"error": f"Variant #{variant_id} is not pending review (status: {variant.status})"}

        if req.action == "approve":
            variant.status = "ready"
        elif req.action == "reject":
            variant.status = "rejected"
        else:
            return {"error": f"Invalid action: {req.action}. Use 'approve' or 'reject'"}

        return {"variant_id": variant_id, "new_status": variant.status}


# --- Advisory Recommendations ---

@app.post("/api/evaluate")
def run_evaluate():
    """Run evaluation pipeline — generates recommendations without applying decisions."""
    from libro.strategy.optimizer import evaluate_all
    with get_session() as session:
        result = evaluate_all(session)
    return asdict(result)


@app.get("/api/recommendations")
def get_recommendations():
    """List publications with pending recommendations."""
    from libro.models.publication import Publication
    with get_session() as session:
        pubs = (
            session.query(Publication)
            .filter(
                Publication.recommended_decision.isnot(None),
                Publication.decision.is_(None),
            )
            .all()
        )
        import json
        return [
            {
                "id": p.id,
                "title": p.variant.title[:50] if p.variant else "?",
                "asin": p.asin,
                "marketplace": p.marketplace,
                "recommended_decision": p.recommended_decision,
                "confidence": round(p.recommendation_confidence or 0, 2),
                "reasons": json.loads(p.recommendation_reasons) if p.recommendation_reasons else [],
                "recommended_at": p.recommended_at.isoformat() if p.recommended_at else None,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "snapshot_count": len(p.snapshots) if p.snapshots else 0,
            }
            for p in pubs
        ]


@app.post("/api/decide/batch")
def decide_batch(req: BatchDecisionRequest):
    """Apply decisions to multiple publications at once."""
    from libro.models.publication import Publication
    from datetime import UTC, datetime, timedelta
    results = []
    with get_session() as session:
        for item in req.decisions:
            pub_id = item.get("pub_id")
            decision = item.get("decision")
            pub = session.get(Publication, pub_id)
            if not pub:
                results.append({"pub_id": pub_id, "error": "not found"})
                continue

            if decision == "snooze":
                snooze_days = item.get("snooze_days", 7)
                pub.snoozed_until = datetime.now(UTC) + timedelta(days=snooze_days)
                pub.recommended_decision = None
                pub.recommendation_confidence = None
                pub.recommendation_reasons = None
                pub.recommended_at = None
                results.append({"pub_id": pub_id, "snoozed_until": pub.snoozed_until.isoformat()})
            elif decision == "accept":
                if not pub.recommended_decision:
                    results.append({"pub_id": pub_id, "error": "no recommendation to accept"})
                    continue
                pub.decision = pub.recommended_decision
                pub.decided_at = datetime.now(UTC)
                results.append({"pub_id": pub_id, "decision": pub.decision})
            elif decision in ("scale", "iterate", "kill"):
                pub.decision = decision
                pub.decided_at = datetime.now(UTC)
                results.append({"pub_id": pub_id, "decision": pub.decision})
            else:
                results.append({"pub_id": pub_id, "error": f"invalid decision: {decision}"})
    return {"results": results}


@app.post("/api/decide/{pub_id}")
def decide_publication(pub_id: int, req: DecisionRequest):
    """Apply a human decision to a publication."""
    from libro.models.publication import Publication
    from datetime import UTC, datetime, timedelta
    with get_session() as session:
        pub = session.get(Publication, pub_id)
        if not pub:
            return {"error": f"Publication #{pub_id} not found"}

        if req.decision == "snooze":
            pub.snoozed_until = datetime.now(UTC) + timedelta(days=req.snooze_days)
            pub.recommended_decision = None
            pub.recommendation_confidence = None
            pub.recommendation_reasons = None
            pub.recommended_at = None
            return {"pub_id": pub_id, "snoozed_until": pub.snoozed_until.isoformat()}

        # "accept" applies the recommended_decision as the final decision
        decision = req.decision
        if decision == "accept":
            if not pub.recommended_decision:
                return {"error": f"Publication #{pub_id} has no recommendation to accept"}
            decision = pub.recommended_decision

        if decision not in ("scale", "iterate", "kill"):
            return {"error": f"Invalid decision: {decision}"}

        pub.decision = decision
        pub.decided_at = datetime.now(UTC)
        return {"pub_id": pub_id, "decision": pub.decision}


# --- KDP 5.4.8 Compliance ---

@app.get("/api/risk")
def get_risk_assessment():
    """Get portfolio-level 5.4.8 risk assessment."""
    from libro.strategy.compliance import assess_portfolio_risk
    from dataclasses import asdict
    with get_session() as session:
        risk = assess_portfolio_risk(session)
        return asdict(risk)


@app.post("/api/compliance/scan")
def run_compliance_scan():
    """Trigger full portfolio compliance scan."""
    from libro.strategy.compliance import assess_portfolio_risk
    from dataclasses import asdict
    with get_session() as session:
        risk = assess_portfolio_risk(session)
        return asdict(risk)


@app.get("/api/compliance/{variant_id}")
def get_compliance_check(variant_id: int):
    """Run compliance checklist on a single variant."""
    from libro.publication.checklist import run_compliance_checklist
    with get_session() as session:
        result = run_compliance_checklist(session, variant_id)
        return {
            "variant_id": result.variant_id,
            "passed": result.passed,
            "errors": [{"name": c.name, "message": c.message} for c in result.errors],
            "warnings": [{"name": c.name, "message": c.message} for c in result.warnings],
            "checks": [
                {"name": c.name, "passed": c.passed, "message": c.message, "severity": c.severity}
                for c in result.checks
            ],
        }


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
    log_file = "/tmp/libro_kdp_deploy.log"
    cmd = f"cd /home/fabian/workSpace/Libro && source .venv/bin/activate && libro kdp batch --limit {limit} 2>&1 | tee {log_file}"

    # Try to open in a new terminal window
    terminal = None
    for term in ["x-terminal-emulator", "qterminal", "gnome-terminal", "xfce4-terminal", "konsole", "kitty", "alacritty", "xterm"]:
        if shutil.which(term):
            terminal = term
            break

    full_cmd = f"{cmd}; echo ''; echo 'Presiona Enter para cerrar...'; read"

    if terminal == "gnome-terminal":
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", full_cmd])
    elif terminal in ("x-terminal-emulator", "qterminal", "lxterminal", "mate-terminal"):
        subprocess.Popen([terminal, "-e", f"bash -c '{full_cmd}'"])
    elif terminal == "xfce4-terminal":
        subprocess.Popen(["xfce4-terminal", "-e", f"bash -c \"{full_cmd}\""])
    elif terminal == "konsole":
        subprocess.Popen(["konsole", "-e", "bash", "-c", full_cmd])
    elif terminal in ("kitty", "alacritty", "wezterm"):
        subprocess.Popen([terminal, "-e", "bash", "-c", full_cmd])
    elif terminal == "xterm":
        subprocess.Popen(["xterm", "-e", f"bash -c \"{full_cmd}\""])
    else:
        return {"launched": False, "error": "No terminal emulator found", "manual_command": f"libro kdp batch --limit {limit}"}

    return {
        "launched": True,
        "terminal": terminal,
        "limit": limit,
        "log_file": log_file,
        "message": f"Deploy launched in {terminal} — {limit} books",
    }


@app.get("/api/deploy/log")
def deploy_log(lines: int = 100):
    """Read the last N lines of the deploy log."""
    log_path = Path("/tmp/libro_kdp_deploy.log")
    if not log_path.exists():
        return {"log": "", "exists": False}
    text = log_path.read_text()
    last_lines = text.strip().split("\n")[-lines:]
    return {"log": "\n".join(last_lines), "exists": True}


# --- Templates, Feedback & Seasonal ---

@app.get("/api/templates")
def get_templates():
    """List all available interior templates."""
    from libro.generation.interior import list_templates
    return list_templates()


@app.get("/api/feedback")
def get_feedback():
    """Get feedback loop insights."""
    from libro.strategy.feedback_loop import analyze_performance
    with get_session() as session:
        insights = analyze_performance(session)
    return {
        "data_sufficient": insights.data_sufficient,
        "total_analyzed": insights.total_publications_analyzed,
        "recommended_niches_to_scale": insights.recommended_niches_to_scale,
        "recommended_niches_to_avoid": insights.recommended_niches_to_avoid,
        "recommended_interior_types": insights.recommended_interior_types,
        "top_niches": [
            {"keyword": n.keyword, "score": n.score, "published": n.published, "scaled": n.scaled, "killed": n.killed}
            for n in insights.top_niches[:5]
        ],
        "interior_rankings": [
            {"interior_type": it.interior_type, "scale_rate": round(it.scale_rate, 2), "kill_rate": round(it.kill_rate, 2), "total": it.total_published, "avg_revenue": round(it.avg_revenue or 0, 2)}
            for it in insights.interior_rankings
        ],
    }


@app.get("/api/seasonal")
def get_seasonal():
    """Get upcoming seasonal niches."""
    from libro.generation.niche_enricher import get_seasonal_with_lead_time
    niches = get_seasonal_with_lead_time(weeks_ahead=6)
    return [{"keyword": kw, "interior_types": types} for kw, types in niches]


# --- Analytics ---

@app.get("/api/analytics")
def get_analytics():
    """Get full analytics report: ROI by niche, cohorts, performers."""
    from libro.strategy.analytics import generate_analytics_report
    from dataclasses import asdict
    with get_session() as session:
        report = generate_analytics_report(session)
    return {
        "generated_at": report.generated_at.isoformat(),
        "total_published": report.total_published,
        "total_estimated_monthly_revenue": round(report.total_estimated_monthly_revenue, 2),
        "niche_roi": [
            {
                "keyword": n.keyword,
                "published": n.published_count,
                "total_revenue": round(n.total_estimated_revenue, 2),
                "avg_per_book": round(n.avg_revenue_per_book, 2),
                "scale_rate": round(n.scale_rate, 2),
                "kill_rate": round(n.kill_rate, 2),
                "best_interior": n.best_interior_type,
            }
            for n in report.niche_roi
        ],
        "cohorts": [
            {
                "period": c.period,
                "books": c.books_published,
                "avg_bsr": int(c.avg_bsr) if c.avg_bsr else None,
                "avg_revenue": round(c.avg_revenue, 2),
                "scale": c.scale_count,
                "kill": c.kill_count,
                "pending": c.pending_count,
            }
            for c in report.cohorts
        ],
        "top_performers": [
            {
                "title": p.title,
                "niche": p.niche_keyword,
                "revenue": round(p.estimated_monthly_revenue, 2),
                "bsr": p.latest_bsr,
                "decision": p.decision,
            }
            for p in report.top_performers
        ],
        "bottom_performers": [
            {
                "title": p.title,
                "niche": p.niche_keyword,
                "revenue": round(p.estimated_monthly_revenue, 2),
                "bsr": p.latest_bsr,
                "decision": p.decision,
            }
            for p in report.bottom_performers
        ],
        "interior_types": report.interior_type_stats,
        "marketplaces": report.marketplace_stats,
    }


# --- ISBN & Barcode ---

@app.post("/api/barcode/{variant_id}")
def generate_barcode_endpoint(variant_id: int, isbn: str = ""):
    """Generate an EAN-13 barcode for a variant."""
    from libro.publication.isbn import validate_isbn13, generate_barcode
    from libro.config import get_settings

    if not isbn:
        return {"error": "ISBN is required", "valid": False}

    info = validate_isbn13(isbn)
    if not info.valid:
        return {"error": info.error, "valid": False}

    settings = get_settings()
    output_dir = settings.output_dir / f"variant_{variant_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    barcode_path = generate_barcode(isbn, output_dir / "barcode.png")
    return {
        "valid": True,
        "isbn": info.formatted,
        "barcode_path": str(barcode_path),
    }
