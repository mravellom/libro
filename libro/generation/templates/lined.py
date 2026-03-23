"""Lined page template — classic ruled notebook."""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import InteriorTemplate, TrimSize


class LinedTemplate(InteriorTemplate):
    """Classic lined/ruled pages like a notebook."""

    name = "lined"
    description = "Ruled lines for writing, like a classic notebook"

    def __init__(
        self,
        line_spacing: float = 24,  # points (~8.5mm)
        line_color: tuple = (0.8, 0.8, 0.8),  # light gray
        line_width: float = 0.5,
        header_line: bool = True,
        page_numbers: bool = True,
    ):
        self.line_spacing = line_spacing
        self.line_color = Color(*line_color)
        self.line_width = line_width
        self.header_line = header_line
        self.page_numbers = page_numbers

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        c.setStrokeColor(self.line_color)
        c.setLineWidth(self.line_width)

        # Header line (thicker, for date/title)
        if self.header_line:
            header_y = trim.content_top - 20
            c.setStrokeColor(Color(0.6, 0.6, 0.6))
            c.setLineWidth(0.8)
            c.line(trim.content_left, header_y, trim.content_right, header_y)
            start_y = header_y - self.line_spacing * 1.5
            c.setStrokeColor(self.line_color)
            c.setLineWidth(self.line_width)
        else:
            start_y = trim.content_top

        # Draw ruled lines
        y = start_y
        while y >= trim.content_bottom:
            c.line(trim.content_left, y, trim.content_right, y)
            y -= self.line_spacing

        # Page number
        if self.page_numbers:
            c.setFont("Helvetica", 8)
            c.setFillColor(Color(0.6, 0.6, 0.6))
            c.drawCentredString(trim.width / 2, trim.content_bottom - 15, str(page_num))
