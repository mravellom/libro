"""Tests for the niche scoring algorithm."""

from libro.intelligence.scorer import NicheScorer
from libro.models.niche import Niche
from libro.models.product import Product


def _make_niche(**kwargs) -> Niche:
    return Niche(
        keyword=kwargs.get("keyword", "test"),
    )


def _make_product(**kwargs) -> Product:
    return Product(
        asin=kwargs.get("asin", "B0TEST"),
        niche_id=kwargs.get("niche_id", 1),
        title=kwargs.get("title", "Test Product"),
        bsr=kwargs.get("bsr", None),
        price=kwargs.get("price", None),
        reviews_count=kwargs.get("reviews_count", 0),
        bsr_trend=kwargs.get("bsr_trend", None),
        bsr_30d_avg=kwargs.get("bsr_30d_avg", None),
        bsr_90d_avg=kwargs.get("bsr_90d_avg", None),
    )


def test_high_demand_low_competition():
    """Low BSR + few reviews = high opportunity."""
    scorer = NicheScorer()
    niche = _make_niche(keyword="easy niche")
    products = [
        _make_product(bsr=5000, price=9.99, reviews_count=10),
        _make_product(bsr=15000, price=8.99, reviews_count=20),
        _make_product(bsr=25000, price=7.99, reviews_count=5),
    ]
    score = scorer.score_niche(niche, products)

    assert score.demand > 0.7, f"Expected high demand, got {score.demand}"
    assert score.competition < 0.4, f"Expected low competition, got {score.competition}"
    assert score.opportunity > 0.6, f"Expected high opportunity, got {score.opportunity}"


def test_low_demand_high_competition():
    """High BSR + many reviews = low opportunity."""
    scorer = NicheScorer()
    niche = _make_niche(keyword="hard niche")
    products = [
        _make_product(bsr=400000, price=9.99, reviews_count=500),
        _make_product(bsr=450000, price=8.99, reviews_count=300),
        _make_product(bsr=480000, price=7.99, reviews_count=600),
    ]
    score = scorer.score_niche(niche, products)

    assert score.demand < 0.3, f"Expected low demand, got {score.demand}"
    assert score.competition > 0.7, f"Expected high competition, got {score.competition}"
    assert score.opportunity < 0.4, f"Expected low opportunity, got {score.opportunity}"


def test_no_products():
    """Empty product list should return zero scores."""
    scorer = NicheScorer()
    niche = _make_niche()
    score = scorer.score_niche(niche, [])

    assert score.opportunity == 0
    assert "No products" in score.reasons[0]


def test_trend_scoring():
    """Rising trend should score higher than falling."""
    scorer = NicheScorer()
    niche = _make_niche()

    rising_products = [
        _make_product(bsr=10000, price=9.99, reviews_count=20, bsr_trend="rising"),
        _make_product(bsr=20000, price=8.99, reviews_count=30, bsr_trend="rising"),
    ]
    falling_products = [
        _make_product(bsr=10000, price=9.99, reviews_count=20, bsr_trend="falling"),
        _make_product(bsr=20000, price=8.99, reviews_count=30, bsr_trend="falling"),
    ]

    rising_score = scorer.score_niche(niche, rising_products)
    falling_score = scorer.score_niche(niche, falling_products)

    assert rising_score.trend > falling_score.trend
    assert rising_score.opportunity > falling_score.opportunity


def test_stability_scoring():
    """Low divergence between 30d and 90d avg = high stability."""
    scorer = NicheScorer()
    niche = _make_niche()

    stable_products = [
        _make_product(bsr=10000, price=9.99, reviews_count=20, bsr_30d_avg=10000, bsr_90d_avg=10500),
    ]
    unstable_products = [
        _make_product(bsr=10000, price=9.99, reviews_count=20, bsr_30d_avg=10000, bsr_90d_avg=30000),
    ]

    stable_score = scorer.score_niche(niche, stable_products)
    unstable_score = scorer.score_niche(niche, unstable_products)

    assert stable_score.stability > unstable_score.stability


def test_low_price_penalized():
    """Products priced below minimum should reduce price score."""
    scorer = NicheScorer()
    niche = _make_niche()

    cheap = [_make_product(bsr=10000, price=3.99, reviews_count=10)]
    good_price = [_make_product(bsr=10000, price=9.99, reviews_count=10)]

    cheap_score = scorer.score_niche(niche, cheap)
    good_score = scorer.score_niche(niche, good_price)

    assert good_score.price > cheap_score.price
