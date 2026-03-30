"""Performance evaluator — recommends scale/iterate/kill decisions."""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from libro.common.amazon import estimate_daily_sales
from libro.models.publication import Publication
from libro.models.tracking import TrackingSnapshot

log = logging.getLogger(__name__)


@dataclass
class Evaluation:
    """Decision recommendation for a publication."""
    recommendation: str  # "scale" | "iterate" | "kill"
    confidence: float  # 0.0 to 1.0
    reasons: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


class PerformanceEvaluator:
    """Evaluates publication performance and recommends decisions.

    Decision logic:
    - SCALE: BSR trending down (improving), reviews growing, estimated sales > threshold
    - ITERATE: Mixed signals — some metrics good, some not
    - KILL: BSR trending up (worsening), no reviews, no sales
    """

    def __init__(
        self,
        min_daily_sales_scale: float = 1.0,
        min_daily_sales_iterate: float = 0.2,
        min_reviews_scale: int = 3,
        min_snapshots: int = 3,
    ):
        self.min_daily_sales_scale = min_daily_sales_scale
        self.min_daily_sales_iterate = min_daily_sales_iterate
        self.min_reviews_scale = min_reviews_scale
        self.min_snapshots = min_snapshots

    def evaluate(self, publication: Publication, snapshots: list[TrackingSnapshot]) -> Evaluation:
        """Evaluate a publication based on its tracking snapshots."""
        reasons: list[str] = []
        metrics: dict = {}

        if len(snapshots) < self.min_snapshots:
            return Evaluation(
                recommendation="iterate",
                confidence=0.3,
                reasons=[f"Only {len(snapshots)} snapshots (need {self.min_snapshots} for reliable evaluation)"],
                metrics={"snapshots": len(snapshots)},
            )

        # Sort by capture time
        sorted_snaps = sorted(snapshots, key=lambda s: s.captured_at)

        # Metrics
        bsr_trend = self._analyze_bsr_trend(sorted_snaps, reasons, metrics)
        sales_level = self._analyze_sales(sorted_snaps, reasons, metrics)
        review_growth = self._analyze_reviews(sorted_snaps, reasons, metrics)
        revenue = self._analyze_revenue(sorted_snaps, reasons, metrics)

        # Decision matrix
        score = 0.0

        # BSR trend (weight: 0.3)
        if bsr_trend == "improving":
            score += 0.3
        elif bsr_trend == "stable":
            score += 0.15
        # else: worsening = 0

        # Sales level (weight: 0.3)
        if sales_level == "good":
            score += 0.3
        elif sales_level == "moderate":
            score += 0.15

        # Reviews (weight: 0.2)
        if review_growth == "growing":
            score += 0.2
        elif review_growth == "some":
            score += 0.1

        # Revenue (weight: 0.2)
        if revenue == "profitable":
            score += 0.2
        elif revenue == "marginal":
            score += 0.1

        # Map score to decision
        if score >= 0.6:
            recommendation = "scale"
            confidence = min(1.0, score)
        elif score >= 0.3:
            recommendation = "iterate"
            confidence = 0.5
        else:
            recommendation = "kill"
            confidence = min(1.0, 1.0 - score)

        reasons.append(f"Overall score: {score:.2f} → {recommendation}")

        return Evaluation(
            recommendation=recommendation,
            confidence=round(confidence, 2),
            reasons=reasons,
            metrics=metrics,
        )

    def _analyze_bsr_trend(
        self, snapshots: list[TrackingSnapshot], reasons: list[str], metrics: dict
    ) -> str:
        """Analyze BSR trend over time. Lower BSR = better."""
        bsrs = [(s.captured_at, s.bsr) for s in snapshots if s.bsr is not None]
        if len(bsrs) < 2:
            reasons.append("BSR: insufficient data")
            return "unknown"

        first_bsr = bsrs[0][1]
        last_bsr = bsrs[-1][1]
        avg_bsr = sum(b for _, b in bsrs) / len(bsrs)
        min_bsr = min(b for _, b in bsrs)

        metrics["bsr_first"] = first_bsr
        metrics["bsr_last"] = last_bsr
        metrics["bsr_avg"] = round(avg_bsr)
        metrics["bsr_best"] = min_bsr

        change_pct = (last_bsr - first_bsr) / first_bsr * 100 if first_bsr > 0 else 0

        if change_pct < -10:
            reasons.append(f"BSR improving: {first_bsr:,} → {last_bsr:,} ({change_pct:+.0f}%)")
            return "improving"
        elif change_pct > 20:
            reasons.append(f"BSR worsening: {first_bsr:,} → {last_bsr:,} ({change_pct:+.0f}%)")
            return "worsening"
        else:
            reasons.append(f"BSR stable: {first_bsr:,} → {last_bsr:,} ({change_pct:+.0f}%)")
            return "stable"

    def _analyze_sales(
        self, snapshots: list[TrackingSnapshot], reasons: list[str], metrics: dict
    ) -> str:
        """Analyze estimated daily sales."""
        sales = [s.estimated_daily_sales for s in snapshots if s.estimated_daily_sales is not None]
        if not sales:
            reasons.append("Sales: no estimates available")
            return "unknown"

        avg_sales = sum(sales) / len(sales)
        latest_sales = sales[-1]
        metrics["avg_daily_sales"] = round(avg_sales, 2)
        metrics["latest_daily_sales"] = round(latest_sales, 2)

        if avg_sales >= self.min_daily_sales_scale:
            reasons.append(f"Sales good: avg {avg_sales:.1f}/day")
            return "good"
        elif avg_sales >= self.min_daily_sales_iterate:
            reasons.append(f"Sales moderate: avg {avg_sales:.1f}/day")
            return "moderate"
        else:
            reasons.append(f"Sales low: avg {avg_sales:.2f}/day")
            return "low"

    def _analyze_reviews(
        self, snapshots: list[TrackingSnapshot], reasons: list[str], metrics: dict
    ) -> str:
        """Analyze review growth."""
        reviews = [(s.captured_at, s.reviews_count) for s in snapshots if s.reviews_count is not None]
        if not reviews:
            return "unknown"

        first_reviews = reviews[0][1]
        last_reviews = reviews[-1][1]
        gained = last_reviews - first_reviews

        metrics["reviews_start"] = first_reviews
        metrics["reviews_current"] = last_reviews
        metrics["reviews_gained"] = gained

        if gained >= self.min_reviews_scale:
            reasons.append(f"Reviews growing: +{gained} ({first_reviews} → {last_reviews})")
            return "growing"
        elif gained > 0:
            reasons.append(f"Some reviews: +{gained}")
            return "some"
        else:
            reasons.append(f"No new reviews ({last_reviews} total)")
            return "none"

    def _analyze_revenue(
        self, snapshots: list[TrackingSnapshot], reasons: list[str], metrics: dict
    ) -> str:
        """Analyze estimated monthly revenue."""
        revenues = [s.estimated_monthly_revenue for s in snapshots if s.estimated_monthly_revenue is not None]
        if not revenues:
            return "unknown"

        avg_rev = sum(revenues) / len(revenues)
        metrics["avg_monthly_revenue"] = round(avg_rev, 2)

        if avg_rev >= 50:
            reasons.append(f"Revenue profitable: ~${avg_rev:.0f}/month")
            return "profitable"
        elif avg_rev >= 10:
            reasons.append(f"Revenue marginal: ~${avg_rev:.0f}/month")
            return "marginal"
        else:
            reasons.append(f"Revenue minimal: ~${avg_rev:.2f}/month")
            return "minimal"


def evaluate_publication(session: Session, publication_id: int) -> Evaluation | None:
    """Evaluate a publication and return recommendation."""
    pub = session.get(Publication, publication_id)
    if not pub:
        return None

    snapshots = (
        session.query(TrackingSnapshot)
        .filter(TrackingSnapshot.publication_id == publication_id)
        .order_by(TrackingSnapshot.captured_at)
        .all()
    )

    evaluator = PerformanceEvaluator()
    return evaluator.evaluate(pub, snapshots)
