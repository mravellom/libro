"""Dashboard — catalog metrics and revenue tracking."""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from libro.common.amazon import estimate_monthly_revenue
from libro.config import get_settings
from libro.models.niche import Niche
from libro.models.publication import Publication
from libro.models.variant import Variant
from libro.models.tracking import TrackingSnapshot

log = logging.getLogger(__name__)


@dataclass
class CatalogMetrics:
    """Global catalog performance metrics."""
    # Catalog counts
    total_niches: int = 0
    total_variants: int = 0
    total_published: int = 0
    total_ready: int = 0
    total_draft: int = 0

    # Decision breakdown
    decisions_scale: int = 0
    decisions_iterate: int = 0
    decisions_kill: int = 0
    decisions_pending: int = 0

    # Niche types
    evergreen_count: int = 0
    trending_count: int = 0

    # Revenue estimates
    estimated_monthly_revenue: float = 0.0
    estimated_annual_revenue: float = 0.0
    avg_revenue_per_book: float = 0.0

    # Targets
    target_catalog_size: int = 0
    target_net_per_book: float = 0.0
    target_monthly_revenue: float = 0.0
    catalog_progress_pct: float = 0.0

    # Marketplace breakdown
    marketplace_counts: dict[str, int] = field(default_factory=dict)

    # Series
    total_series: int = 0

    # Kill rate
    kill_rate_pct: float = 0.0
    scale_rate_pct: float = 0.0


def get_catalog_metrics(session: Session) -> CatalogMetrics:
    """Calculate comprehensive catalog metrics."""
    settings = get_settings()
    m = CatalogMetrics()

    # Catalog counts
    m.total_niches = session.query(Niche).count()
    m.total_variants = session.query(Variant).count()

    # Variant status breakdown
    m.total_published = session.query(Variant).filter(Variant.status == "published").count()
    m.total_ready = session.query(Variant).filter(Variant.status == "ready").count()
    m.total_draft = session.query(Variant).filter(Variant.status == "draft").count()

    # Publication decisions
    pubs = session.query(Publication).all()
    total_pubs = len(pubs)
    for pub in pubs:
        if pub.decision == "scale":
            m.decisions_scale += 1
        elif pub.decision == "iterate":
            m.decisions_iterate += 1
        elif pub.decision == "kill":
            m.decisions_kill += 1
        else:
            m.decisions_pending += 1

        # Marketplace breakdown
        mp = pub.marketplace or "com"
        m.marketplace_counts[mp] = m.marketplace_counts.get(mp, 0) + 1

    # Niche types
    m.evergreen_count = session.query(Niche).filter(Niche.niche_type == "evergreen").count()
    m.trending_count = session.query(Niche).filter(Niche.niche_type == "trending").count()

    # Revenue estimation from latest snapshots
    total_monthly_rev = 0.0
    active_books_with_revenue = 0
    for pub in pubs:
        if pub.decision == "kill":
            continue
        if pub.snapshots:
            latest = max(pub.snapshots, key=lambda s: s.captured_at)
            if latest.estimated_monthly_revenue:
                total_monthly_rev += latest.estimated_monthly_revenue
                active_books_with_revenue += 1

    m.estimated_monthly_revenue = round(total_monthly_rev, 2)
    m.estimated_annual_revenue = round(total_monthly_rev * 12, 2)
    m.avg_revenue_per_book = (
        round(total_monthly_rev / active_books_with_revenue, 2)
        if active_books_with_revenue > 0 else 0.0
    )

    # Kill/scale rates
    decided = m.decisions_scale + m.decisions_iterate + m.decisions_kill
    if decided > 0:
        m.kill_rate_pct = round(m.decisions_kill / decided * 100, 1)
        m.scale_rate_pct = round(m.decisions_scale / decided * 100, 1)

    # Targets
    m.target_catalog_size = settings.target_catalog_size
    m.target_net_per_book = settings.target_net_per_book
    m.target_monthly_revenue = round(settings.target_catalog_size * settings.target_net_per_book, 2)
    m.catalog_progress_pct = round(total_pubs / settings.target_catalog_size * 100, 1) if settings.target_catalog_size > 0 else 0.0

    # Series count
    from libro.models.series import Series
    m.total_series = session.query(Series).count()

    return m
