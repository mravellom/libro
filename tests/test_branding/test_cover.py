"""Tests for cover generation."""

import tempfile
from pathlib import Path

from PIL import Image

from libro.branding.cover import CoverGenerator, _hex_to_rgb
from libro.common.pdf_utils import get_cover_dimensions


def test_hex_to_rgb():
    assert _hex_to_rgb("#FF0000") == (255, 0, 0)
    assert _hex_to_rgb("#2D4A3E") == (45, 74, 62)
    assert _hex_to_rgb("FFFFFF") == (255, 255, 255)


def test_generate_cover():
    gen = CoverGenerator()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = gen.generate(
            title="Test Journal",
            subtitle="A Subtitle",
            author="Test Author",
            trim_size="6x9",
            page_count=120,
            output_path=Path(tmpdir) / "cover.png",
        )
        assert path.exists()
        img = Image.open(path)
        assert img.size[0] > 0
        assert img.size[1] > 0


def test_cover_dimensions_match_kdp():
    """Cover image dimensions should match KDP requirements."""
    gen = CoverGenerator()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = gen.generate(
            title="Test",
            trim_size="6x9",
            page_count=120,
            output_path=Path(tmpdir) / "cover.png",
        )
        img = Image.open(path)
        dims = get_cover_dimensions("6x9", 120)
        expected_w = int(dims.total_width * 300)
        expected_h = int(dims.total_height * 300)
        assert abs(img.size[0] - expected_w) <= 1
        assert abs(img.size[1] - expected_h) <= 1


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
