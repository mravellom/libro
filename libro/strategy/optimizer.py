"""Optimizer — Phase 2 logic: auto-kill, series generation, A/B cover testing."""

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from libro.config import get_settings
from libro.models.publication import Publication
from libro.models.variant import Variant
from libro.models.series import Series

log = logging.getLogger(__name__)


# --- Auto-Kill ---

@dataclass
class KillResult:
    """Summary of auto-kill execution."""
    checked: int = 0
    killed: int = 0
    spared: int = 0
    details: list[str] = field(default_factory=list)


def auto_kill_check(session: Session, days: int | None = None) -> KillResult:
    """Mark publications without impressions after N days as 'kill'.

    Rule: If a book has no organic impressions in 21 days, kill it.
    We approximate this by checking if any snapshots show BSR data
    (a book with no BSR/sales data = no impressions).
    """
    settings = get_settings()
    kill_days = days or settings.auto_kill_days
    cutoff = datetime.utcnow() - timedelta(days=kill_days)
    result = KillResult()

    # Publications without a decision, published before cutoff
    pubs = (
        session.query(Publication)
        .filter(
            Publication.decision.is_(None),
            Publication.published_at.isnot(None),
            Publication.published_at <= cutoff,
        )
        .all()
    )

    for pub in pubs:
        result.checked += 1

        # Check if any snapshot shows real activity
        has_activity = False
        if pub.snapshots:
            for snap in pub.snapshots:
                if snap.bsr and snap.bsr < 3_000_000:
                    has_activity = True
                    break
                if snap.reviews_count and snap.reviews_count > 0:
                    has_activity = True
                    break
                if snap.estimated_daily_sales and snap.estimated_daily_sales > 0.05:
                    has_activity = True
                    break

        if pub.impressions_detected:
            has_activity = True

        title = pub.variant.title[:40] if pub.variant else f"pub #{pub.id}"

        if not has_activity:
            pub.decision = "kill"
            pub.decided_at = datetime.utcnow()
            if pub.variant and pub.variant.niche:
                pub.variant.niche.status = "killed"
            result.killed += 1
            result.details.append(f"KILL: {title} — no activity after {kill_days} days")
            log.info(f"Auto-killed publication #{pub.id}: {title}")
        else:
            result.spared += 1
            result.details.append(f"SPARE: {title} — has activity")

    session.flush()
    return result


# --- Find Winners ---

def find_winners(session: Session) -> list[Publication]:
    """Find publications with 'scale' decision — candidates for series expansion."""
    return (
        session.query(Publication)
        .filter(Publication.decision == "scale")
        .all()
    )


# --- Series Generation ---

@dataclass
class SeriesResult:
    """Summary of series generation."""
    series_name: str = ""
    variants_created: int = 0
    details: list[str] = field(default_factory=list)


# Related niche expansions for series generation
SERIES_EXPANSIONS: dict[str, list[str]] = {
    "gratitude": ["meditation diary", "mindfulness log", "self care tracker", "affirmation journal"],
    "fitness": ["meal planner", "supplement tracker", "body measurement log", "workout recovery journal"],
    "workout": ["stretching log", "cardio tracker", "strength training log", "gym notebook"],
    "yoga": ["meditation diary", "breathwork journal", "flexibility tracker", "chakra journal"],
    "budget": ["savings challenge", "expense tracker", "financial goal planner", "debt payoff journal"],
    "recipe": ["meal prep planner", "grocery list notebook", "cooking journal", "baking log"],
    "reading": ["book review journal", "reading challenge tracker", "literary quotes notebook"],
    "prayer": ["devotional journal", "bible study notebook", "scripture writing journal"],
    "planner": ["habit tracker", "goal setting journal", "weekly review notebook"],
    "travel": ["trip planner", "adventure log", "packing checklist notebook"],
    "garden": ["plant care log", "seed starting journal", "harvest tracker"],
}


def generate_series(
    session: Session,
    publication_id: int,
    count: int = 4,
) -> SeriesResult:
    """Generate a product line from a winning publication.

    Takes a successful book and creates related variants with the same
    aesthetic (brand, colors, style) to enable cross-selling on Amazon.
    """
    from libro.generation.variant_engine import TITLE_PATTERNS, AUDIENCES, TIME_FRAMES, BENEFITS
    from libro.common.similarity import content_fingerprint

    result = SeriesResult()

    pub = session.get(Publication, publication_id)
    if not pub or not pub.variant:
        result.details.append(f"Publication #{publication_id} not found")
        return result

    source_variant = pub.variant
    source_niche = source_variant.niche

    if not source_niche:
        result.details.append("Source variant has no niche")
        return result

    # Create or find series
    series_name = f"{source_niche.keyword.title()} Collection"
    result.series_name = series_name

    series = Series(
        name=series_name,
        base_niche_id=source_niche.id,
        brand_id=source_variant.brand_id,
        style_aesthetic=json.dumps({
            "source_variant_id": source_variant.id,
            "interior_type": source_variant.interior_type,
            "trim_size": source_variant.trim_size,
        }),
    )
    session.add(series)
    session.flush()

    # Link source variant to series
    source_variant.series_id = series.id
    source_variant.series_name = series_name

    # Find expansion keywords
    expansion_keywords = _find_expansions(source_niche.keyword)
    if not expansion_keywords:
        expansion_keywords = [f"{source_niche.keyword} {suffix}" for suffix in ["for beginners", "for women", "for men", "weekly"]]

    # Create variants for related niches
    for i, exp_keyword in enumerate(expansion_keywords[:count]):
        # Find or create niche for expansion
        exp_niche = session.query(Niche).filter(Niche.keyword == exp_keyword).first()
        if not exp_niche:
            exp_niche = Niche(
                keyword=exp_keyword,
                niche_type=source_niche.niche_type,
                marketplace=source_niche.marketplace,
                status="generating",
            )
            session.add(exp_niche)
            session.flush()

        # Create variant with same aesthetic as source
        pattern = TITLE_PATTERNS[i % len(TITLE_PATTERNS)]
        audience = AUDIENCES[i % len(AUDIENCES)]
        time_frame = TIME_FRAMES[i % len(TIME_FRAMES)]
        benefit = BENEFITS[i % len(BENEFITS)]

        title = pattern.format(
            keyword=exp_keyword.title(),
            audience=audience,
            time_frame=time_frame,
            benefit=benefit,
            type=source_variant.interior_type.title(),
        )

        fp = content_fingerprint(title, source_variant.interior_type, source_variant.trim_size)

        variant = Variant(
            niche_id=exp_niche.id,
            brand_id=source_variant.brand_id,
            title=title,
            subtitle=f"A {source_variant.interior_type.title()} {exp_keyword.title()} Notebook",
            interior_type=source_variant.interior_type,
            trim_size=source_variant.trim_size,
            page_count=source_variant.page_count,
            content_fingerprint=fp,
            series_id=series.id,
            series_name=series_name,
            status="draft",
        )
        session.add(variant)
        result.variants_created += 1
        result.details.append(f"Created: {title[:50]}...")

    session.flush()
    return result


def _find_expansions(keyword: str) -> list[str]:
    """Find related keywords for series expansion."""
    keyword_lower = keyword.lower()
    for key, expansions in SERIES_EXPANSIONS.items():
        if key in keyword_lower:
            return expansions
    return []


# --- A/B Cover Variants ---

@dataclass
class CoverABResult:
    """Summary of A/B cover generation."""
    variant_id: int = 0
    covers_generated: int = 0
    paths: list[str] = field(default_factory=list)
    palettes_used: list[str] = field(default_factory=list)


def generate_cover_variants(
    session: Session,
    variant_id: int,
    count: int = 3,
) -> CoverABResult:
    """Generate multiple cover variants with different palettes for A/B testing.

    When a book has impressions but low CTR, test different cover designs.
    """
    from libro.branding.cover import CoverGenerator
    from libro.branding.brand_manager import COLOR_PALETTES, BrandStyle
    from libro.models.brand import Brand

    settings = get_settings()
    result = CoverABResult(variant_id=variant_id)

    variant = session.get(Variant, variant_id)
    if not variant:
        return result

    # Select distinct palettes for A/B testing
    available_palettes = list(COLOR_PALETTES.keys())
    random.shuffle(available_palettes)
    selected_palettes = available_palettes[:count]

    generator = CoverGenerator()
    output_dir = settings.output_dir / f"variant_{variant_id}" / "ab_covers"

    # Get author name
    author_name = ""
    if variant.brand_id:
        brand = session.get(Brand, variant.brand_id)
        if brand:
            author_name = brand.name

    for i, palette_name in enumerate(selected_palettes):
        palette = COLOR_PALETTES[palette_name]
        cover_path = output_dir / f"cover_{palette_name}.png"

        try:
            generator.generate(
                title=variant.title,
                subtitle=variant.subtitle or "",
                author=author_name,
                trim_size=variant.trim_size,
                page_count=variant.page_count,
                output_path=cover_path,
                primary_color=palette["primary_color"],
                secondary_color=palette["secondary_color"],
                accent_color=palette["accent_color"],
                font_name="Sans",
            )
            result.covers_generated += 1
            result.paths.append(str(cover_path))
            result.palettes_used.append(palette_name)
        except Exception as e:
            log.error(f"A/B cover generation failed ({palette_name}): {e}")

    return result
