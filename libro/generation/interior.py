"""Interior PDF generation — creates complete book interiors."""

import logging
from pathlib import Path

from libro.common.pdf_utils import TRIM_SIZES
from libro.generation.templates.custom import get_template

log = logging.getLogger(__name__)


def generate_interior(
    template_name: str,
    output_path: Path,
    trim_size: str = "6x9",
    page_count: int = 120,
) -> Path:
    """Generate an interior PDF using a named template.

    Args:
        template_name: Template to use (lined, dotted, grid, gratitude, planner).
        output_path: Where to save the PDF.
        trim_size: KDP trim size (e.g., "6x9", "5.5x8.5").
        page_count: Number of pages.

    Returns:
        Path to the generated PDF.
    """
    template = get_template(template_name)
    log.info(
        f"Generating {template_name} interior: {trim_size}, "
        f"{page_count} pages → {output_path}"
    )
    return template.generate_pdf(output_path, trim_size, page_count)


def list_templates() -> list[dict[str, str]]:
    """List all available templates with their descriptions."""
    from libro.generation.templates.custom import TEMPLATE_REGISTRY, register_templates

    if not TEMPLATE_REGISTRY:
        register_templates()

    return [
        {"name": name, "description": cls().description}
        for name, cls in TEMPLATE_REGISTRY.items()
    ]
