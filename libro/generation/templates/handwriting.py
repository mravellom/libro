"""Handwriting practice template — 3-line penmanship rule with dotted midline."""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import InteriorTemplate, TrimSize


class HandwritingTemplate(InteriorTemplate):
    """Penmanship practice paper: groups of top line, dotted midline, baseline.

    This is the standard rule used by handwriting workbooks (kids and adults):
    a solid top line, a dotted guide line at half height, and a heavier
    baseline, with a gap between groups.
    """

    name = "handwriting"
    description = "Handwriting practice paper with dotted midline guide rule"

    def __init__(
        self,
        rule_height: float = 34.0,  # points from baseline to top line (~12mm)
        group_gap: float = 18.0,  # points between practice groups
        line_color: tuple = (0.75, 0.75, 0.75),
        midline_dash: tuple = (3, 3),
        baseline_width: float = 0.9,
        page_numbers: bool = True,
    ):
        super().__init__()
        self._default_rule_height = rule_height
        self._default_group_gap = group_gap
        self._default_line_color = line_color
        self._default_midline_dash = midline_dash
        self._default_baseline_width = baseline_width
        self.page_numbers = page_numbers

    @property
    def rule_height(self) -> float:
        if self.style:
            return self.style.hw_rule_height
        return self._default_rule_height

    @property
    def group_gap(self) -> float:
        if self.style:
            return self.style.hw_group_gap
        return self._default_group_gap

    @property
    def line_color(self) -> Color:
        c = self.style.line_color if self.style else self._default_line_color
        return Color(*c)

    @property
    def midline_dash(self) -> tuple:
        if self.style:
            return self.style.hw_midline_dash
        return self._default_midline_dash

    @property
    def baseline_width(self) -> float:
        if self.style:
            return self.style.hw_baseline_width
        return self._default_baseline_width

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        left = trim.content_left
        right = trim.content_right

        # Each group needs rule_height plus the gap to the next group
        group_height = self.rule_height + self.group_gap

        top = trim.content_top
        while top - self.rule_height >= trim.content_bottom:
            baseline = top - self.rule_height
            midline = top - self.rule_height / 2

            # Top line (light)
            c.setStrokeColor(self.line_color)
            c.setLineWidth(0.5)
            c.line(left, top, right, top)

            # Dotted midline (guide for lowercase letter height)
            c.setDash(*self.midline_dash)
            c.line(left, midline, right, midline)
            c.setDash()

            # Baseline (heavier — where letters sit)
            c.setLineWidth(self.baseline_width)
            c.line(left, baseline, right, baseline)

            top -= group_height

        # Page number
        if self.page_numbers:
            self._draw_page_number(c, page_num, trim)
