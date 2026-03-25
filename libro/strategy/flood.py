"""Flood pipeline — high-volume book production for Phase 1."""

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from libro.config import get_settings
from libro.models.niche import Niche
from libro.models.variant import Variant

log = logging.getLogger(__name__)


@dataclass
class FloodResult:
    """Summary of a flood pipeline run."""
    niches_processed: int = 0
    variants_created: int = 0
    interiors_generated: int = 0
    covers_generated: int = 0
    packages_ready: int = 0
    skipped_bsr: int = 0
    errors: list[str] = field(default_factory=list)


def flood_pipeline(
    session: Session,
    daily_target: int | None = None,
    evergreen_ratio: float | None = None,
    brand_id: int | None = None,
    dry_run: bool = False,
) -> FloodResult:
    """Execute the flooding strategy: produce books at scale.

    1. Select niches (70% evergreen, 30% trending)
    2. For each niche: generate variants → interior → cover → package
    3. Respect max_bsr_threshold (300K rule)

    Args:
        session: DB session.
        daily_target: Books to produce (default from config).
        evergreen_ratio: Ratio of evergreen vs trending (default from config).
        brand_id: Brand to use for covers (picks random existing if None).
        dry_run: If True, only plan without generating files.
    """
    from libro.strategy.evergreen_niches import get_evergreen_sample

    settings = get_settings()
    target = daily_target or settings.flood_daily_target
    target = min(target, settings.flood_max_daily_target)
    ev_ratio = evergreen_ratio or settings.flood_evergreen_ratio

    result = FloodResult()

    # Calculate split
    evergreen_count = int(target * ev_ratio)
    trending_count = target - evergreen_count

    # --- Step 1: Select niches ---
    niches_to_process: list[tuple[str, list[str], str]] = []  # (keyword, interior_types, niche_type)

    # Evergreen niches from curated list
    evergreen_sample = get_evergreen_sample(evergreen_count)
    for keyword, interior_types in evergreen_sample:
        niches_to_process.append((keyword, interior_types, "evergreen"))

    # Trending niches from DB (scored, not yet generating)
    trending_niches = (
        session.query(Niche)
        .filter(
            Niche.niche_type == "trending",
            Niche.status.in_(["discovered", "scored"]),
            Niche.opportunity_score >= settings.min_opportunity_score,
        )
        .order_by(Niche.opportunity_score.desc())
        .limit(trending_count)
        .all()
    )

    for niche in trending_niches:
        niches_to_process.append((niche.keyword, ["lined", "dotted", "grid"], "trending"))

    # Fill remaining trending slots with more evergreen if not enough trending
    if len(trending_niches) < trending_count:
        extra = get_evergreen_sample(trending_count - len(trending_niches))
        for keyword, interior_types in extra:
            niches_to_process.append((keyword, interior_types, "evergreen"))

    if dry_run:
        result.niches_processed = len(niches_to_process)
        result.variants_created = len(niches_to_process)  # 1 per niche in dry run estimate
        return result

    # --- Step 2: Process each niche ---
    for keyword, interior_types, niche_type in niches_to_process:
        try:
            _process_niche(
                session, keyword, interior_types, niche_type,
                brand_id, result, settings,
            )
        except Exception as e:
            log.error(f"Error processing niche '{keyword}': {e}")
            result.errors.append(f"{keyword}: {e}")

    # Velocity warning (5.4.8 compliance)
    _check_velocity_warning(session, settings)

    return result


def _check_velocity_warning(session: Session, settings) -> None:
    """Log a warning if publishing velocity exceeds compliance thresholds."""
    from datetime import datetime, timedelta
    from libro.models.publication import Publication

    now = datetime.utcnow()
    count_7d = (
        session.query(Publication)
        .filter(Publication.published_at >= now - timedelta(days=7))
        .count()
    )
    count_30d = (
        session.query(Publication)
        .filter(Publication.published_at >= now - timedelta(days=30))
        .count()
    )

    if count_7d > settings.compliance_velocity_7d_max:
        log.warning(
            f"5.4.8 VELOCITY ALERT: {count_7d} publications in 7 days "
            f"(threshold: {settings.compliance_velocity_7d_max}). "
            "Review publishing pace to avoid spam classification."
        )
    if count_30d > settings.compliance_velocity_30d_max:
        log.warning(
            f"5.4.8 VELOCITY ALERT: {count_30d} publications in 30 days "
            f"(threshold: {settings.compliance_velocity_30d_max}). "
            "Review publishing pace to avoid spam classification."
        )


def _process_niche(
    session: Session,
    keyword: str,
    interior_types: list[str],
    niche_type: str,
    brand_id: int | None,
    result: FloodResult,
    settings,
) -> None:
    """Process a single niche: create/find niche → variant → interior → cover → package."""
    from libro.generation.variant_engine import generate_variants
    from libro.generation.interior import generate_interior
    from libro.branding.cover import CoverGenerator
    from libro.branding.brand_manager import BrandStyle, COLOR_PALETTES
    from libro.models.brand import Brand

    # Find or create niche
    niche = session.query(Niche).filter(Niche.keyword == keyword).first()
    if not niche:
        niche = Niche(
            keyword=keyword,
            niche_type=niche_type,
            marketplace=settings.amazon_marketplace,
            status="discovered",
        )
        session.add(niche)
        session.flush()

    # Check BSR threshold (regla de oro: no competir si avg BSR > 300K)
    if niche.avg_bsr and niche.avg_bsr > settings.max_bsr_threshold:
        log.info(f"Skipping '{keyword}': avg BSR {niche.avg_bsr:,.0f} > {settings.max_bsr_threshold:,}")
        result.skipped_bsr += 1
        return

    result.niches_processed += 1

    # Generate 1 variant per niche (for daily volume)
    variants = generate_variants(session, niche.id, count=1)
    if not variants:
        result.errors.append(f"{keyword}: no variants created (similarity guard)")
        return

    variant = variants[0]
    result.variants_created += 1

    # Override interior type if specified
    if interior_types:
        chosen_interior = random.choice(interior_types)
        variant.interior_type = chosen_interior

    # Assign seed for unique interior generation
    variant.interior_seed = variant.id
    session.flush()

    # Generate interior PDF
    try:
        output_dir = settings.output_dir / f"variant_{variant.id}"
        interior_path = output_dir / "interior.pdf"
        generate_interior(
            template_name=variant.interior_type,
            output_path=interior_path,
            trim_size=variant.trim_size,
            page_count=variant.page_count,
            seed=variant.interior_seed,
        )
        variant.interior_pdf_path = str(interior_path)
        result.interiors_generated += 1
    except Exception as e:
        log.error(f"Interior generation failed for variant #{variant.id}: {e}")
        result.errors.append(f"interior #{variant.id}: {e}")
        return

    # Generate cover
    try:
        # Get brand style
        if brand_id:
            brand = session.get(Brand, brand_id)
            style = BrandStyle.from_brand(brand) if brand else _random_style()
            author_name = brand.name if brand else ""
        else:
            # Pick a random existing brand or use random palette
            brand = session.query(Brand).first()
            if brand:
                style = BrandStyle.from_brand(brand)
                author_name = brand.name
            else:
                style = _random_style()
                author_name = ""

        cover_path = output_dir / "cover.png"
        generator = CoverGenerator()
        generator.generate(
            title=variant.title,
            subtitle=variant.subtitle or "",
            author=author_name,
            trim_size=variant.trim_size,
            page_count=variant.page_count,
            output_path=cover_path,
            primary_color=style.primary_color,
            secondary_color=style.secondary_color,
            accent_color=style.accent_color,
            font_name=style.font,
        )
        variant.cover_pdf_path = str(cover_path)
        variant.status = "pending_review" if settings.require_human_review else "ready"
        result.covers_generated += 1
    except Exception as e:
        log.error(f"Cover generation failed for variant #{variant.id}: {e}")
        result.errors.append(f"cover #{variant.id}: {e}")
        return

    # Package for KDP
    try:
        from libro.publication.packager import package_variant
        pkg = package_variant(session, variant.id, author=author_name)
        if pkg.checklist_passed:
            result.packages_ready += 1
    except Exception as e:
        log.error(f"Packaging failed for variant #{variant.id}: {e}")
        result.errors.append(f"package #{variant.id}: {e}")

    session.flush()


def _random_style():
    """Return a random BrandStyle from available palettes."""
    from libro.branding.brand_manager import BrandStyle, COLOR_PALETTES
    palette_name = random.choice(list(COLOR_PALETTES.keys()))
    palette = COLOR_PALETTES[palette_name]
    return BrandStyle(
        font="Sans",
        primary_color=palette["primary_color"],
        secondary_color=palette["secondary_color"],
        accent_color=palette["accent_color"],
    )
