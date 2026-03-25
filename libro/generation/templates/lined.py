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
        super().__init__()
        self._default_line_spacing = line_spacing
        self._default_line_color = line_color
        self._default_line_width = line_width
        self.header_line = header_line
        self.page_numbers = page_numbers

    @property
    def line_spacing(self) -> float:
        return self.style.line_spacing if self.style else self._default_line_spacing

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

        # Header line (thicker, for date/title)
        header_style = self.style.header_style if self.style else "line"
        if self.header_line and header_style != "none":
            header_y = trim.content_top - 20
            header_color = Color(0.6, 0.6, 0.6)
            c.setStrokeColor(header_color)
            c.setLineWidth(0.8)

            if header_style == "box":
                c.rect(trim.content_left, header_y - 2, trim.content_width, 14, fill=0)
            elif header_style == "dotted_line":
                c.setDash(3, 3)
                c.line(trim.content_left, header_y, trim.content_right, header_y)
                c.setDash()
            else:  # "line"
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
            self._draw_page_number(c, page_num, trim)
