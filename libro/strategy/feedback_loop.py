"""Feedback loop — uses tracking data to improve future generation decisions.

Analyzes which niches, personas, interior types, and title patterns perform
best, then feeds those insights back into the variant generation pipeline.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from libro.models.niche import Niche
from libro.models.variant import Variant
from libro.models.publication import Publication
from libro.models.tracking import TrackingSnapshot

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NichePerformance:
    """Aggregated performance data for a niche."""
    niche_id: int
    keyword: str
    total_variants: int = 0
    published: int = 0
    scaled: int = 0
    killed: int = 0
    avg_bsr: float | None = None
    avg_revenue: float | None = None
    best_interior_type: str | None = None
    best_variant_title: str | None = None
    score: float = 0.0  # 0-1 composite performance score


@dataclass
class InteriorTypePerformance:
    """Performance aggregates per interior type."""
    interior_type: str
    total_published: int = 0
    avg_bsr: float | None = None
    avg_revenue: float | None = None
    scale_rate: float = 0.0  # % of publications that got "scale"
    kill_rate: float = 0.0


@dataclass
class FeedbackInsights:
    """Complete feedback analysis for the generation pipeline."""
    # Top performers
    top_niches: list[NichePerformance] = field(default_factory=list)
    worst_niches: list[NichePerformance] = field(default_factory=list)

    # Interior type rankings
    interior_rankings: list[InteriorTypePerformance] = field(default_factory=list)

    # Actionable signals
    recommended_niches_to_scale: list[str] = field(default_factory=list)
    recommended_niches_to_avoid: list[str] = field(default_factory=list)
    recommended_interior_types: list[str] = field(default_factory=list)
    recommended_page_counts: list[int] = field(default_factory=list)

    # Stats
    total_publications_analyzed: int = 0
    data_sufficient: bool = False


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_performance(session: Session, days: int = 90) -> FeedbackInsights:
    """Analyze publication performance and generate actionable insights.

    Args:
        session: DB session.
        days: How far back to look for data.

    Returns:
        FeedbackInsights with recommendations for the generation pipeline.
    """
    insights = FeedbackInsights()
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Get all publications with decisions
    pubs = (
        session.query(Publication)
        .filter(Publication.published_at >= cutoff)
        .all()
    )

    insights.total_publications_analyzed = len(pubs)
    if len(pubs) < 5:
        insights.data_sufficient = False
        log.info("Feedback loop: insufficient data (%d publications, need 5+)", len(pubs))
        return insights

    insights.data_sufficient = True

    # --- Niche performance ---
    insights.top_niches, insights.worst_niches = _analyze_niches(session, pubs)

    # --- Interior type performance ---
    insights.interior_rankings = _analyze_interior_types(session, pubs)

    # --- Generate recommendations ---
    _generate_recommendations(insights)

    return insights


def _analyze_niches(
    session: Session,
    pubs: list[Publication],
) -> tuple[list[NichePerformance], list[NichePerformance]]:
    """Analyze performance by niche."""
    niche_data: dict[int, NichePerformance] = {}

    for pub in pubs:
        if not pub.variant or not pub.variant.niche:
            continue

        niche = pub.variant.niche
        if niche.id not in niche_data:
            niche_data[niche.id] = NichePerformance(
                niche_id=niche.id,
                keyword=niche.keyword,
            )

        np = niche_data[niche.id]
        np.published += 1

        if pub.decision == "scale":
            np.scaled += 1
        elif pub.decision == "kill":
            np.killed += 1

        # Get latest snapshot for revenue/BSR
        latest = (
            session.query(TrackingSnapshot)
            .filter(TrackingSnapshot.publication_id == pub.id)
            .order_by(TrackingSnapshot.captured_at.desc())
            .first()
        )
        if latest:
            if latest.bsr:
                bsrs = [np.avg_bsr] if np.avg_bsr else []
                bsrs.append(float(latest.bsr))
                np.avg_bsr = sum(bsrs) / len(bsrs)
            if latest.estimated_monthly_revenue:
                revs = [np.avg_revenue] if np.avg_revenue else []
                revs.append(float(latest.estimated_monthly_revenue))
                np.avg_revenue = sum(revs) / len(revs)

    # Count total variants per niche
    for np in niche_data.values():
        np.total_variants = (
            session.query(Variant)
            .filter(Variant.niche_id == np.niche_id)
            .count()
        )

        # Find best performing variant
        best_pub = (
            session.query(Publication)
            .join(Variant, Publication.variant_id == Variant.id)
            .filter(Variant.niche_id == np.niche_id, Publication.decision == "scale")
            .first()
        )
        if best_pub and best_pub.variant:
            np.best_variant_title = best_pub.variant.title
            np.best_interior_type = best_pub.variant.interior_type

        # Composite score
        np.score = _compute_niche_score(np)

    all_niches = sorted(niche_data.values(), key=lambda x: x.score, reverse=True)
    top = all_niches[:10]
    worst = sorted(niche_data.values(), key=lambda x: x.score)[:5]

    return top, worst


def _compute_niche_score(np: NichePerformance) -> float:
    """Compute a 0-1 performance score for a niche."""
    if np.published == 0:
        return 0.0

    scale_rate = np.scaled / np.published
    kill_rate = np.killed / np.published

    # Revenue component (normalized: $100/mo = 1.0)
    rev_score = min(1.0, (np.avg_revenue or 0) / 100.0)

    # BSR component (lower is better, normalized: 50k = 1.0)
    bsr_score = 0.0
    if np.avg_bsr and np.avg_bsr > 0:
        bsr_score = min(1.0, 50_000 / np.avg_bsr)

    score = (
        scale_rate * 0.35
        + rev_score * 0.30
        + bsr_score * 0.20
        + (1 - kill_rate) * 0.15
    )
    return round(score, 3)


def _analyze_interior_types(
    session: Session,
    pubs: list[Publication],
) -> list[InteriorTypePerformance]:
    """Analyze performance by interior type."""
    type_data: dict[str, dict] = {}

    for pub in pubs:
        if not pub.variant:
            continue

        itype = pub.variant.interior_type
        if itype not in type_data:
            type_data[itype] = {
                "total": 0, "scaled": 0, "killed": 0,
                "bsrs": [], "revenues": [],
            }

        td = type_data[itype]
        td["total"] += 1
        if pub.decision == "scale":
            td["scaled"] += 1
        elif pub.decision == "kill":
            td["killed"] += 1

        latest = (
            session.query(TrackingSnapshot)
            .filter(TrackingSnapshot.publication_id == pub.id)
            .order_by(TrackingSnapshot.captured_at.desc())
            .first()
        )
        if latest:
            if latest.bsr:
                td["bsrs"].append(latest.bsr)
            if latest.estimated_monthly_revenue:
                td["revenues"].append(latest.estimated_monthly_revenue)

    results = []
    for itype, td in type_data.items():
        total = td["total"]
        results.append(InteriorTypePerformance(
            interior_type=itype,
            total_published=total,
            avg_bsr=sum(td["bsrs"]) / len(td["bsrs"]) if td["bsrs"] else None,
            avg_revenue=sum(td["revenues"]) / len(td["revenues"]) if td["revenues"] else None,
            scale_rate=td["scaled"] / total if total > 0 else 0,
            kill_rate=td["killed"] / total if total > 0 else 0,
        ))

    return sorted(results, key=lambda x: x.scale_rate, reverse=True)


def _generate_recommendations(insights: FeedbackInsights) -> None:
    """Generate actionable recommendations from analysis."""
    # Niches to scale: top performers with score > 0.5
    insights.recommended_niches_to_scale = [
        np.keyword for np in insights.top_niches
        if np.score > 0.5 and np.published >= 2
    ]

    # Niches to avoid: high kill rate, low score
    insights.recommended_niches_to_avoid = [
        np.keyword for np in insights.worst_niches
        if np.score < 0.2 and np.killed > 0
    ]

    # Best interior types by scale rate
    insights.recommended_interior_types = [
        it.interior_type for it in insights.interior_rankings
        if it.scale_rate > 0.3 and it.total_published >= 2
    ]

    # If no clear winners, recommend the most common types
    if not insights.recommended_interior_types and insights.interior_rankings:
        insights.recommended_interior_types = [
            insights.interior_rankings[0].interior_type,
        ]


# ---------------------------------------------------------------------------
# Integration with variant engine
# ---------------------------------------------------------------------------

def get_generation_hints(session: Session) -> dict:
    """Get hints for the variant engine based on performance data.

    Returns a dict that can be passed to variant generation to inform
    which niches, interior types, and configurations to prioritize.
    """
    insights = analyze_performance(session)

    hints = {
        "data_sufficient": insights.data_sufficient,
        "niches_to_prioritize": insights.recommended_niches_to_scale,
        "niches_to_avoid": insights.recommended_niches_to_avoid,
        "preferred_interior_types": insights.recommended_interior_types,
        "insights_summary": _format_summary(insights),
    }

    if insights.data_sufficient:
        log.info(
            "Feedback loop: %d pubs analyzed | Scale: %s | Avoid: %s | Best interiors: %s",
            insights.total_publications_analyzed,
            insights.recommended_niches_to_scale[:3],
            insights.recommended_niches_to_avoid[:3],
            insights.recommended_interior_types[:3],
        )

    return hints


def _format_summary(insights: FeedbackInsights) -> str:
    """Format insights as a human-readable summary."""
    if not insights.data_sufficient:
        return (
            f"Insufficient data ({insights.total_publications_analyzed} publications). "
            "Need at least 5 publications with tracking data for meaningful insights."
        )

    lines = [
        f"Analyzed {insights.total_publications_analyzed} publications.",
    ]

    if insights.recommended_niches_to_scale:
        lines.append(f"Top niches to scale: {', '.join(insights.recommended_niches_to_scale[:5])}")

    if insights.recommended_niches_to_avoid:
        lines.append(f"Niches to avoid: {', '.join(insights.recommended_niches_to_avoid[:3])}")

    if insights.interior_rankings:
        best = insights.interior_rankings[0]
        lines.append(
            f"Best interior type: {best.interior_type} "
            f"(scale rate: {best.scale_rate:.0%}, avg revenue: ${best.avg_revenue or 0:.0f}/mo)"
        )

    if insights.top_niches:
        best_niche = insights.top_niches[0]
        lines.append(
            f"Best niche: {best_niche.keyword} "
            f"(score: {best_niche.score:.2f}, {best_niche.scaled}/{best_niche.published} scaled)"
        )

    return " | ".join(lines)
