"""KDP metadata generation — title, description, keywords, categories.

Generates market-optimized metadata with formatted descriptions,
competitor-informed pricing, and rich keyword strategies.
"""

import logging
import textwrap
from dataclasses import dataclass

from libro.models.variant import Variant

log = logging.getLogger(__name__)

# Common KDP categories for low-content books
KDP_CATEGORIES = {
    "journal": [
        "Self-Help > Journal Writing",
        "Self-Help > Personal Transformation",
    ],
    "gratitude": [
        "Self-Help > Journal Writing",
        "Self-Help > Motivational",
    ],
    "planner": [
        "Self-Help > Time Management",
        "Business & Money > Skills > Time Management",
    ],
    "notebook": [
        "Self-Help > Journal Writing",
        "Education & Teaching > Studying & Workbooks",
    ],
    "fitness": [
        "Health, Fitness & Dieting > Exercise & Fitness > Journals",
        "Self-Help > Journal Writing",
    ],
    "finance": [
        "Business & Money > Personal Finance > Budgeting & Money Management",
        "Self-Help > Journal Writing",
    ],
    "education": [
        "Education & Teaching > Studying & Workbooks",
        "Children's Books > Activities, Crafts & Games",
    ],
    "default": [
        "Self-Help > Journal Writing",
        "Self-Help > Personal Transformation",
    ],
}


@dataclass
class KDPMetadata:
    """Complete metadata ready for KDP upload."""
    title: str
    subtitle: str
    author: str
    description: str
    keywords: list[str]  # max 7
    categories: list[str]  # 2 BISAC categories
    language: str
    trim_size: str
    page_count: int
    price_suggestion: str

    def to_text(self) -> str:
        """Format as readable text for manual upload reference."""
        lines = [
            "=" * 60,
            "KDP METADATA",
            "=" * 60,
            f"Title: {self.title}",
            f"Subtitle: {self.subtitle}",
            f"Author: {self.author}",
            "",
            "Description:",
            self.description,
            "",
            "Keywords (copy each separately):",
        ]
        for i, kw in enumerate(self.keywords, 1):
            lines.append(f"  {i}. {kw}")

        lines.extend([
            "",
            "Categories:",
            f"  1. {self.categories[0]}",
            f"  2. {self.categories[1]}" if len(self.categories) > 1 else "",
            "",
            f"Language: {self.language}",
            f"Trim Size: {self.trim_size}",
            f"Page Count: {self.page_count}",
            f"Suggested Price: {self.price_suggestion}",
            "=" * 60,
        ])
        return "\n".join(lines)


def generate_metadata(
    variant: Variant,
    author: str = "",
    language: str = "English",
    competitor_avg_price: float | None = None,
) -> KDPMetadata:
    """Generate KDP-ready metadata from a variant.

    Args:
        variant: The book variant to generate metadata for.
        author: Author/brand name.
        language: Book language.
        competitor_avg_price: Average competitor price for dynamic pricing.

    Returns:
        KDPMetadata ready for upload.
    """
    # Keywords (max 7, from variant or generated)
    if variant.keywords:
        keywords = [kw.strip() for kw in variant.keywords.split(",")][:7]
    else:
        keywords = _generate_keywords(variant.title)

    # Categories based on interior type and title
    categories = _detect_categories(variant.title, variant.interior_type)

    # Description (use variant's or generate)
    description = variant.description or _generate_description(variant)

    # Price suggestion — use competitor data if available
    price = _suggest_price(variant.page_count, competitor_avg_price)

    return KDPMetadata(
        title=variant.title,
        subtitle=variant.subtitle or "",
        author=author,
        description=description,
        keywords=keywords,
        categories=categories,
        language=language,
        trim_size=variant.trim_size,
        page_count=variant.page_count,
        price_suggestion=price,
    )


def _generate_keywords(title: str) -> list[str]:
    """Generate keywords from title words."""
    words = title.lower().split()
    stop = {"a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with"}
    meaningful = [w for w in words if w not in stop and len(w) > 2]
    keywords = []

    # Add bigrams first
    for i in range(len(meaningful) - 1):
        kw = f"{meaningful[i]} {meaningful[i+1]}"
        if kw not in keywords:
            keywords.append(kw)
        if len(keywords) >= 4:
            break

    # Fill with singles
    for w in meaningful:
        if w not in keywords and len(keywords) < 7:
            keywords.append(w)

    return keywords[:7]


def _detect_categories(title: str, interior_type: str) -> list[str]:
    """Detect appropriate KDP categories."""
    title_lower = title.lower()

    # Check extended categories first (more specific)
    specific_hints = {
        "fitness": ["fitness", "workout", "exercise", "gym", "yoga", "running", "weight"],
        "finance": ["budget", "expense", "savings", "debt", "money", "income", "bill"],
        "education": ["handwriting", "spelling", "math", "sight words", "homeschool"],
    }

    for cat_key, hints in specific_hints.items():
        for hint in hints:
            if hint in title_lower:
                return KDP_CATEGORIES[cat_key]

    # Fall back to general categories
    for key in ["gratitude", "planner", "journal", "notebook"]:
        if key in title_lower or key == interior_type:
            return KDP_CATEGORIES[key]

    return KDP_CATEGORIES["default"]


def _generate_description(variant: Variant) -> str:
    """Generate a KDP description with benefits and formatting."""
    interior_features = {
        "lined": "clean, evenly-spaced lines for free-flowing thoughts and reflections",
        "dotted": "versatile dot-grid pages perfect for writing, sketching, and bullet journaling",
        "grid": "structured grid pages for precise tracking, charts, and organized logging",
        "gratitude": "guided gratitude prompts designed to build a positive daily habit",
        "planner": "structured daily planning pages with schedule blocks, priorities, and notes",
    }

    feature = interior_features.get(variant.interior_type, "thoughtfully designed pages")

    return textwrap.dedent(f"""\
        Looking for the perfect {variant.interior_type} journal? This one was designed \
with purpose, not just filled with blank pages.

Inside You'll Find:
- {variant.page_count} pages of {feature}
- {variant.trim_size} portable size that fits in your bag or on your nightstand
- Premium matte cover for a professional look and feel
- Undated format — start anytime, no wasted pages

Why This Journal:
- Thoughtfully designed interior that's a pleasure to use
- Quality paper that handles most pens without bleed-through
- Makes a meaningful gift for anyone on a self-improvement journey

Whether you use it daily or whenever inspiration strikes, this journal is \
your companion for growth, reflection, and progress.

Add to cart and start writing your next chapter today.\
    """).strip()


def _suggest_price(
    page_count: int,
    competitor_avg_price: float | None = None,
) -> str:
    """Suggest a retail price based on page count and competitor data.

    Uses competitor pricing as anchor when available, otherwise
    falls back to page-count-based tiers.
    """
    # Base price from page count
    if page_count <= 80:
        base = 6.99
    elif page_count <= 120:
        base = 7.99
    elif page_count <= 200:
        base = 9.99
    else:
        base = 12.99

    if competitor_avg_price is None:
        return f"${base:.2f}"

    # Anchor to competitor price: slightly below average for competitive edge
    # but never below our base (to maintain margin)
    competitive = round(competitor_avg_price * 0.95, 2)

    # Snap to common price points
    price_points = [6.99, 7.99, 8.99, 9.99, 10.99, 11.99, 12.99]
    best_price = base
    for pp in price_points:
        if pp >= base and pp <= competitive + 1.00:
            best_price = pp

    return f"${best_price:.2f}"
