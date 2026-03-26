"""Tests for the title engine module."""

from libro.generation.personas import get_persona_by_name
from libro.generation.title_engine import GeneratedTitle, _clean_keyword, generate_title


def _get_test_persona():
    return get_persona_by_name("anxiety_warrior")


def test_generate_title_returns_generated_title():
    persona = _get_test_persona()
    result = generate_title("anxiety journal", persona, seed=42)
    assert isinstance(result, GeneratedTitle)
    assert result.title
    assert result.subtitle
    assert result.description
    assert result.keywords
    assert result.persona_name == "anxiety_warrior"


def test_title_no_duplicate_type_word():
    persona = _get_test_persona()
    result = generate_title("anxiety journal", persona, seed=42)
    # After _clean_keyword, "anxiety journal" becomes "Anxiety",
    # so "Journal Journal" should never appear.
    assert "Journal Journal" not in result.title
    assert "journal journal" not in result.title.lower()


def test_subtitle_length_within_limit():
    persona = _get_test_persona()
    result = generate_title("anxiety journal", persona, seed=42)
    assert len(result.subtitle) <= 200


def test_keywords_max_seven():
    persona = _get_test_persona()
    result = generate_title("anxiety journal", persona, seed=42)
    assert len(result.keywords) <= 7


def test_description_nonempty_and_under_4000():
    persona = _get_test_persona()
    result = generate_title("anxiety journal", persona, seed=42)
    assert len(result.description) > 0
    assert len(result.description) < 4000


def test_same_seed_produces_same_title():
    persona = _get_test_persona()
    a = generate_title("anxiety journal", persona, seed=123)
    b = generate_title("anxiety journal", persona, seed=123)
    assert a.title == b.title
    assert a.subtitle == b.subtitle


def test_different_seeds_produce_different_titles():
    persona = _get_test_persona()
    a = generate_title("anxiety journal", persona, seed=1)
    b = generate_title("anxiety journal", persona, seed=9999)
    # With different seeds and enough template variation, titles should differ.
    # In the unlikely case they match, at least subtitles should differ.
    assert a.title != b.title or a.subtitle != b.subtitle


def test_clean_keyword_strips_type_word():
    assert _clean_keyword("anxiety journal") == "Anxiety"


def test_clean_keyword_no_strip_single_word():
    assert _clean_keyword("hiking") == "Hiking"
