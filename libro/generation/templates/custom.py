"""Custom templates — specialized page layouts for specific niches."""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import InteriorTemplate, TrimSize


class GratitudeTemplate(InteriorTemplate):
    """Gratitude journal page — structured prompts."""

    name = "gratitude"
    description = "Structured gratitude journal with daily prompts"

    def __init__(self, page_numbers: bool = True):
        self.page_numbers = page_numbers
        self.line_color = Color(0.8, 0.8, 0.8)
        self.prompt_color = Color(0.4, 0.4, 0.4)

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        # Date line
        c.setFont("Helvetica", 9)
        c.setFillColor(self.prompt_color)
        c.drawString(trim.content_left, y, "Date: _______________")
        y -= 30

        # Prompt sections
        prompts = [
            "Today I am grateful for:",
            "What made today special:",
            "One positive thing that happened:",
            "How I can make tomorrow better:",
        ]

        lines_per_prompt = 4
        line_spacing = 22

        for prompt in prompts:
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
            for _ in range(lines_per_prompt):
                c.line(trim.content_left, y, trim.content_right, y)
                y -= line_spacing

            y -= 10  # spacing between sections

        # Page number
        if self.page_numbers:
            c.setFont("Helvetica", 8)
            c.setFillColor(Color(0.6, 0.6, 0.6))
            c.drawCentredString(trim.width / 2, trim.content_bottom - 15, str(page_num))


class DailyPlannerTemplate(InteriorTemplate):
    """Daily planner page — schedule + tasks + notes."""

    name = "planner"
    description = "Daily planner with schedule, tasks, and notes"

    def __init__(self, page_numbers: bool = True):
        self.page_numbers = page_numbers
        self.line_color = Color(0.8, 0.8, 0.8)
        self.label_color = Color(0.4, 0.4, 0.4)

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

        # Schedule section (left column)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "SCHEDULE")
        y -= 18

        c.setFont("Helvetica", 8)
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)

        for hour in range(6, 21):  # 6 AM to 8 PM
            label = f"{hour:2d}:00"
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left, y, label)
            c.line(trim.content_left + 35, y, mid_x - 15, y)
            y -= 16
            if y < trim.content_bottom + 100:
                break

        # Tasks section
        y -= 10
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "TOP PRIORITIES")
        y -= 18

        c.setStrokeColor(self.line_color)
        for i in range(5):
            # Checkbox
            c.rect(trim.content_left, y - 3, 10, 10, fill=0)
            c.line(trim.content_left + 18, y, trim.content_right, y)
            y -= 22

        # Notes section (bottom)
        y -= 10
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "NOTES")
        y -= 18

        while y > trim.content_bottom + 20:
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 20

        # Page number
        if self.page_numbers:
            c.setFont("Helvetica", 8)
            c.setFillColor(Color(0.6, 0.6, 0.6))
            c.drawCentredString(trim.width / 2, trim.content_bottom - 15, str(page_num))


# Registry of all available templates
TEMPLATE_REGISTRY: dict[str, type[InteriorTemplate]] = {}


def register_templates():
    """Register all built-in templates."""
    from libro.generation.templates.lined import LinedTemplate
    from libro.generation.templates.dotted import DottedTemplate
    from libro.generation.templates.grid import GridTemplate

    TEMPLATE_REGISTRY["lined"] = LinedTemplate
    TEMPLATE_REGISTRY["dotted"] = DottedTemplate
    TEMPLATE_REGISTRY["grid"] = GridTemplate
    TEMPLATE_REGISTRY["gratitude"] = GratitudeTemplate
    TEMPLATE_REGISTRY["planner"] = DailyPlannerTemplate


def get_template(name: str) -> InteriorTemplate:
    """Get a template instance by name."""
    if not TEMPLATE_REGISTRY:
        register_templates()
    if name not in TEMPLATE_REGISTRY:
        raise ValueError(f"Unknown template: {name}. Options: {list(TEMPLATE_REGISTRY)}")
    return TEMPLATE_REGISTRY[name]()
