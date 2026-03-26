"""Custom templates — specialized page layouts for specific niches."""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import InteriorTemplate, TrimSize


class GratitudeTemplate(InteriorTemplate):
    """Gratitude journal page — structured prompts."""

    name = "gratitude"
    description = "Structured gratitude journal with daily prompts"

    def __init__(self, page_numbers: bool = True):
        super().__init__()
        self.page_numbers = page_numbers

    @property
    def line_color(self) -> Color:
        return Color(*(self.style.line_color if self.style else (0.8, 0.8, 0.8)))

    @property
    def prompt_color(self) -> Color:
        return Color(*(self.style.prompt_color if self.style else (0.4, 0.4, 0.4)))

    @property
    def prompts(self) -> list[str]:
        if self.style:
            from libro.generation.interior_params import GRATITUDE_PROMPT_SETS
            idx = self.style.prompt_set_index % len(GRATITUDE_PROMPT_SETS)
            return GRATITUDE_PROMPT_SETS[idx]
        return [
            "Today I am grateful for:",
            "What made today special:",
            "One positive thing that happened:",
            "How I can make tomorrow better:",
        ]

    @property
    def lines_per_prompt(self) -> int:
        return self.style.lines_per_prompt if self.style else 4

    @property
    def line_spacing(self) -> float:
        return self.style.prompt_line_spacing if self.style else 22.0

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        # Date line
        c.setFont("Helvetica", 9)
        c.setFillColor(self.prompt_color)
        c.drawString(trim.content_left, y, "Date: _______________")
        y -= 30

        for prompt in self.prompts:
            if y < trim.content_bottom + 40:
                break

            # Prompt text
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(self.prompt_color)
            c.drawString(trim.content_left, y, prompt)
            y -= 20

            # Writing lines
            c.setStrokeColor(self.line_color)
            c.setLineWidth(0.5)
            for _ in range(self.lines_per_prompt):
                c.line(trim.content_left, y, trim.content_right, y)
                y -= self.line_spacing

            y -= 10  # spacing between sections

        # Page number
        if self.page_numbers:
            self._draw_page_number(c, page_num, trim)


class DailyPlannerTemplate(InteriorTemplate):
    """Daily planner page — schedule + tasks + notes."""

    name = "planner"
    description = "Daily planner with schedule, tasks, and notes"

    def __init__(self, page_numbers: bool = True):
        super().__init__()
        self.page_numbers = page_numbers

    @property
    def line_color(self) -> Color:
        return Color(*(self.style.line_color if self.style else (0.8, 0.8, 0.8)))

    @property
    def label_color(self) -> Color:
        return Color(*(self.style.prompt_color if self.style else (0.4, 0.4, 0.4)))

    @property
    def hour_start(self) -> int:
        return self.style.planner_hour_start if self.style else 6

    @property
    def hour_end(self) -> int:
        return self.style.planner_hour_end if self.style else 21

    @property
    def priority_count(self) -> int:
        return self.style.planner_priority_count if self.style else 5

    @property
    def sections_order(self) -> list[str]:
        if self.style:
            return self.style.planner_sections_order
        return ["schedule", "priorities", "notes"]

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top
        mid_x = trim.content_left + trim.content_width * 0.55

        # Date header
        c.setFont("Helvetica", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "Date: _______________")
        c.drawString(mid_x, y, "Day: ________")
        y -= 25

        # Divider
        c.setStrokeColor(Color(0.5, 0.5, 0.5))
        c.setLineWidth(0.8)
        c.line(trim.content_left, y, trim.content_right, y)
        y -= 20

        for section in self.sections_order:
            if y < trim.content_bottom + 30:
                break
            if section == "schedule":
                y = self._draw_schedule(c, y, trim, mid_x)
            elif section == "priorities":
                y = self._draw_priorities(c, y, trim)
            elif section == "notes":
                y = self._draw_notes(c, y, trim)

        # Page number
        if self.page_numbers:
            self._draw_page_number(c, page_num, trim)

    def _draw_schedule(self, c: Canvas, y: float, trim: TrimSize, mid_x: float) -> float:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "SCHEDULE")
        y -= 18

        c.setFont("Helvetica", 8)
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)

        for hour in range(self.hour_start, self.hour_end):
            label = f"{hour:2d}:00"
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left, y, label)
            c.line(trim.content_left + 35, y, mid_x - 15, y)
            y -= 16
            if y < trim.content_bottom + 100:
                break

        y -= 10
        return y

    def _draw_priorities(self, c: Canvas, y: float, trim: TrimSize) -> float:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "TOP PRIORITIES")
        y -= 18

        c.setStrokeColor(self.line_color)
        for _ in range(self.priority_count):
            if y < trim.content_bottom + 40:
                break
            c.rect(trim.content_left, y - 3, 10, 10, fill=0)
            c.line(trim.content_left + 18, y, trim.content_right, y)
            y -= 22

        y -= 10
        return y

    def _draw_notes(self, c: Canvas, y: float, trim: TrimSize) -> float:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "NOTES")
        y -= 18

        c.setStrokeColor(self.line_color)
        while y > trim.content_bottom + 20:
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 20

        return y


# Registry of all available templates
TEMPLATE_REGISTRY: dict[str, type[InteriorTemplate]] = {}


def register_templates():
    """Register all built-in templates."""
    from libro.generation.templates.lined import LinedTemplate
    from libro.generation.templates.dotted import DottedTemplate
    from libro.generation.templates.grid import GridTemplate
    from libro.generation.templates.thematic import (
        AnxietyJournalTemplate,
        FitnessLogTemplate,
        BudgetTrackerTemplate,
        ReadingLogTemplate,
        MealPlannerTemplate,
    )

    TEMPLATE_REGISTRY["lined"] = LinedTemplate
    TEMPLATE_REGISTRY["dotted"] = DottedTemplate
    TEMPLATE_REGISTRY["grid"] = GridTemplate
    TEMPLATE_REGISTRY["gratitude"] = GratitudeTemplate
    TEMPLATE_REGISTRY["planner"] = DailyPlannerTemplate
    # Thematic templates with niche-specific content
    TEMPLATE_REGISTRY["anxiety"] = AnxietyJournalTemplate
    TEMPLATE_REGISTRY["fitness"] = FitnessLogTemplate
    TEMPLATE_REGISTRY["budget"] = BudgetTrackerTemplate
    TEMPLATE_REGISTRY["reading"] = ReadingLogTemplate
    TEMPLATE_REGISTRY["meal"] = MealPlannerTemplate


def get_template(name: str, seed: int | None = None) -> InteriorTemplate:
    """Get a template instance by name, optionally with a unique style seed."""
    if not TEMPLATE_REGISTRY:
        register_templates()
    if name not in TEMPLATE_REGISTRY:
        raise ValueError(f"Unknown template: {name}. Options: {list(TEMPLATE_REGISTRY)}")

    template = TEMPLATE_REGISTRY[name]()

    if seed is not None:
        from libro.generation.interior_params import generate_interior_style
        style = generate_interior_style(seed, name)
        template.set_style(style)

    return template
