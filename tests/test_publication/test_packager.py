"""Tests for publication packaging."""

from libro.publication.metadata import generate_metadata, _suggest_price, KDPMetadata
from libro.publication.checklist import run_checklist, ChecklistResult
from libro.models.variant import Variant


def _make_variant(**kwargs) -> Variant:
    return Variant(
        niche_id=kwargs.get("niche_id", 1),
        title=kwargs.get("title", "Test Journal"),
        subtitle=kwargs.get("subtitle", "A Test Subtitle"),
        description=kwargs.get("description", "A test description."),
        keywords=kwargs.get("keywords", "journal, test, notebook"),
        interior_type=kwargs.get("interior_type", "lined"),
        trim_size=kwargs.get("trim_size", "6x9"),
        page_count=kwargs.get("page_count", 120),
    )


def test_generate_metadata():
    variant = _make_variant()
    meta = generate_metadata(variant, author="Test Author")

    assert meta.title == "Test Journal"
    assert meta.author == "Test Author"
    assert len(meta.keywords) <= 7
    assert len(meta.categories) == 2


def test_metadata_to_text():
    variant = _make_variant()
    meta = generate_metadata(variant, author="Test Author")
    text = meta.to_text()

    assert "Test Journal" in text
    assert "Test Author" in text
    assert "KDP METADATA" in text


def test_price_suggestion():
    assert _suggest_price(60) == "$6.99"
    assert _suggest_price(120) == "$7.99"
    assert _suggest_price(200) == "$9.99"
    assert _suggest_price(300) == "$12.99"


def test_keywords_max_seven():
    variant = _make_variant(keywords="a, b, c, d, e, f, g, h, i, j")
    meta = generate_metadata(variant)
    assert len(meta.keywords) <= 7


def test_checklist_no_files(db_session):
    """Variant without files should fail checklist."""
    variant = _make_variant()
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(variant)

    result = run_checklist(db_session, variant.id)
    assert not result.passed
    assert len(result.errors) > 0
