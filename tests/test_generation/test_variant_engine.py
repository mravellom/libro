"""Tests for the variant engine module."""

from libro.generation.variant_engine import generate_variants


def test_generate_variants_creates_correct_count(db_session, sample_niche, sample_products):
    variants = generate_variants(db_session, sample_niche.id, count=2)
    assert len(variants) == 2


def test_generated_variants_have_required_fields(db_session, sample_niche, sample_products):
    variants = generate_variants(db_session, sample_niche.id, count=2)
    for v in variants:
        assert v.title and len(v.title) > 0
        assert v.subtitle and len(v.subtitle) > 0
        assert v.description and len(v.description) > 0
        assert v.keywords and len(v.keywords) > 0


def test_generated_variants_have_valid_interior_type(db_session, sample_niche, sample_products):
    known_types = {
        "lined", "dotted", "grid", "gratitude", "planner",
        "anxiety", "fitness", "budget", "reading", "meal",
    }
    variants = generate_variants(db_session, sample_niche.id, count=2)
    for v in variants:
        assert v.interior_type in known_types, f"Unknown interior type: {v.interior_type}"


def test_hero_tier_page_count(db_session, sample_niche, sample_products):
    variants = generate_variants(db_session, sample_niche.id, count=2, tier="hero")
    for v in variants:
        assert v.page_count >= 150, f"Hero tier should have >= 150 pages, got {v.page_count}"
