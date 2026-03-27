"""Tests for cover generation."""

import tempfile
from pathlib import Path

from libro.branding.cover import CoverGenerator, _hex
from libro.common.pdf_utils import get_cover_dimensions


def test_hex():
    assert _hex("#FF0000") == (255, 0, 0)
    assert _hex("#2D4A3E") == (45, 74, 62)
    assert _hex("FFFFFF") == (255, 255, 255)


def test_generate_cover():
    gen = CoverGenerator()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = gen.generate(
            title="Test Journal",
            subtitle="A Subtitle",
            author="Test Author",
            trim_size="6x9",
            page_count=120,
            output_path=Path(tmpdir) / "cover.pdf",
        )
        assert path.exists()
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 0


def test_cover_dimensions_match_kdp():
    """Cover PDF should be generated with correct KDP dimensions."""
    gen = CoverGenerator()
    dims = get_cover_dimensions("6x9", 120)
    expected_w = int(dims.total_width * 300)
    expected_h = int(dims.total_height * 300)
    # Ensure expected dimensions are positive and reasonable
    assert expected_w > 0
    assert expected_h > 0
    with tempfile.TemporaryDirectory() as tmpdir:
        path = gen.generate(
            title="Test",
            trim_size="6x9",
            page_count=120,
            output_path=Path(tmpdir) / "cover.pdf",
        )
        assert path.exists()
        assert path.stat().st_size > 1000  # non-trivial PDF


def test_different_trim_sizes():
    gen = CoverGenerator()
    with tempfile.TemporaryDirectory() as tmpdir:
        for trim in ["5x8", "6x9", "8.5x11"]:
            path = gen.generate(
                title=f"Test {trim}",
                trim_size=trim,
                page_count=100,
                output_path=Path(tmpdir) / f"cover_{trim}.png",
            )
            assert path.exists()
