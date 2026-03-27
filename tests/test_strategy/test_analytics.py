"""Tests for advanced analytics module."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libro.database import Base
import libro.models  # noqa: F401
from libro.models import Niche, Variant, Publication
from libro.models.tracking import TrackingSnapshot
from libro.strategy.analytics import generate_analytics_report


@pytest.fixture
def analytics_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def populated_db(analytics_session):
    """Create niches, variants, publications, and snapshots for analytics."""
    session = analytics_session
    now = datetime.now(UTC)

    # Niche 1 — good performer
    n1 = Niche(keyword="gratitude journal", category="Self-Help", opportunity_score=0.8)
    session.add(n1)
    session.flush()

    v1 = Variant(niche_id=n1.id, title="Daily Gratitude", interior_type="gratitude",
                 trim_size="6x9", page_count=120, status="published")
    v2 = Variant(niche_id=n1.id, title="5-Minute Gratitude", interior_type="lined",
                 trim_size="6x9", page_count=100, status="published")
    session.add_all([v1, v2])
    session.flush()

    p1 = Publication(variant_id=v1.id, published_at=now - timedelta(days=60),
                     marketplace="com", decision="scale",
                     evaluation_start=now - timedelta(days=60),
                     evaluation_end=now - timedelta(days=39))
    p2 = Publication(variant_id=v2.id, published_at=now - timedelta(days=30),
                     marketplace="com", decision=None,
                     evaluation_start=now - timedelta(days=30),
                     evaluation_end=now - timedelta(days=9))
    session.add_all([p1, p2])
    session.flush()

    s1 = TrackingSnapshot(publication_id=p1.id, bsr=25000,
                          estimated_monthly_revenue=45.0, captured_at=now)
    s2 = TrackingSnapshot(publication_id=p2.id, bsr=80000,
                          estimated_monthly_revenue=12.0, captured_at=now)
    session.add_all([s1, s2])

    # Niche 2 — poor performer
    n2 = Niche(keyword="budget planner", category="Finance", opportunity_score=0.5)
    session.add(n2)
    session.flush()

    v3 = Variant(niche_id=n2.id, title="Monthly Budget Tracker", interior_type="grid",
                 trim_size="8.5x11", page_count=120, status="published")
    session.add(v3)
    session.flush()

    p3 = Publication(variant_id=v3.id, published_at=now - timedelta(days=45),
                     marketplace="com", decision="kill",
                     evaluation_start=now - timedelta(days=45),
                     evaluation_end=now - timedelta(days=24))
    session.add(p3)
    session.flush()

    s3 = TrackingSnapshot(publication_id=p3.id, bsr=500000,
                          estimated_monthly_revenue=1.0, captured_at=now)
    session.add(s3)

    session.commit()
    return session


def test_report_structure(populated_db):
    report = generate_analytics_report(populated_db)
    assert report.total_published == 3
    assert report.total_estimated_monthly_revenue > 0
    assert len(report.niche_roi) == 2
    assert len(report.top_performers) <= 10


def test_niche_roi_sorted_by_avg_revenue(populated_db):
    report = generate_analytics_report(populated_db)
    # Gratitude niche should be first (higher avg revenue)
    assert report.niche_roi[0].keyword == "gratitude journal"
    assert report.niche_roi[0].avg_revenue_per_book > report.niche_roi[1].avg_revenue_per_book


def test_cohorts_generated(populated_db):
    report = generate_analytics_report(populated_db)
    assert len(report.cohorts) > 0
    for c in report.cohorts:
        assert c.books_published > 0


def test_top_performers_ordered(populated_db):
    report = generate_analytics_report(populated_db)
    revenues = [p.estimated_monthly_revenue for p in report.top_performers]
    assert revenues == sorted(revenues, reverse=True)


def test_interior_type_stats(populated_db):
    report = generate_analytics_report(populated_db)
    assert "gratitude" in report.interior_type_stats
    assert "grid" in report.interior_type_stats
    assert report.interior_type_stats["gratitude"]["count"] >= 1


def test_empty_db_report(analytics_session):
    report = generate_analytics_report(analytics_session)
    assert report.total_published == 0
    assert report.niche_roi == []
    assert report.cohorts == []
