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
        super().__init__()
        self._default_cell_size = cell_size
        self._default_line_color = line_color
        self._default_line_width = line_width
        self.page_numbers = page_numbers

    @property
    def cell_size(self) -> float:
        return self.style.cell_size if self.style else self._default_cell_size

    @property
    def line_color(self) -> Color:
        c = self.style.line_color if self.style else self._default_line_color
        return Color(*c)

    @property
    def line_width(self) -> float:
        return self.style.line_width if self.style else self._default_line_width

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
            self._draw_page_number(c, page_num, trim)
