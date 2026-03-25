"""Variant engine — creates data-driven book variants from niche analysis."""

import logging
from itertools import product as itertools_product

from sqlalchemy.orm import Session

from libro.common.similarity import check_similarity, content_fingerprint
from libro.config import get_settings
from libro.models.niche import Niche
from libro.models.product import Product
from libro.models.variant import Variant

log = logging.getLogger(__name__)

# Title patterns commonly used in low-content KDP books
TITLE_PATTERNS = [
    "{keyword}: A Daily Journal for {audience}",
    "{keyword} Notebook: {time_frame} Guide to {benefit}",
    "{keyword} for {audience}: {time_frame} {type} Journal",
    "The {time_frame} {keyword} Journal: {benefit}",
    "My {keyword} Journal: A {type} Notebook for {audience}",
]

AUDIENCES = [
    "Women", "Men", "Teens", "Adults",
    "Beginners", "Self-Care Enthusiasts",
]

TIME_FRAMES = [
    "Daily", "52-Week", "90-Day", "5-Minute", "365-Day",
]

BENEFITS = [
    "Mindfulness and Positivity",
    "Self-Discovery and Growth",
    "Reflection and Inner Peace",
    "Building Better Habits",
    "Finding Joy Every Day",
]


def generate_variants(
    session: Session,
    niche_id: int,
    count: int = 3,
) -> list[Variant]:
    """Create diverse book variants for a niche.

    Analyzes existing products in the niche to inform:
    - Which trim sizes sell best
    - Which interior types to use
    - Title patterns that work
    - Keywords to target

    Args:
        session: DB session.
        niche_id: Niche to generate variants for.
        count: Number of variants to create.

    Returns:
        List of created Variant records.
    """
    settings = get_settings()
    niche = session.get(Niche, niche_id)
    if not niche:
        raise ValueError(f"Niche #{niche_id} not found")

    products = (
        session.query(Product)
        .filter(Product.niche_id == niche_id)
        .all()
    )

    # Analyze competitors to inform variant creation
    analysis = _analyze_competitors(products)

    # Generate diverse combinations
    variants_data = _create_variant_combos(niche, analysis, count)

    # Create variants with similarity guard
    created: list[Variant] = []
    for vdata in variants_data:
        # Check similarity
        warnings = check_similarity(
            session,
            vdata["title"],
            niche_id,
            threshold=settings.similarity_title_threshold,
            max_similar=settings.similarity_max_similar_active,
        )

        if any("BLOCKED" in w for w in warnings):
            log.warning(f"Skipping variant: {warnings[0]}")
            continue

        for w in warnings:
            log.info(f"Similarity warning: {w}")

        fingerprint = content_fingerprint(
            vdata["title"], vdata["interior_type"], vdata["trim_size"]
        )

        variant = Variant(
            niche_id=niche_id,
            title=vdata["title"],
            subtitle=vdata.get("subtitle"),
            description=vdata.get("description"),
            keywords=vdata.get("keywords"),
            interior_type=vdata["interior_type"],
            trim_size=vdata["trim_size"],
            page_count=vdata.get("page_count", settings.default_page_count),
            content_fingerprint=fingerprint,
            status="draft",
        )
        session.add(variant)
        created.append(variant)

    if created:
        niche.status = "generating"
        session.flush()

        # Assign interior seeds after flush (variant IDs now assigned)
        for v in created:
            v.interior_seed = v.id
            # Update fingerprint to include seed
            v.content_fingerprint = content_fingerprint(
                v.title, v.interior_type, v.trim_size, seed=v.interior_seed
            )
        session.flush()

    return created


def _analyze_competitors(products: list[Product]) -> dict:
    """Analyze competitor products to inform variant creation."""
    analysis = {
        "popular_trim": "6x9",
        "popular_page_counts": [120],
        "interior_types": ["lined", "dotted", "grid"],
        "avg_price": 9.99,
    }

    if not products:
        return analysis

    # Most common dimensions
    dims = [p.dimensions for p in products if p.dimensions]
    if dims:
        # Map common Amazon dimensions to KDP trim sizes
        for d in dims:
            if "6" in d and "9" in d:
                analysis["popular_trim"] = "6x9"
                break
            elif "8.5" in d and "11" in d:
                analysis["popular_trim"] = "8.5x11"
                break
            elif "5.5" in d and "8.5" in d:
                analysis["popular_trim"] = "5.5x8.5"
                break

    # Page counts
    pages = [p.page_count for p in products if p.page_count]
    if pages:
        analysis["popular_page_counts"] = sorted(set(pages))[:3]

    # Avg price
    prices = [p.price for p in products if p.price]
    if prices:
        analysis["avg_price"] = sum(prices) / len(prices)

    return analysis


def _create_variant_combos(
    niche: Niche, analysis: dict, count: int
) -> list[dict]:
    """Create diverse variant configurations."""
    keyword = niche.keyword
    variants = []

    # Interior types to cycle through
    interior_types = ["lined", "dotted", "gratitude", "planner", "grid"]
    trim_sizes = [analysis["popular_trim"]]
    if analysis["popular_trim"] != "6x9":
        trim_sizes.append("6x9")

    # Page count options
    page_counts = analysis.get("popular_page_counts", [120])
    if 120 not in page_counts:
        page_counts.append(120)

    for i in range(count):
        interior = interior_types[i % len(interior_types)]
        trim = trim_sizes[i % len(trim_sizes)]
        pages = page_counts[i % len(page_counts)]
        audience = AUDIENCES[i % len(AUDIENCES)]
        time_frame = TIME_FRAMES[i % len(TIME_FRAMES)]
        benefit = BENEFITS[i % len(BENEFITS)]
        pattern = TITLE_PATTERNS[i % len(TITLE_PATTERNS)]

        title = pattern.format(
            keyword=keyword.title(),
            audience=audience,
            time_frame=time_frame,
            benefit=benefit,
            type=interior.title(),
        )

        subtitle = f"A {interior.title()} {keyword.title()} Notebook for {audience}"

        # KDP keywords (comma-separated, max 7)
        kw_parts = keyword.split()
        keywords_list = [
            keyword,
            f"{keyword} for {audience.lower()}",
            f"{time_frame.lower()} {keyword}",
            f"{keyword} notebook",
            f"{keyword} journal",
            interior + " journal",
            benefit.lower(),
        ]
        keywords = ", ".join(keywords_list[:7])

        description = (
            f"This beautifully designed {keyword} journal features {pages} pages "
            f"of {interior} interior in a {trim} format. Perfect for {audience.lower()} "
            f"looking for {benefit.lower()}. Use it as a {time_frame.lower()} companion "
            f"for your personal growth journey."
        )

        variants.append({
            "title": title,
            "subtitle": subtitle,
            "description": description,
            "keywords": keywords,
            "interior_type": interior,
            "trim_size": trim,
            "page_count": pages,
        })

    return variants
