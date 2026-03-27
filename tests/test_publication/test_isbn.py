"""Tests for ISBN validation and barcode generation."""

import tempfile
from pathlib import Path

from libro.publication.isbn import validate_isbn13, generate_barcode, _calculate_check_digit


def test_valid_isbn13():
    result = validate_isbn13("978-3-16-148410-0")
    assert result.valid
    assert result.isbn13 == "9783161484100"


def test_valid_isbn13_no_hyphens():
    result = validate_isbn13("9783161484100")
    assert result.valid


def test_invalid_check_digit():
    result = validate_isbn13("9783161484109")
    assert not result.valid
    assert "check digit" in result.error.lower()


def test_invalid_length():
    result = validate_isbn13("978316")
    assert not result.valid
    assert "13 digits" in result.error


def test_invalid_prefix():
    result = validate_isbn13("1234567890123")
    assert not result.valid
    assert "978 or 979" in result.error


def test_calculate_check_digit():
    assert _calculate_check_digit("978316148410") == 0
    assert _calculate_check_digit("978014028002") == 9


def test_generate_barcode_png():
    with tempfile.TemporaryDirectory() as d:
        path = generate_barcode("9783161484100", Path(d) / "barcode.png")
        assert path.exists()
        assert path.stat().st_size > 0


def test_generate_barcode_invalid_isbn():
    import pytest
    with pytest.raises(ValueError, match="Invalid ISBN"):
        with tempfile.TemporaryDirectory() as d:
            generate_barcode("1234", Path(d) / "barcode.png")
