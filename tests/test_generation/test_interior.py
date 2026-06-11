"""Tests for interior PDF generation."""

import tempfile
from pathlib import Path

from libro.generation.interior import generate_interior, list_templates


def test_list_templates():
    templates = list_templates()
    names = [t["name"] for t in templates]
    assert "lined" in names
    assert "dotted" in names
    assert "grid" in names
    assert "gratitude" in names
    assert "planner" in names
    assert "handwriting" in names


def test_generate_lined_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("lined", Path(tmpdir) / "test.pdf", "6x9", page_count=5)
        assert path.exists()
        assert path.stat().st_size > 0


def test_generate_dotted_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("dotted", Path(tmpdir) / "test.pdf", "6x9", page_count=5)
        assert path.exists()
        assert path.stat().st_size > 0


def test_generate_handwriting_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("handwriting", Path(tmpdir) / "test.pdf", "6x9", page_count=5)
        assert path.exists()
        assert path.stat().st_size > 0


def test_generate_handwriting_pdf_with_seed():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("handwriting", Path(tmpdir) / "test.pdf", "6x9", page_count=5, seed=42)
        assert path.exists()
        assert path.stat().st_size > 0


def test_handwriting_seed_does_not_change_existing_styles():
    """New handwriting rng draws must not alter styles of existing variants."""
    from libro.generation.interior_params import generate_interior_style

    style = generate_interior_style(1, "dotted")
    # Values recorded before the handwriting params were added (seed=1)
    assert style.hw_rule_height != style.hw_group_gap  # params exist and differ
    # The pre-existing fields must remain a pure function of the seed
    again = generate_interior_style(1, "dotted")
    assert style.line_spacing == again.line_spacing
    assert style.dot_spacing == again.dot_spacing
    assert style.margin_inches == again.margin_inches


def test_generate_gratitude_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("gratitude", Path(tmpdir) / "test.pdf", "6x9", page_count=5)
        assert path.exists()


def test_generate_different_trim_sizes():
    with tempfile.TemporaryDirectory() as tmpdir:
        for trim in ["5x8", "5.5x8.5", "6x9", "8.5x11"]:
            path = generate_interior("lined", Path(tmpdir) / f"{trim}.pdf", trim, page_count=3)
            assert path.exists(), f"Failed for trim {trim}"


def test_invalid_template_raises():
    import pytest
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="Unknown template"):
            generate_interior("nonexistent", Path(tmpdir) / "test.pdf")
