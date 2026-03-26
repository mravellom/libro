"""Tests for the intro pages module."""

import tempfile
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from libro.generation.templates.base import TrimSize
from libro.generation.templates.intro_pages import (
    INTRO_CONTENT,
    _DEFAULT_INTRO,
    draw_intro_pages,
)


EXPECTED_TYPES = [
    "lined", "dotted", "gratitude", "planner", "grid",
    "anxiety", "fitness", "budget", "reading", "meal",
]


def test_intro_content_has_all_10_types():
    for itype in EXPECTED_TYPES:
        assert itype in INTRO_CONTENT, f"Missing intro content for '{itype}'"


def test_each_entry_has_title_and_body():
    for itype in EXPECTED_TYPES:
        entry = INTRO_CONTENT[itype]
        assert "title" in entry, f"Missing 'title' for '{itype}'"
        assert "body" in entry, f"Missing 'body' for '{itype}'"
        assert len(entry["title"]) > 0
        assert len(entry["body"]) > 0


def test_draw_intro_pages_returns_2():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "intro_test.pdf"
        c = Canvas(str(pdf_path))
        trim = TrimSize("6x9")
        pages = draw_intro_pages(c, trim, "lined", title="Test Book")
        c.save()
        assert pages == 2


def test_unknown_type_uses_default_intro():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "default_intro.pdf"
        c = Canvas(str(pdf_path))
        trim = TrimSize("6x9")
        # Should not raise; falls back to _DEFAULT_INTRO
        pages = draw_intro_pages(c, trim, "totally_unknown_type")
        c.save()
        assert pages == 2
        assert pdf_path.exists()
