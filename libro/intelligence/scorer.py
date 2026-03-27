"""Niche scoring algorithm — pure computation, no I/O."""

import logging
from dataclasses import dataclass

from libro.config import get_settings
from libro.models.niche import Niche
from libro.models.product import Product

log = logging.getLogger(__name__)


@dataclass
class NicheScore:
    """Computed scores for a niche."""
    demand: float        # 0-1: how much demand exists
    competition: float   # 0-1: how hard to compete (lower = easier)
    trend: float         # 0-1: market momentum (higher = rising demand)
    stability: float     # 0-1: how stable the BSR is (higher = more predictable)
    price: float         # 0-1: price viability
    opportunity: float   # 0-1: weighted composite score
    reasons: list[str]   # Human-readable scoring notes


class NicheScorer:
    """Scores niches based on product data using weighted formula.

    Formula:
        opportunity = demand × W_d + (1 - competition) × W_c +
                      trend × W_t + stability × W_s + price × W_p

    Where W_d + W_c + W_t + W_s + W_p = 1.0
    """

    def __init__(self):
        settings = get_settings()
        self.w_demand = settings.weight_demand
        self.w_competition = settings.weight_competition
        self.w_trend = settings.weight_trend
        self.w_stability = settings.weight_stability
        self.w_price = settings.weight_price
        self.min_bsr = settings.min_bsr_for_demand
        self.max_reviews_low = settings.max_reviews_for_low_competition
        self.min_price = settings.min_price_for_margin

    def score_niche(self, niche: Niche, products: list[Product]) -> NicheScore:
        """Score a niche based on its scraped products."""
        reasons: list[str] = []

        if not products:
            return NicheScore(0, 0, 0, 0, 0, 0, ["No products to analyze"])

        demand = self._score_demand(products, reasons)
        competition = self._score_competition(products, reasons)
        trend = self._score_trend(products, reasons)
        stability = self._score_stability(products, reasons)
        price = self._score_price(products, reasons)

        opportunity = (
            demand * self.w_demand
            + (1 - competition) * self.w_competition
            + trend * self.w_trend
            + stability * self.w_stability
            + price * self.w_price
        )

        # Classify overall
        if opportunity >= 0.7:
            reasons.append(f"HIGH opportunity ({opportunity:.2f})")
        elif opportunity >= 0.4:
            reasons.append(f"MEDIUM opportunity ({opportunity:.2f})")
        else:
            reasons.append(f"LOW opportunity ({opportunity:.2f})")

        return NicheScore(
            demand=round(demand, 3),
            competition=round(competition, 3),
            trend=round(trend, 3),
            stability=round(stability, 3),
            price=round(price, 3),
            opportunity=round(opportunity, 3),
            reasons=reasons,
        )

    def _score_demand(self, products: list[Product], reasons: list[str]) -> float:
        """Score demand based on BSR distribution.

        High demand = many products with low BSR (selling well).
        """
        bsrs = [p.bsr for p in products if p.bsr is not None]
        if not bsrs:
            reasons.append("Demand: no BSR data available")
            return 0.5  # neutral when no data

        avg_bsr = sum(bsrs) / len(bsrs)
        # Products with BSR < threshold = validated demand
        strong_sellers = sum(1 for b in bsrs if b < 100_000)
        strong_ratio = strong_sellers / len(bsrs)

        # Normalize: BSR 1k → 1.0, BSR 500k → 0.0
        bsr_score = max(0, 1 - (avg_bsr / self.min_bsr))

        # Combine BSR score with ratio of strong sellers
        demand = bsr_score * 0.6 + strong_ratio * 0.4

        reasons.append(
            f"Demand: avg BSR {avg_bsr:,.0f}, "
            f"{strong_sellers}/{len(bsrs)} sell well → {demand:.2f}"
        )
        return min(1.0, max(0.0, demand))

    def _score_competition(self, products: list[Product], reasons: list[str]) -> float:
        """Score competition level (0 = no competition, 1 = very competitive).

        Low competition = many products with few reviews.
        """
        reviews = [p.reviews_count for p in products]
        if not reviews:
            reasons.append("Competition: no review data")
            return 0.5

        avg_reviews = sum(reviews) / len(reviews)
        # Products with < threshold reviews = beatable
        low_review_count = sum(1 for r in reviews if r < self.max_reviews_low)
        low_review_ratio = low_review_count / len(reviews)

        # Normalize: 0 reviews → 0.0, 200+ reviews → 1.0
        review_score = min(1.0, avg_reviews / 200)

        # High ratio of low-review products = lower competition
        competition = review_score * 0.6 + (1 - low_review_ratio) * 0.4

        reasons.append(
            f"Competition: avg {avg_reviews:.0f} reviews, "
            f"{low_review_count}/{len(reviews)} beatable → {competition:.2f}"
        )
        return min(1.0, max(0.0, competition))

    def _score_trend(self, products: list[Product], reasons: list[str]) -> float:
        """Score market trend based on BSR trend data.

        Rising = BSR going down = more sales = good.
        """
        trends = [p.bsr_trend for p in products if p.bsr_trend]
        if not trends:
            reasons.append("Trend: no trend data (enrich with Keepa for better scoring)")
            return 0.5  # neutral when no data

        rising = sum(1 for t in trends if t == "rising")
        stable = sum(1 for t in trends if t == "stable")
        falling = sum(1 for t in trends if t == "falling")
        total = len(trends)

        # Weighted: rising=1.0, stable=0.5, falling=0.0
        trend_score = (rising * 1.0 + stable * 0.5 + falling * 0.0) / total

        reasons.append(
            f"Trend: {rising} rising, {stable} stable, {falling} falling → {trend_score:.2f}"
        )
        return trend_score

    def _score_stability(self, products: list[Product], reasons: list[str]) -> float:
        """Score BSR stability based on 30d vs 90d average divergence.

        Stable BSR = predictable market = safer to enter.
        """
        divergences = []
        for p in products:
            if p.bsr_30d_avg and p.bsr_90d_avg and p.bsr_90d_avg > 0:
                # How much 30d differs from 90d (as ratio)
                div = abs(p.bsr_30d_avg - p.bsr_90d_avg) / p.bsr_90d_avg
                divergences.append(div)

        if not divergences:
            reasons.append("Stability: no historical data (enrich with Keepa)")
            return 0.5  # neutral

        avg_divergence = sum(divergences) / len(divergences)
        # Low divergence = high stability
        # 0% divergence → 1.0, 50%+ divergence → 0.0
        stability = max(0.0, 1 - (avg_divergence * 2))

        reasons.append(
            f"Stability: avg divergence {avg_divergence:.1%} → {stability:.2f}"
        )
        return stability

    def _score_price(self, products: list[Product], reasons: list[str]) -> float:
        """Score price viability.

        Books priced too low have thin margins. Sweet spot: $6.99-$14.99.
        """
        prices = [p.price for p in products if p.price is not None]
        if not prices:
            reasons.append("Price: no price data")
            return 0.5

        avg_price = sum(prices) / len(prices)
        viable = sum(1 for p in prices if p >= self.min_price)
        viable_ratio = viable / len(prices)

        # Score based on avg price position in sweet spot
        if avg_price >= self.min_price:
            # Higher price = better margin, but cap at 15
            price_score = min(1.0, avg_price / 15.0)
        else:
            price_score = avg_price / self.min_price * 0.5

        combined = price_score * 0.5 + viable_ratio * 0.5

        reasons.append(
            f"Price: avg ${avg_price:.2f}, "
            f"{viable}/{len(prices)} above ${self.min_price} → {combined:.2f}"
        )
        return min(1.0, max(0.0, combined))


def score_niche_in_db(session, niche_id: int) -> NicheScore | None:
    """Score a niche and update its DB record."""
    from libro.models.niche import Niche
    from libro.models.product import Product

    niche = session.get(Niche, niche_id)
    if not niche:
        return None

    products = (
        session.query(Product)
        .filter(Product.niche_id == niche_id)
        .all()
    )

    scorer = NicheScorer()
    score = scorer.score_niche(niche, products)

    # Update niche with scores
    niche.demand_score = score.demand
    niche.competition_score = score.competition
    niche.trend_score = score.trend
    niche.stability_score = score.stability
    niche.price_score = score.price
    niche.opportunity_score = score.opportunity
    niche.status = "scored"

    from datetime import UTC, datetime
    niche.scored_at = datetime.now(UTC)

    session.flush()
    return score
