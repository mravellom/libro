"""PDF validation for KDP uploads.

Validates structure, page count, dimensions, and file size
before uploading to KDP — catches problems early.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from libro.common.pdf_utils import (
    PPI,
    TRIM_SIZES,
    get_cover_dimensions,
)

log = logging.getLogger(__name__)

# KDP limits
MAX_INTERIOR_SIZE_MB = 650
MAX_COVER_SIZE_MB = 40
# Tolerance for dimension checks (in points)
DIMENSION_TOLERANCE_PTS = 2.0


@dataclass
class PDFValidationResult:
    """Result of validating a single PDF."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    page_count: int | None = None
    width_pts: float | None = None
    height_pts: float | None = None

    @property
    def summary(self) -> str:
        if self.valid:
            return f"OK ({self.page_count} pages, {self.width_pts:.0f}x{self.height_pts:.0f} pts)"
        return "; ".join(self.errors)


def validate_pdf_structure(path: Path) -> PDFValidationResult:
    """Check that a file is a readable PDF and extract basic info."""
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        return PDFValidationResult(False, [f"File not found: {path}"], [], None)

    # Check magic bytes
    with open(path, "rb") as f:
        header = f.read(5)
    if header != b"%PDF-":
        return PDFValidationResult(False, [f"Not a valid PDF (bad header): {path.name}"], [], None)

    try:
        reader = PdfReader(path)
        page_count = len(reader.pages)
    except Exception as e:
        return PDFValidationResult(False, [f"Cannot read PDF: {e}"], [], None)

    if page_count == 0:
        errors.append("PDF has 0 pages")

    # Get dimensions from first page
    width_pts = None
    height_pts = None
    if page_count > 0:
        box = reader.pages[0].mediabox
        width_pts = float(box.width)
        height_pts = float(box.height)

    return PDFValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        page_count=page_count,
        width_pts=width_pts,
        height_pts=height_pts,
    )


def validate_interior(
    path: Path,
    expected_trim_size: str,
    expected_page_count: int,
) -> PDFValidationResult:
    """Validate an interior PDF against KDP requirements."""
    result = validate_pdf_structure(path)
    if not result.valid:
        return result

    errors = list(result.errors)
    warnings = list(result.warnings)

    # File size
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_INTERIOR_SIZE_MB:
        errors.append(f"Interior too large: {size_mb:.1f} MB (max {MAX_INTERIOR_SIZE_MB} MB)")

    # Page count: KDP limits
    if result.page_count is not None:
        if result.page_count < 24:
            errors.append(f"Too few pages: {result.page_count} (min 24)")
        elif result.page_count > 828:
            errors.append(f"Too many pages: {result.page_count} (max 828)")

        # Compare with expected
        if result.page_count != expected_page_count:
            warnings.append(
                f"Page count mismatch: PDF has {result.page_count}, expected {expected_page_count}"
            )

    # Page dimensions vs trim size
    if expected_trim_size in TRIM_SIZES and result.width_pts and result.height_pts:
        exp_w, exp_h = TRIM_SIZES[expected_trim_size]
        exp_w_pts = exp_w * PPI
        exp_h_pts = exp_h * PPI

        if abs(result.width_pts - exp_w_pts) > DIMENSION_TOLERANCE_PTS:
            errors.append(
                f"Width mismatch: {result.width_pts:.1f} pts, "
                f"expected {exp_w_pts:.1f} pts for {expected_trim_size}"
            )
        if abs(result.height_pts - exp_h_pts) > DIMENSION_TOLERANCE_PTS:
            errors.append(
                f"Height mismatch: {result.height_pts:.1f} pts, "
                f"expected {exp_h_pts:.1f} pts for {expected_trim_size}"
            )

    return PDFValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        page_count=result.page_count,
        width_pts=result.width_pts,
        height_pts=result.height_pts,
    )


def validate_cover(
    path: Path,
    trim_size: str,
    page_count: int,
) -> PDFValidationResult:
    """Validate a cover PDF against KDP cover dimension requirements.

    Cover is generated as an image saved to PDF via Pillow, so the PDF
    has exactly 1 page. Dimensions are in pixels at 300 DPI, but the PDF
    mediabox reports points (pixels * 72/300).
    """
    result = validate_pdf_structure(path)
    if not result.valid:
        return result

    errors = list(result.errors)
    warnings = list(result.warnings)

    # File size
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_COVER_SIZE_MB:
        errors.append(f"Cover too large: {size_mb:.1f} MB (max {MAX_COVER_SIZE_MB} MB)")

    # Cover should be a single page
    if result.page_count != 1:
        warnings.append(f"Cover has {result.page_count} pages (expected 1)")

    # Dimension check: cover dimensions include spine + bleed
    if trim_size in TRIM_SIZES and result.width_pts and result.height_pts:
        dims = get_cover_dimensions(trim_size, page_count)
        # Pillow saves images as PDF at the specified DPI.
        # The mediabox in points = pixels * 72 / DPI.
        # Our covers are 300 DPI, so expected_pts = inches * 72
        exp_w_pts = dims.total_width * PPI
        exp_h_pts = dims.total_height * PPI

        # Use a wider tolerance for covers (rounding from pixel math)
        cover_tolerance = 3.0
        if abs(result.width_pts - exp_w_pts) > cover_tolerance:
            errors.append(
                f"Cover width: {result.width_pts:.1f} pts, "
                f"expected ~{exp_w_pts:.1f} pts"
            )
        if abs(result.height_pts - exp_h_pts) > cover_tolerance:
            errors.append(
                f"Cover height: {result.height_pts:.1f} pts, "
                f"expected ~{exp_h_pts:.1f} pts"
            )

    return PDFValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        page_count=result.page_count,
        width_pts=result.width_pts,
        height_pts=result.height_pts,
    )
