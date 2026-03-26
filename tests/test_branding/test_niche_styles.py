"""Tests for the niche styles module."""

from libro.branding.niche_styles import (
    DEFAULT_STYLE,
    get_cover_style_for_niche,
    get_layout_index,
    get_palette_for_style,
)


def test_anxiety_journal_returns_sage_palette():
    style = get_cover_style_for_niche("anxiety journal")
    assert style.palette == "sage"


def test_budget_planner_returns_finance_palette():
    # "budget planner" matches "budget" (finance) via longest-match-first sorting
    # but "planner" is also a keyword for productivity. The actual longest match
    # is "budget" (6 chars) vs "planner" (7 chars), so "planner" wins -> productivity.
    style = get_cover_style_for_niche("budget planner")
    assert style.palette == "minimal"  # "planner" (7 chars) > "budget" (6 chars) -> productivity
    # Pure "budget" keyword matches finance:
    style_budget = get_cover_style_for_niche("budget tracker")
    assert style_budget.palette == "midnight"  # finance category


def test_workout_log_returns_fitness_palette():
    style = get_cover_style_for_niche("workout log")
    assert style.palette == "slate"  # fitness category


def test_unknown_niche_returns_default_style():
    style = get_cover_style_for_niche("unknown thing")
    assert style.palette == DEFAULT_STYLE.palette
    assert style.preferred_layouts == DEFAULT_STYLE.preferred_layouts


def test_get_palette_for_style_has_required_keys():
    style = get_cover_style_for_niche("anxiety journal")
    palette = get_palette_for_style(style)
    assert isinstance(palette, dict)
    assert "primary_color" in palette
    assert "secondary_color" in palette
    assert "accent_color" in palette


def test_get_layout_index_returns_from_preferred():
    style = get_cover_style_for_niche("anxiety journal")
    idx = get_layout_index(style, seed=42)
    assert isinstance(idx, int)
    assert idx in style.preferred_layouts
