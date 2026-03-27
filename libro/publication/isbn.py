"""ISBN management and barcode generation for KDP publications.

KDP provides free ISBNs, but for tracking and barcode placement on
back covers, we need to manage them locally. This module handles:
- ISBN-13 validation and formatting
- EAN-13 barcode generation as PNG/SVG
- Barcode image for back cover placement
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ISBNInfo:
    """Parsed ISBN information."""
    isbn13: str
    formatted: str  # e.g. 978-1-234567-89-0
    valid: bool
    error: str | None = None


def validate_isbn13(isbn: str) -> ISBNInfo:
    """Validate an ISBN-13 string and return parsed info."""
    # Strip hyphens and spaces
    clean = re.sub(r"[\s-]", "", isbn)

    if len(clean) != 13:
        return ISBNInfo(isbn13=clean, formatted=isbn, valid=False,
                        error=f"ISBN must be 13 digits, got {len(clean)}")

    if not clean.isdigit():
        return ISBNInfo(isbn13=clean, formatted=isbn, valid=False,
                        error="ISBN must contain only digits")

    if not (clean.startswith("978") or clean.startswith("979")):
        return ISBNInfo(isbn13=clean, formatted=isbn, valid=False,
                        error="ISBN-13 must start with 978 or 979")

    # Check digit validation
    check = _calculate_check_digit(clean[:12])
    if check != int(clean[12]):
        return ISBNInfo(isbn13=clean, formatted=isbn, valid=False,
                        error=f"Invalid check digit: expected {check}, got {clean[12]}")

    formatted = _format_isbn13(clean)
    return ISBNInfo(isbn13=clean, formatted=formatted, valid=True)


def _calculate_check_digit(first_12: str) -> int:
    """Calculate ISBN-13 check digit from first 12 digits."""
    total = 0
    for i, ch in enumerate(first_12):
        weight = 1 if i % 2 == 0 else 3
        total += int(ch) * weight
    remainder = total % 10
    return (10 - remainder) % 10


def _format_isbn13(isbn: str) -> str:
    """Format ISBN-13 with hyphens (simplified grouping)."""
    # Standard grouping: prefix-group-publisher-title-check
    # Using simple grouping: 978-X-XXXXXX-XX-X
    return f"{isbn[:3]}-{isbn[3]}-{isbn[4:10]}-{isbn[10:12]}-{isbn[12]}"


def generate_barcode(
    isbn: str,
    output_path: Path,
    format: str = "png",
) -> Path:
    """Generate an EAN-13 barcode image from an ISBN.

    Args:
        isbn: ISBN-13 string (with or without hyphens).
        output_path: Where to save the barcode image.
        format: Output format ('png' or 'svg').

    Returns:
        Path to the generated barcode image.
    """
    import barcode
    from barcode.writer import ImageWriter, SVGWriter

    info = validate_isbn13(isbn)
    if not info.valid:
        raise ValueError(f"Invalid ISBN: {info.error}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer = ImageWriter() if format == "png" else SVGWriter()

    ean = barcode.get("ean13", info.isbn13, writer=writer)

    # python-barcode appends the extension automatically
    stem = str(output_path.with_suffix(""))
    saved_path = ean.save(stem)

    log.info(f"Barcode generated: {saved_path}")
    return Path(saved_path)


def generate_barcode_for_variant(
    session,
    variant_id: int,
    output_dir: Path | None = None,
) -> Path | None:
    """Generate a barcode for a variant's ISBN if available.

    Looks up the publication record for the variant and generates
    a barcode from its ISBN. Returns None if no ISBN is set.
    """
    from libro.models.publication import Publication
    from libro.config import get_settings

    pub = (
        session.query(Publication)
        .filter(Publication.variant_id == variant_id)
        .first()
    )
    if not pub or not getattr(pub, "isbn", None):
        return None

    if output_dir is None:
        output_dir = get_settings().output_dir / f"variant_{variant_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    return generate_barcode(pub.isbn, output_dir / "barcode.png")
