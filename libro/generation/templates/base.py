"""Abstract base class for interior page templates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from reportlab.lib.units import inch
from reportlab.lib.colors import Color
from reportlab.pdfgen.canvas import Canvas

from libro.common.pdf_utils import TRIM_SIZES, PPI

if TYPE_CHECKING:
    from libro.generation.interior_params import InteriorStyle


class TrimSize:
    """Trim size with dimensions in points."""

    def __init__(self, name: str, margin_inches: float = 0.5):
        if name not in TRIM_SIZES:
            raise ValueError(f"Unknown trim size: {name}. Options: {list(TRIM_SIZES)}")
        self.name = name
        w_in, h_in = TRIM_SIZES[name]
        self.width = w_in * PPI
        self.height = h_in * PPI
        self.width_in = w_in
        self.height_in = h_in
        self._margin = margin_inches * PPI

    # Usable area (with margins)
    @property
    def margin(self) -> float:
        return self._margin

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

    def __init__(self):
        self.style: InteriorStyle | None = None

    def set_style(self, style: InteriorStyle) -> None:
        """Set the interior style for unique generation."""
        self.style = style

    @abstractmethod
    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        """Draw a single page on the canvas."""
        ...

    def _draw_page_number(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        """Draw page number respecting style settings."""
        s = self.style
        font = s.page_number_font if s else "Helvetica"
        position = s.page_number_position if s else "centered"

        c.setFont(font, 8)
        c.setFillColor(Color(0.6, 0.6, 0.6))

        y = trim.content_bottom - 15
        text = str(page_num)

        if position == "outer_corner":
            x = trim.content_right if page_num % 2 == 0 else trim.content_left
            if page_num % 2 == 0:
                c.drawRightString(x, y, text)
            else:
                c.drawString(x, y, text)
        elif position == "inner_corner":
            x = trim.content_left if page_num % 2 == 0 else trim.content_right
            if page_num % 2 == 0:
                c.drawString(x, y, text)
            else:
                c.drawRightString(x, y, text)
        else:  # centered
            c.drawCentredString(trim.width / 2, y, text)

    def _draw_header_decoration(self, c: Canvas, trim: TrimSize) -> None:
        """Draw header decoration based on style."""
        s = self.style
        if not s or s.header_decoration == "none":
            return

        y = trim.content_top + 5
        color = Color(*s.line_color)

        if s.header_decoration == "thin_rule":
            c.setStrokeColor(color)
            c.setLineWidth(0.3)
            c.line(trim.content_left, y, trim.content_right, y)
        elif s.header_decoration == "dots":
            c.setFillColor(color)
            x = trim.content_left
            while x <= trim.content_right:
                c.circle(x, y, 0.4, fill=1, stroke=0)
                x += 8
        elif s.header_decoration == "corner_marks":
            c.setStrokeColor(color)
            c.setLineWidth(0.4)
            mark = 8
            # Top-left
            c.line(trim.content_left, y, trim.content_left + mark, y)
            c.line(trim.content_left, y, trim.content_left, y - mark)
            # Top-right
            c.line(trim.content_right, y, trim.content_right - mark, y)
            c.line(trim.content_right, y, trim.content_right, y - mark)

    def _draw_footer_decoration(self, c: Canvas, trim: TrimSize) -> None:
        """Draw footer decoration based on style."""
        s = self.style
        if not s or s.footer_decoration == "none":
            return

        y = trim.content_bottom - 5
        color = Color(*s.line_color)

        if s.footer_decoration == "thin_rule":
            c.setStrokeColor(color)
            c.setLineWidth(0.3)
            c.line(trim.content_left, y, trim.content_right, y)
        elif s.footer_decoration == "dots":
            c.setFillColor(color)
            x = trim.content_left
            while x <= trim.content_right:
                c.circle(x, y, 0.4, fill=1, stroke=0)
                x += 8

    def _draw_section_divider(self, c: Canvas, trim: TrimSize) -> None:
        """Draw a decorative section divider page."""
        s = self.style
        color = Color(*(s.line_color if s else (0.8, 0.8, 0.8)))

        mid_y = trim.height / 2
        mid_x = trim.width / 2

        # Decorative line with diamond
        c.setStrokeColor(color)
        c.setLineWidth(0.5)
        c.line(mid_x - 60, mid_y, mid_x - 8, mid_y)
        c.line(mid_x + 8, mid_y, mid_x + 60, mid_y)

        # Diamond shape
        c.setFillColor(color)
        path = c.beginPath()
        path.moveTo(mid_x, mid_y + 5)
        path.lineTo(mid_x + 5, mid_y)
        path.lineTo(mid_x, mid_y - 5)
        path.lineTo(mid_x - 5, mid_y)
        path.close()
        c.drawPath(path, fill=1, stroke=0)

    def _draw_quote_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        """Draw an interstitial quote page."""
        s = self.style
        if not s or not s.quotes:
            return

        quote_idx = (page_num // max(s.quote_page_interval, 1)) % len(s.quotes)
        quote = s.quotes[quote_idx]

        color = Color(*(s.prompt_color if s else (0.4, 0.4, 0.4)))
        mid_y = trim.height / 2

        c.setFont("Times-Italic", 12)
        c.setFillColor(color)

        # Word-wrap the quote
        words = quote.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if c.stringWidth(test, "Times-Italic", 12) < trim.content_width * 0.7:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        # Center vertically
        total_height = len(lines) * 18
        y = mid_y + total_height / 2

        for line in lines:
            c.drawCentredString(trim.width / 2, y, line)
            y -= 18

        # Decorative dash below
        c.setStrokeColor(color)
        c.setLineWidth(0.5)
        c.line(trim.width / 2 - 20, y - 10, trim.width / 2 + 20, y - 10)

    def _is_special_page(self, page_num: int) -> str | None:
        """Check if this page should be a special interstitial page.

        Returns: 'quote', 'divider', or None for regular page.
        """
        s = self.style
        if not s:
            return None

        if s.has_section_dividers and page_num > 1:
            if page_num % s.section_divider_interval == 0:
                return "divider"

        if s.has_quote_pages and page_num > 1:
            if (page_num % s.quote_page_interval == 0
                    and page_num % s.section_divider_interval != 0):
                return "quote"

        return None

    def generate_pdf(
        self,
        output_path: Path,
        trim_size: str = "6x9",
        page_count: int = 120,
        seed: int | None = None,
    ) -> Path:
        """Generate a complete interior PDF.

        Args:
            output_path: Where to save the PDF.
            trim_size: KDP trim size string (e.g., "6x9").
            page_count: Total number of pages.
            seed: Variant ID for unique style generation.

        Returns:
            Path to the generated PDF.
        """
        if seed is not None:
            from libro.generation.interior_params import generate_interior_style
            self.style = generate_interior_style(seed, self.name)

        margin = self.style.margin_inches if self.style else 0.5
        trim = TrimSize(trim_size, margin_inches=margin)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        c = Canvas(str(output_path), pagesize=(trim.width, trim.height))

        # Draw intro pages (title page + how-to-use)
        from libro.generation.templates.intro_pages import draw_intro_pages
        intro_count = draw_intro_pages(c, trim, self.name)

        # Remaining pages for content (subtract intro pages)
        content_pages = max(1, page_count - intro_count)

        for page_num in range(1, content_pages + 1):
            special = self._is_special_page(page_num)
            if special == "divider":
                self._draw_section_divider(c, trim)
                self._draw_page_number(c, page_num, trim)
            elif special == "quote":
                self._draw_quote_page(c, page_num, trim)
                self._draw_page_number(c, page_num, trim)
            else:
                self._draw_header_decoration(c, trim)
                self.draw_page(c, page_num, trim)
                self._draw_footer_decoration(c, trim)
            c.showPage()

        c.save()
        return output_path
