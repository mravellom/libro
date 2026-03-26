"""Variant engine — creates market-aware book variants from niche analysis.

Uses buyer personas, competitor keyword analysis, and the title engine
to generate variants with compelling titles, targeted descriptions,
and optimized keywords — not just mechanical combinations.
"""

import logging

from sqlalchemy.orm import Session

from libro.common.similarity import check_similarity, content_fingerprint
from libro.config import get_settings
from libro.generation.personas import Persona, get_personas_for_niche
from libro.generation.title_engine import generate_title
from libro.models.niche import Niche
from libro.models.product import Product
from libro.models.variant import Variant

log = logging.getLogger(__name__)


def generate_variants(
    session: Session,
    niche_id: int,
    count: int = 3,
    tier: str = "scout",
) -> list[Variant]:
    """Create diverse, market-aware book variants for a niche.

    Each variant targets a specific buyer persona with a compelling title,
    tailored description, and optimized keywords.

    Args:
        session: DB session.
        niche_id: Niche to generate variants for.
        count: Number of variants to create.
        tier: "scout" for quick test variants, "hero" for premium variants.

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

    # Analyze competitors for market intelligence
    analysis = _analyze_competitors(products)
    competitor_keywords = _extract_competitor_keywords(products)

    # Get relevant personas for this niche
    personas = get_personas_for_niche(niche.keyword)

    # Generate diverse combinations
    variants_data = _create_variant_combos(
        niche, analysis, personas, competitor_keywords, count, tier,
    )

    # Create variants with similarity guard
    created: list[Variant] = []
    for vdata in variants_data:
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


def _extract_competitor_keywords(products: list[Product]) -> list[str]:
    """Extract keyword insights from competitor titles using the keyword analyzer."""
    titles = [p.title for p in products if p.title]
    if not titles:
        return []

    try:
        from libro.intelligence.keyword_analyzer import analyze_titles
        insight = analyze_titles(titles)
        return insight.suggested_keywords
    except Exception:
        return []


def _create_variant_combos(
    niche: Niche,
    analysis: dict,
    personas: list[Persona],
    competitor_keywords: list[str],
    count: int,
    tier: str,
) -> list[dict]:
    """Create diverse variant configurations using personas and the title engine."""
    keyword = niche.keyword
    variants = []

    trim_sizes = [analysis["popular_trim"]]
    if analysis["popular_trim"] != "6x9":
        trim_sizes.append("6x9")

    page_counts = analysis.get("popular_page_counts", [120])
    if 120 not in page_counts:
        page_counts.append(120)

    # Use competitor avg_price to inform page count selection
    # Higher competitor prices → we can justify more pages
    avg_price = analysis.get("avg_price", 9.99)

    for i in range(count):
        # Cycle through personas for audience diversity
        persona = personas[i % len(personas)]

        # Pick interior type from persona preferences
        interior = persona.preferred_interiors[i % len(persona.preferred_interiors)]

        trim = trim_sizes[i % len(trim_sizes)]
        pages = page_counts[i % len(page_counts)]

        # Hero tier: use more pages for premium feel
        if tier == "hero" and pages < 150:
            pages = 150

        # Generate compelling title using the title engine
        seed = hash(f"{keyword}_{persona.name}_{i}") & 0x7FFFFFFF
        generated = generate_title(
            niche_keyword=keyword,
            persona=persona,
            seed=seed,
            interior_type=interior,
            page_count=pages,
            trim_size=trim,
            competitor_keywords=competitor_keywords,
        )

        variants.append({
            "title": generated.title,
            "subtitle": generated.subtitle,
            "description": generated.description,
            "keywords": ", ".join(generated.keywords),
            "interior_type": interior,
            "trim_size": trim,
            "page_count": pages,
            "persona": persona.name,
            "tier": tier,
        })

    return variants
