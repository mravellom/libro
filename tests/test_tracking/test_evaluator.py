"""Tests for the performance evaluator."""

from datetime import datetime, timedelta

from libro.tracking.evaluator import PerformanceEvaluator
from libro.models.publication import Publication
from libro.models.tracking import TrackingSnapshot


def _make_publication() -> Publication:
    return Publication(
        variant_id=1,
        asin="B0TEST0001",
        published_at=datetime(2026, 1, 1),
        evaluation_start=datetime(2026, 1, 1),
        evaluation_end=datetime(2026, 1, 15),
    )


def _make_snapshots(
    pub_id: int = 1,
    bsrs: list[int] | None = None,
    reviews: list[int] | None = None,
    daily_sales: list[float] | None = None,
    monthly_rev: list[float] | None = None,
    count: int = 5,
) -> list[TrackingSnapshot]:
    bsrs = bsrs or [50000] * count
    reviews = reviews or [0] * count
    daily_sales = daily_sales or [None] * count
    monthly_rev = monthly_rev or [None] * count

    snaps = []
    for i in range(count):
        snaps.append(TrackingSnapshot(
            publication_id=pub_id,
            bsr=bsrs[i] if i < len(bsrs) else bsrs[-1],
            reviews_count=reviews[i] if i < len(reviews) else reviews[-1],
            estimated_daily_sales=daily_sales[i] if i < len(daily_sales) else daily_sales[-1],
            estimated_monthly_revenue=monthly_rev[i] if i < len(monthly_rev) else monthly_rev[-1],
            captured_at=datetime(2026, 1, 1) + timedelta(days=i),
        ))
    return snaps


def test_scale_recommendation():
    """Improving BSR + reviews + sales should recommend SCALE."""
    evaluator = PerformanceEvaluator()
    pub = _make_publication()

    snaps = _make_snapshots(
        bsrs=[80000, 60000, 40000, 30000, 20000],      # BSR improving
        reviews=[0, 1, 2, 3, 5],                         # Reviews growing
        daily_sales=[0.5, 1.0, 1.5, 2.0, 3.0],          # Sales growing
        monthly_rev=[10, 30, 50, 70, 100],               # Revenue growing
    )

    result = evaluator.evaluate(pub, snaps)
    assert result.recommendation == "scale", f"Expected scale, got {result.recommendation}"


def test_kill_recommendation():
    """Worsening BSR + no reviews + no sales should recommend KILL."""
    evaluator = PerformanceEvaluator()
    pub = _make_publication()

    snaps = _make_snapshots(
        bsrs=[100000, 200000, 300000, 400000, 500000],  # BSR worsening
        reviews=[0, 0, 0, 0, 0],                         # No reviews
        daily_sales=[0.1, 0.05, 0.03, 0.01, 0.01],      # Sales dying
        monthly_rev=[1, 0.5, 0.3, 0.1, 0.1],            # No revenue
    )

    result = evaluator.evaluate(pub, snaps)
    assert result.recommendation == "kill", f"Expected kill, got {result.recommendation}"


def test_iterate_with_few_snapshots():
    """Too few snapshots should recommend ITERATE with low confidence."""
    evaluator = PerformanceEvaluator()
    pub = _make_publication()

    snaps = _make_snapshots(count=2, bsrs=[50000, 45000])

    result = evaluator.evaluate(pub, snaps)
    assert result.recommendation == "iterate"
    assert result.confidence < 0.5


def test_iterate_mixed_signals():
    """Mixed metrics should recommend ITERATE."""
    evaluator = PerformanceEvaluator()
    pub = _make_publication()

    snaps = _make_snapshots(
        bsrs=[50000, 45000, 55000, 40000, 50000],  # BSR stable
        reviews=[0, 0, 1, 1, 1],                    # Some reviews
        daily_sales=[0.5, 0.6, 0.4, 0.7, 0.5],     # Moderate sales
        monthly_rev=[15, 18, 12, 20, 15],            # Marginal revenue
    )

    result = evaluator.evaluate(pub, snaps)
    assert result.recommendation == "iterate", f"Expected iterate, got {result.recommendation}"


def test_empty_snapshots():
    """No snapshots should return iterate with low confidence."""
    evaluator = PerformanceEvaluator()
    pub = _make_publication()

    result = evaluator.evaluate(pub, [])
    assert result.recommendation == "iterate"
    assert result.confidence <= 0.3


def test_metrics_populated():
    """Evaluation should populate metrics dict."""
    evaluator = PerformanceEvaluator()
    pub = _make_publication()

    snaps = _make_snapshots(
        bsrs=[50000, 40000, 30000, 25000, 20000],
        reviews=[0, 1, 2, 3, 4],
        daily_sales=[1.0, 1.5, 2.0, 2.5, 3.0],
        monthly_rev=[30, 45, 60, 75, 90],
    )

    result = evaluator.evaluate(pub, snaps)
    assert "bsr_first" in result.metrics
    assert "bsr_last" in result.metrics
    assert "avg_daily_sales" in result.metrics
    assert "reviews_gained" in result.metrics
