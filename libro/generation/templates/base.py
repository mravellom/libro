"""Abstract base class for interior page templates."""

from abc import ABC, abstractmethod
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from libro.common.pdf_utils import TRIM_SIZES, PPI


class TrimSize:
    """Trim size with dimensions in points."""

    def __init__(self, name: str):
        if name not in TRIM_SIZES:
            raise ValueError(f"Unknown trim size: {name}. Options: {list(TRIM_SIZES)}")
        self.name = name
        w_in, h_in = TRIM_SIZES[name]
        self.width = w_in * PPI
        self.height = h_in * PPI
        self.width_in = w_in
        self.height_in = h_in

    # Usable area (with margins)
    @property
    def margin(self) -> float:
        """Default margin in points (0.5 inch)."""
        return 0.5 * PPI

    @property
    def content_width(self) -> float:
        return self.width - 2 * self.margin

    @property
    def content_height(self) -> float:
        return self.height - 2 * self.margin

    @property
    def content_left(self) -> float:
        return self.margin

    @property
    def content_right(self) -> float:
        return self.width - self.margin

    @property
    def content_top(self) -> float:
        return self.height - self.margin

    @property
    def content_bottom(self) -> float:
        return self.margin


class InteriorTemplate(ABC):
    """Abstract base for interior page templates.

    Each template knows how to draw one page. The generate_pdf method
    handles creating the full document by repeating draw_page.
    """

    name: str = "base"
    description: str = ""
    supported_trim_sizes: list[str] = list(TRIM_SIZES.keys())

    @abstractmethod
    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        """Draw a single page on the canvas.

        Args:
            c: ReportLab canvas (already set to correct page size).
            page_num: 1-based page number.
            trim: Trim size with dimensions.
        """
        ...

    def generate_pdf(
        self,
        output_path: Path,
        trim_size: str = "6x9",
        page_count: int = 120,
    ) -> Path:
        """Generate a complete interior PDF.

        Args:
            output_path: Where to save the PDF.
            trim_size: KDP trim size string (e.g., "6x9").
            page_count: Total number of pages.

        Returns:
            Path to the generated PDF.
        """
        trim = TrimSize(trim_size)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        c = Canvas(str(output_path), pagesize=(trim.width, trim.height))

        for page_num in range(1, page_count + 1):
            self.draw_page(c, page_num, trim)
            c.showPage()

        c.save()
        return output_path
