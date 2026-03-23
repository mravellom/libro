"""Tests for keyword analyzer."""

from libro.intelligence.keyword_analyzer import analyze_titles


def test_basic_analysis():
    titles = [
        "Gratitude Journal for Women: Daily 5-Minute Guide",
        "Gratitude Journal: Practice Positivity and Mindfulness",
        "Daily Gratitude Journal for Self-Care",
    ]
    result = analyze_titles(titles)

    # "gratitude" and "journal" should be top words
    words = [w for w, _ in result.top_words]
    assert "gratitude" in words
    assert "journal" in words

    # Should detect colon pattern
    assert any("Colon" in p for p in result.common_patterns)

    # Should suggest keywords
    assert len(result.suggested_keywords) > 0
    assert len(result.suggested_keywords) <= 7


def test_audience_detection():
    titles = [
        "Journal for Women",
        "Planner for Women",
        "Notebook for Kids",
    ]
    result = analyze_titles(titles)
    assert any("women" in p.lower() for p in result.common_patterns)


def test_empty_titles():
    result = analyze_titles([])
    assert result.top_words == []
    assert result.suggested_keywords == []
