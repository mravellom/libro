"""Advanced analytics — ROI by niche, cohort analysis, performance ranking.

Provides insights for strategic decision-making:
- ROI per niche (revenue vs. effort)
- Cohort analysis (performance by publish date)
- Top/bottom performers
- Interior type effectiveness
- Marketplace comparison
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from libro.models.niche import Niche
from libro.models.publication import Publication
from libro.models.tracking import TrackingSnapshot
from libro.models.variant import Variant

log = logging.getLogger(__name__)


@dataclass
class NicheROI:
    """ROI metrics for a single niche."""
    niche_id: int
    keyword: str
    variants_count: int
    published_count: int
    total_estimated_revenue: float
    avg_revenue_per_book: float
    scale_rate: float  # fraction of books that got 'scale' decision
    kill_rate: float
    best_interior_type: str | None = None


@dataclass
class CohortMetrics:
    """Performance metrics for a cohort (books published in same period)."""
    period: str  # e.g. "2026-03" for March 2026
    books_published: int
    avg_bsr: float | None
    avg_revenue: float
    scale_count: int
    kill_count: int
    pending_count: int


@dataclass
class PerformerEntry:
    """A single book's performance summary."""
    variant_id: int
    title: str
    niche_keyword: str
    published_at: datetime | None
    latest_bsr: int | None
    estimated_monthly_revenue: float
    decision: str | None


@dataclass
class AnalyticsReport:
    """Full analytics report."""
    generated_at: datetime
    total_published: int
    total_estimated_monthly_revenue: float
    niche_roi: list[NicheROI]
    cohorts: list[CohortMetrics]
    top_performers: list[PerformerEntry]
    bottom_performers: list[PerformerEntry]
    interior_type_stats: dict[str, dict]
    marketplace_stats: dict[str, dict]


def generate_analytics_report(session: Session, top_n: int = 10) -> AnalyticsReport:
    """Generate a comprehensive analytics report."""
    now = datetime.now(UTC)

    niche_roi = _compute_niche_roi(session)
    cohorts = _compute_cohorts(session)
    top, bottom = _compute_performers(session, top_n)
    interior_stats = _compute_interior_type_stats(session)
    marketplace_stats = _compute_marketplace_stats(session)

    total_revenue = sum(n.total_estimated_revenue for n in niche_roi)
    total_published = sum(n.published_count for n in niche_roi)

    return AnalyticsReport(
        generated_at=now,
        total_published=total_published,
        total_estimated_monthly_revenue=total_revenue,
        niche_roi=sorted(niche_roi, key=lambda n: n.avg_revenue_per_book, reverse=True),
        cohorts=cohorts,
        top_performers=top,
        bottom_performers=bottom,
        interior_type_stats=interior_stats,
        marketplace_stats=marketplace_stats,
    )


def _compute_niche_roi(session: Session) -> list[NicheROI]:
    """Compute ROI metrics per niche."""
    niches = session.query(Niche).all()
    results = []

    for niche in niches:
        variants = session.query(Variant).filter(Variant.niche_id == niche.id).all()
        if not variants:
            continue

        publications = []
        for v in variants:
            pub = session.query(Publication).filter(Publication.variant_id == v.id).first()
            if pub:
                publications.append(pub)

        published_count = len(publications)
        if published_count == 0:
            continue

        # Sum estimated revenue from latest snapshots
        total_revenue = 0.0
        decisions = {"scale": 0, "iterate": 0, "kill": 0, "none": 0}
        best_interior = {}

        for pub in publications:
            latest = (
                session.query(TrackingSnapshot)
                .filter(TrackingSnapshot.publication_id == pub.id)
                .order_by(TrackingSnapshot.captured_at.desc())
                .first()
            )
            rev = latest.estimated_monthly_revenue if latest and latest.estimated_monthly_revenue else 0
            total_revenue += rev

            decision = pub.decision or "none"
            decisions[decision] = decisions.get(decision, 0) + 1

            # Track interior type performance
            variant = session.get(Variant, pub.variant_id)
            if variant and variant.interior_type:
                itype = variant.interior_type
                if itype not in best_interior:
                    best_interior[itype] = 0.0
                best_interior[itype] += rev

        total_decisions = sum(decisions.values())
        best_type = max(best_interior, key=best_interior.get) if best_interior else None

        results.append(NicheROI(
            niche_id=niche.id,
            keyword=niche.keyword,
            variants_count=len(variants),
            published_count=published_count,
            total_estimated_revenue=total_revenue,
            avg_revenue_per_book=total_revenue / published_count if published_count else 0,
            scale_rate=decisions["scale"] / total_decisions if total_decisions else 0,
            kill_rate=decisions["kill"] / total_decisions if total_decisions else 0,
            best_interior_type=best_type,
        ))

    return results


def _compute_cohorts(session: Session) -> list[CohortMetrics]:
    """Group publications by month and compute cohort metrics."""
    publications = (
        session.query(Publication)
        .filter(Publication.published_at.isnot(None))
        .order_by(Publication.published_at)
        .all()
    )

    cohorts: dict[str, list[Publication]] = {}
    for pub in publications:
        key = pub.published_at.strftime("%Y-%m")
        cohorts.setdefault(key, []).append(pub)

    results = []
    for period, pubs in sorted(cohorts.items()):
        bsr_values = []
        revenue_sum = 0.0
        scale = iterate = kill = pending = 0

        for pub in pubs:
            latest = (
                session.query(TrackingSnapshot)
                .filter(TrackingSnapshot.publication_id == pub.id)
                .order_by(TrackingSnapshot.captured_at.desc())
                .first()
            )
            if latest:
                if latest.bsr:
                    bsr_values.append(latest.bsr)
                revenue_sum += latest.estimated_monthly_revenue or 0

            d = pub.decision or "none"
            if d == "scale": scale += 1
            elif d == "kill": kill += 1
            elif d == "none": pending += 1

        results.append(CohortMetrics(
            period=period,
            books_published=len(pubs),
            avg_bsr=sum(bsr_values) / len(bsr_values) if bsr_values else None,
            avg_revenue=revenue_sum / len(pubs) if pubs else 0,
            scale_count=scale,
            kill_count=kill,
            pending_count=pending,
        ))

    return results


def _compute_performers(session: Session, top_n: int) -> tuple[list[PerformerEntry], list[PerformerEntry]]:
    """Get top and bottom performers by estimated revenue."""
    publications = session.query(Publication).filter(Publication.published_at.isnot(None)).all()

    entries = []
    for pub in publications:
        variant = session.get(Variant, pub.variant_id)
        if not variant:
            continue

        latest = (
            session.query(TrackingSnapshot)
            .filter(TrackingSnapshot.publication_id == pub.id)
            .order_by(TrackingSnapshot.captured_at.desc())
            .first()
        )

        niche = session.get(Niche, variant.niche_id) if variant.niche_id else None

        entries.append(PerformerEntry(
            variant_id=variant.id,
            title=variant.title,
            niche_keyword=niche.keyword if niche else "unknown",
            published_at=pub.published_at,
            latest_bsr=latest.bsr if latest else None,
            estimated_monthly_revenue=latest.estimated_monthly_revenue if latest else 0,
            decision=pub.decision,
        ))

    # Sort by revenue
    entries.sort(key=lambda e: e.estimated_monthly_revenue, reverse=True)

    top = entries[:top_n]
    bottom = list(reversed(entries[-top_n:])) if len(entries) > top_n else []

    return top, bottom


def _compute_interior_type_stats(session: Session) -> dict[str, dict]:
    """Revenue and performance stats by interior type."""
    variants = (
        session.query(Variant)
        .filter(Variant.status == "published")
        .all()
    )

    stats: dict[str, dict] = {}
    for v in variants:
        itype = v.interior_type or "unknown"
        if itype not in stats:
            stats[itype] = {"count": 0, "total_revenue": 0.0, "scale": 0, "kill": 0}

        stats[itype]["count"] += 1

        pub = session.query(Publication).filter(Publication.variant_id == v.id).first()
        if pub:
            if pub.decision == "scale":
                stats[itype]["scale"] += 1
            elif pub.decision == "kill":
                stats[itype]["kill"] += 1

            latest = (
                session.query(TrackingSnapshot)
                .filter(TrackingSnapshot.publication_id == pub.id)
                .order_by(TrackingSnapshot.captured_at.desc())
                .first()
            )
            if latest and latest.estimated_monthly_revenue:
                stats[itype]["total_revenue"] += latest.estimated_monthly_revenue

    # Add avg_revenue
    for itype, data in stats.items():
        data["avg_revenue"] = data["total_revenue"] / data["count"] if data["count"] else 0

    return stats


def _compute_marketplace_stats(session: Session) -> dict[str, dict]:
    """Performance stats by marketplace."""
    publications = session.query(Publication).filter(Publication.published_at.isnot(None)).all()

    stats: dict[str, dict] = {}
    for pub in publications:
        mp = pub.marketplace or "com"
        if mp not in stats:
            stats[mp] = {"count": 0, "total_revenue": 0.0, "scale": 0, "kill": 0}

        stats[mp]["count"] += 1

        if pub.decision == "scale":
            stats[mp]["scale"] += 1
        elif pub.decision == "kill":
            stats[mp]["kill"] += 1

        latest = (
            session.query(TrackingSnapshot)
            .filter(TrackingSnapshot.publication_id == pub.id)
            .order_by(TrackingSnapshot.captured_at.desc())
            .first()
        )
        if latest and latest.estimated_monthly_revenue:
            stats[mp]["total_revenue"] += latest.estimated_monthly_revenue

    for mp, data in stats.items():
        data["avg_revenue"] = data["total_revenue"] / data["count"] if data["count"] else 0

    return stats
