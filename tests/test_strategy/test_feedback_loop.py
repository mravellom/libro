"""Tests for the feedback loop module."""

from libro.strategy.feedback_loop import (
    NichePerformance,
    _compute_niche_score,
    analyze_performance,
    get_generation_hints,
)


def test_analyze_performance_empty_db(db_session):
    insights = analyze_performance(db_session)
    assert insights.data_sufficient is False
    assert insights.total_publications_analyzed == 0


def test_get_generation_hints_empty_db(db_session):
    hints = get_generation_hints(db_session)
    assert hints["data_sufficient"] is False
    assert hints["niches_to_prioritize"] == []
    assert hints["niches_to_avoid"] == []


def test_compute_niche_score_zero_published():
    np = NichePerformance(
        niche_id=1,
        keyword="test",
        total_variants=5,
        published=0,
    )
    assert _compute_niche_score(np) == 0.0
