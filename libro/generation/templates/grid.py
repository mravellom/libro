"""Grid/graph paper template."""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import InteriorTemplate, TrimSize


class GridTemplate(InteriorTemplate):
    """Square grid pages, like graph paper."""

    name = "grid"
    description = "Square grid pattern like graph paper"

    def __init__(
        self,
        cell_size: float = 18,  # points (~6.3mm)
        line_color: tuple = (0.82, 0.82, 0.82),
        line_width: float = 0.3,
        page_numbers: bool = True,
    ):
        self.cell_size = cell_size
        self.line_color = Color(*line_color)
        self.line_width = line_width
        self.page_numbers = page_numbers

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        c.setStrokeColor(self.line_color)
        c.setLineWidth(self.line_width)

        # Horizontal lines
        y = trim.content_top
        while y >= trim.content_bottom:
            c.line(trim.content_left, y, trim.content_right, y)
            y -= self.cell_size

        # Vertical lines
        x = trim.content_left
        while x <= trim.content_right:
            c.line(x, trim.content_bottom, x, trim.content_top)
            x += self.cell_size

        # Page number
        if self.page_numbers:
            c.setFont("Helvetica", 8)
            c.setFillColor(Color(0.6, 0.6, 0.6))
            c.drawCentredString(trim.width / 2, trim.content_bottom - 15, str(page_num))
