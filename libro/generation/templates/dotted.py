"""Dotted grid template — popular for bullet journals."""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import InteriorTemplate, TrimSize


class DottedTemplate(InteriorTemplate):
    """Dot grid pages, popular for bullet journals and planners."""

    name = "dotted"
    description = "Dot grid pattern for bullet journaling"

    def __init__(
        self,
        dot_spacing: float = 18,  # points (~6.3mm, standard dot grid)
        dot_radius: float = 0.6,
        dot_color: tuple = (0.75, 0.75, 0.75),
        page_numbers: bool = True,
    ):
        super().__init__()
        self._default_dot_spacing = dot_spacing
        self._default_dot_radius = dot_radius
        self._default_dot_color = dot_color
        self.page_numbers = page_numbers

    @property
    def dot_spacing(self) -> float:
        return self.style.dot_spacing if self.style else self._default_dot_spacing

    @property
    def dot_radius(self) -> float:
        return self.style.dot_radius if self.style else self._default_dot_radius

    @property
    def dot_color(self) -> Color:
        c = self.style.dot_color if self.style else self._default_dot_color
        return Color(*c)

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        c.setFillColor(self.dot_color)

        # Draw dot grid
        y = trim.content_top
        while y >= trim.content_bottom:
            x = trim.content_left
            while x <= trim.content_right:
                c.circle(x, y, self.dot_radius, fill=1, stroke=0)
                x += self.dot_spacing
            y -= self.dot_spacing

        # Page number
        if self.page_numbers:
            self._draw_page_number(c, page_num, trim)
