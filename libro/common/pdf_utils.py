"""KDP-specific PDF dimensions, bleed calculations, and trim sizes."""

from dataclasses import dataclass

# Points per inch (PDF standard)
PPI = 72

# Common KDP trim sizes (width x height in inches)
TRIM_SIZES: dict[str, tuple[float, float]] = {
    "5x8": (5.0, 8.0),
    "5.5x8.5": (5.5, 8.5),
    "6x9": (6.0, 9.0),
    "7x10": (7.0, 10.0),
    "8.5x11": (8.5, 11.0),
}


@dataclass
class CoverDimensions:
    """Full cover dimensions in inches (front + spine + back + bleed)."""
    width: float
    height: float
    spine_width: float
    bleed: float = 0.125

    @property
    def total_width(self) -> float:
        return self.width * 2 + self.spine_width + self.bleed * 2

    @property
    def total_height(self) -> float:
        return self.height + self.bleed * 2

    @property
    def total_width_pts(self) -> float:
        return self.total_width * PPI

    @property
    def total_height_pts(self) -> float:
        return self.total_height * PPI


def calculate_spine_width(page_count: int, paper_type: str = "white") -> float:
    """Calculate spine width in inches based on page count and paper type.

    KDP formula:
    - White paper: page_count * 0.002252"
    - Cream paper: page_count * 0.002500"
    """
    multiplier = 0.002252 if paper_type == "white" else 0.002500
    return page_count * multiplier


def get_cover_dimensions(
    trim_size: str, page_count: int, paper_type: str = "white"
) -> CoverDimensions:
    if trim_size not in TRIM_SIZES:
        raise ValueError(f"Unknown trim size: {trim_size}. Options: {list(TRIM_SIZES)}")
    width, height = TRIM_SIZES[trim_size]
    spine = calculate_spine_width(page_count, paper_type)
    return CoverDimensions(width=width, height=height, spine_width=spine)


def trim_size_pts(trim_size: str) -> tuple[float, float]:
    """Get trim size in points for ReportLab canvas."""
    if trim_size not in TRIM_SIZES:
        raise ValueError(f"Unknown trim size: {trim_size}")
    w, h = TRIM_SIZES[trim_size]
    return w * PPI, h * PPI
