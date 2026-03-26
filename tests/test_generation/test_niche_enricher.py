"""Tests for the niche enricher module."""

from libro.generation.niche_enricher import (
    MicroNiche,
    expand_to_micro_niches,
    get_seasonal_niches,
    get_seasonal_with_lead_time,
)


def test_expand_returns_correct_count():
    niches = expand_to_micro_niches("anxiety journal", count=5, seed=42)
    assert len(niches) == 5
    assert all(isinstance(n, MicroNiche) for n in niches)


def test_micro_niche_keyword_contains_parent():
    niches = expand_to_micro_niches("anxiety journal", count=5, seed=42)
    for n in niches:
        assert "anxiety journal" in n.keyword


def test_seasonal_niches_december():
    niches = get_seasonal_niches(12)
    keywords = [kw for kw, _ in niches]
    assert any("christmas" in kw for kw in keywords)
    assert any("gift tracker" in kw for kw in keywords)


def test_seasonal_niches_january():
    niches = get_seasonal_niches(1)
    keywords = [kw for kw, _ in niches]
    assert any("new year" in kw for kw in keywords)


def test_seasonal_with_lead_time_returns_nonempty():
    niches = get_seasonal_with_lead_time()
    assert len(niches) > 0


def test_micro_niche_competition_modifier_range():
    niches = expand_to_micro_niches("anxiety journal", count=10, seed=42)
    for n in niches:
        assert 0 <= n.competition_modifier <= 1
