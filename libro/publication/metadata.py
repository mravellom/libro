"""KDP metadata generation — title, description, keywords, categories."""

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
) -> KDPMetadata:
    """Generate KDP-ready metadata from a variant.

    Args:
        variant: The book variant to generate metadata for.
        author: Author/brand name.
        language: Book language.

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

    # Price suggestion based on page count
    price = _suggest_price(variant.page_count)

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

    for key in ["gratitude", "planner", "journal", "notebook"]:
        if key in title_lower or key == interior_type:
            return KDP_CATEGORIES[key]

    return KDP_CATEGORIES["default"]


def _generate_description(variant: Variant) -> str:
    """Generate a KDP description from variant data."""
    return textwrap.dedent(f"""\
        Discover the perfect {variant.interior_type} journal designed to inspire \
        your daily practice. This {variant.trim_size} book features {variant.page_count} \
        pages of thoughtfully designed {variant.interior_type} interior.

        Features:
        - {variant.page_count} pages of premium {variant.interior_type} layout
        - {variant.trim_size} trim size — perfect for carrying anywhere
        - High-quality matte cover
        - Ideal for personal use or as a thoughtful gift

        Start your journey today with this beautifully crafted journal.\
    """).strip()


def _suggest_price(page_count: int) -> str:
    """Suggest a retail price based on page count.

    KDP minimum for paperback is typically $0.99 + printing cost.
    Sweet spot for low-content: $6.99-$12.99.
    """
    if page_count <= 80:
        return "$6.99"
    elif page_count <= 120:
        return "$7.99"
    elif page_count <= 200:
        return "$9.99"
    else:
        return "$12.99"
