"""Niche-based cover style mapping.

Maps niche categories to visual styles that match top-seller aesthetics
in each category, rather than using random palettes.
"""

from dataclasses import dataclass

from libro.branding.brand_manager import COLOR_PALETTES


@dataclass
class NicheCoverStyle:
    """Visual style recommendation for a niche category."""
    palette: str                    # Key in COLOR_PALETTES
    preferred_layouts: list[int]    # Indices into cover.py LAYOUTS (0-7)
    font_style: str                 # Sans, Serif, or a specific font
    description: str


# ---------------------------------------------------------------------------
# Category → visual style mapping (based on KDP top-seller patterns)
# ---------------------------------------------------------------------------

NICHE_STYLES: dict[str, NicheCoverStyle] = {
    "wellness": NicheCoverStyle(
        palette="sage",
        preferred_layouts=[5, 6, 2],   # minimal_modern, watercolor, frame
        font_style="Serif",
        description="Soft, calming — watercolor/botanical feel",
    ),
    "gratitude": NicheCoverStyle(
        palette="blush",
        preferred_layouts=[6, 5, 7],   # watercolor, minimal_modern, layered_shapes
        font_style="Serif",
        description="Warm, feminine — soft colors with elegant typography",
    ),
    "fitness": NicheCoverStyle(
        palette="slate",
        preferred_layouts=[0, 3, 4],   # geometric, split, pattern
        font_style="Sans",
        description="Bold, energetic — dark backgrounds with strong contrast",
    ),
    "finance": NicheCoverStyle(
        palette="midnight",
        preferred_layouts=[5, 0, 3],   # minimal_modern, geometric, split
        font_style="Sans",
        description="Clean, professional — dark/navy with gold or red accent",
    ),
    "education": NicheCoverStyle(
        palette="ocean",
        preferred_layouts=[4, 2, 7],   # pattern, frame, layered_shapes
        font_style="Sans",
        description="Playful but clean — bright colors, friendly feel",
    ),
    "hobby": NicheCoverStyle(
        palette="forest",
        preferred_layouts=[6, 2, 7],   # watercolor, frame, layered_shapes
        font_style="Serif",
        description="Natural, earthy — warm tones with organic feel",
    ),
    "productivity": NicheCoverStyle(
        palette="minimal",
        preferred_layouts=[5, 0, 3],   # minimal_modern, geometric, split
        font_style="Sans",
        description="Ultra-clean, modern — white/black with minimal accent",
    ),
    "professional": NicheCoverStyle(
        palette="ocean",
        preferred_layouts=[5, 3, 0],   # minimal_modern, split, geometric
        font_style="Sans",
        description="Trustworthy, clean — blue tones, professional look",
    ),
    "spiritual": NicheCoverStyle(
        palette="sunset",
        preferred_layouts=[6, 7, 2],   # watercolor, layered_shapes, frame
        font_style="Serif",
        description="Warm, contemplative — purple/gold, elegant",
    ),
    "creative": NicheCoverStyle(
        palette="blush",
        preferred_layouts=[6, 7, 4],   # watercolor, layered_shapes, pattern
        font_style="Serif",
        description="Artistic, expressive — soft tones, creative layouts",
    ),
}

# Default fallback
DEFAULT_STYLE = NicheCoverStyle(
    palette="forest",
    preferred_layouts=[5, 6, 0],
    font_style="Sans",
    description="Versatile default — works across categories",
)


# ---------------------------------------------------------------------------
# Keyword → category mapping
# ---------------------------------------------------------------------------

_KEYWORD_TO_CATEGORY: dict[str, str] = {
    # Wellness
    "anxiety": "wellness", "mindfulness": "wellness", "self care": "wellness",
    "self-care": "wellness", "mental health": "wellness", "stress": "wellness",
    "wellness": "wellness", "healing": "wellness", "therapy": "wellness",
    "shadow work": "wellness",
    # Gratitude
    "gratitude": "gratitude", "thankful": "gratitude", "grateful": "gratitude",
    "appreciation": "gratitude", "positivity": "gratitude",
    # Spiritual
    "prayer": "spiritual", "bible": "spiritual", "faith": "spiritual",
    "meditation": "spiritual", "manifestation": "spiritual", "spiritual": "spiritual",
    "devotional": "spiritual",
    # Fitness
    "fitness": "fitness", "workout": "fitness", "exercise": "fitness",
    "gym": "fitness", "running": "fitness", "yoga": "fitness",
    "bodybuilding": "fitness", "weight loss": "fitness", "weight": "fitness",
    "calorie": "fitness", "food diary": "fitness", "meal": "fitness",
    "water intake": "fitness",
    # Finance
    "budget": "finance", "expense": "finance", "savings": "finance",
    "debt": "finance", "bill": "finance", "income": "finance",
    "money": "finance", "financial": "finance",
    # Education
    "handwriting": "education", "spelling": "education", "math": "education",
    "sight words": "education", "story writing": "education",
    "homeschool": "education", "school": "education", "learning": "education",
    # Hobby
    "recipe": "hobby", "reading": "hobby", "garden": "hobby",
    "travel": "hobby", "bird": "hobby", "fishing": "hobby",
    "wine": "hobby", "craft": "hobby", "music": "hobby",
    "hiking": "hobby", "camping": "hobby", "cooking": "hobby",
    # Productivity
    "habit": "productivity", "goal": "productivity", "planner": "productivity",
    "to do": "productivity", "to-do": "productivity", "time management": "productivity",
    "project": "productivity", "daily planner": "productivity",
    "weekly planner": "productivity",
    # Professional
    "meeting": "professional", "password": "professional",
    "address": "professional", "blood pressure": "professional",
    "blood sugar": "professional", "medication": "professional",
    "vehicle": "professional", "pet": "professional",
    # Creative
    "dream": "creative", "journal writing": "creative", "creative": "creative",
    "art": "creative", "sketch": "creative", "drawing": "creative",
    "bullet journal": "creative",
}


def get_cover_style_for_niche(niche_keyword: str) -> NicheCoverStyle:
    """Determine the best cover style for a niche keyword.

    Matches keyword fragments against the category map.
    """
    keyword_lower = niche_keyword.lower()

    # Try exact phrase matches first (longer = more specific)
    for kw, category in sorted(_KEYWORD_TO_CATEGORY.items(), key=lambda x: -len(x[0])):
        if kw in keyword_lower:
            return NICHE_STYLES.get(category, DEFAULT_STYLE)

    return DEFAULT_STYLE


def get_palette_for_style(style: NicheCoverStyle) -> dict:
    """Get the full color palette dict for a niche style."""
    return COLOR_PALETTES.get(style.palette, COLOR_PALETTES["forest"])


def get_layout_index(style: NicheCoverStyle, seed: int) -> int:
    """Pick a layout index from the style's preferred layouts using a seed."""
    import random
    rng = random.Random(seed)
    return rng.choice(style.preferred_layouts)
