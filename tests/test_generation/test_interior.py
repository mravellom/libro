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
