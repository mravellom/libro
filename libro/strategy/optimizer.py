"""Optimizer — advisory evaluation, series generation, A/B cover testing."""

import json
import logging
import random
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from libro.config import get_settings
from libro.models.publication import Publication
from libro.models.variant import Variant
from libro.models.series import Series

log = logging.getLogger(__name__)


# --- Advisory Evaluation ---

@dataclass
class EvaluationResult:
    """Summary of advisory evaluation run."""
    checked: int = 0
    recommendations: dict = field(default_factory=lambda: {"scale": 0, "iterate": 0, "kill": 0})
    snoozed_skipped: int = 0
    details: list[str] = field(default_factory=list)


@dataclass
class KillResult:
    """Summary of auto-kill execution (deprecated)."""
    checked: int = 0
    killed: int = 0
    spared: int = 0
    details: list[str] = field(default_factory=list)


def evaluate_all(session: Session, days: int | None = None) -> EvaluationResult:
    """Evaluate all pending publications and set advisory recommendations.

    Queries publications where ``decision IS NULL`` and ``published_at`` is at
    least ``evaluation_min_days`` ago.  For each publication, computes a
    recommended decision (scale / iterate / kill) using the
    :class:`~libro.tracking.evaluator.PerformanceEvaluator` when sufficient
    snapshot data exists, falling back to a simple activity-based heuristic.

    Recommendations are written to advisory columns on the publication so a
    human operator can review them via the dashboard.  If
    ``settings.auto_apply_decisions`` is ``True``, the final ``decision`` column
    is also set (backward-compatible auto-kill behaviour).
    """
    from libro.tracking.evaluator import PerformanceEvaluator
    from libro.models.tracking import TrackingSnapshot

    settings = get_settings()
    eval_days = days or settings.evaluation_min_days
    cutoff = datetime.now(UTC) - timedelta(days=eval_days)
    now = datetime.now(UTC)
    result = EvaluationResult()

    pubs = (
        session.query(Publication)
        .filter(
            Publication.decision.is_(None),
            Publication.published_at.isnot(None),
            Publication.published_at <= cutoff,
        )
        .all()
    )

    evaluator = PerformanceEvaluator()

    for pub in pubs:
        # Skip snoozed publications
        if pub.snoozed_until and pub.snoozed_until > now:
            result.snoozed_skipped += 1
            continue

        result.checked += 1
        title = pub.variant.title[:40] if pub.variant else f"pub #{pub.id}"

        # Gather snapshots for rich evaluation
        snapshots = (
            session.query(TrackingSnapshot)
            .filter(TrackingSnapshot.publication_id == pub.id)
            .order_by(TrackingSnapshot.captured_at)
            .all()
        )

        if len(snapshots) >= evaluator.min_snapshots:
            # Use full evaluator logic
            evaluation = evaluator.evaluate(pub, snapshots)
            recommendation = evaluation.recommendation
            confidence = evaluation.confidence
            reasons = evaluation.reasons
        else:
            # Fallback: simple activity-based heuristic (mirrors old auto-kill)
            recommendation, confidence, reasons = _simple_evaluate(pub, eval_days)

        # Write advisory columns
        pub.recommended_decision = recommendation
        pub.recommendation_confidence = confidence
        pub.recommendation_reasons = json.dumps(reasons)
        pub.recommended_at = now

        # Backward-compatible auto-apply
        if settings.auto_apply_decisions:
            pub.decision = recommendation
            pub.decided_at = now
            if recommendation == "kill" and pub.variant and pub.variant.niche:
                pub.variant.niche.status = "killed"

        result.recommendations[recommendation] += 1
        result.details.append(
            f"{recommendation.upper()} ({confidence:.0%}): {title} — {reasons[-1] if reasons else 'no detail'}"
        )
        log.info(
            "Evaluated publication #%d (%s): %s (confidence=%.2f)",
            pub.id, title, recommendation, confidence,
        )

    session.flush()
    return result


def _simple_evaluate(pub: Publication, eval_days: int) -> tuple[str, float, list[str]]:
    """Fallback heuristic when not enough snapshots exist for full evaluation.

    Returns ``(recommendation, confidence, reasons)`` using the same activity
    checks that the old ``auto_kill_check`` used.
    """
    reasons: list[str] = []
    has_activity = False

    if pub.snapshots:
        for snap in pub.snapshots:
            if snap.bsr and snap.bsr < 3_000_000:
                has_activity = True
                reasons.append(f"BSR {snap.bsr:,} indicates visibility")
                break
            if snap.reviews_count and snap.reviews_count > 0:
                has_activity = True
                reasons.append(f"{snap.reviews_count} review(s) detected")
                break
            if snap.estimated_daily_sales and snap.estimated_daily_sales > 0.05:
                has_activity = True
                reasons.append(f"Estimated sales {snap.estimated_daily_sales:.2f}/day")
                break

    if pub.impressions_detected:
        has_activity = True
        reasons.append("Impressions detected")

    if not has_activity:
        reasons.append(f"No activity after {eval_days} days")
        return "kill", 0.8, reasons

    reasons.append("Some activity present — needs more data")
    return "iterate", 0.4, reasons


def auto_kill_check(session: Session, days: int | None = None) -> KillResult:
    """Deprecated: use :func:`evaluate_all` instead.

    This wrapper calls ``evaluate_all`` and converts the result into a
    ``KillResult`` for backward compatibility.
    """
    warnings.warn(
        "auto_kill_check() is deprecated; use evaluate_all() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    log.warning("auto_kill_check() is deprecated — migrating call to evaluate_all()")

    eval_result = evaluate_all(session, days=days)

    return KillResult(
        checked=eval_result.checked,
        killed=eval_result.recommendations.get("kill", 0),
        spared=eval_result.checked - eval_result.recommendations.get("kill", 0),
        details=eval_result.details,
    )


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
    from libro.generation.title_engine import generate_title
    from libro.generation.personas import get_personas_for_niche
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

    # Create variants for related niches using title engine + personas
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

        # Use personas and title engine for compelling titles
        personas = get_personas_for_niche(exp_keyword)
        persona = personas[i % len(personas)] if personas else personas[0]
        seed = hash(f"series_{publication_id}_{exp_keyword}_{i}") & 0x7FFFFFFF

        generated = generate_title(
            niche_keyword=exp_keyword,
            persona=persona,
            seed=seed,
            interior_type=source_variant.interior_type,
            page_count=source_variant.page_count,
            trim_size=source_variant.trim_size,
        )

        fp = content_fingerprint(generated.title, source_variant.interior_type, source_variant.trim_size)

        variant = Variant(
            niche_id=exp_niche.id,
            brand_id=source_variant.brand_id,
            title=generated.title,
            subtitle=generated.subtitle,
            description=generated.description,
            keywords=", ".join(generated.keywords),
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
        result.details.append(f"Created: {generated.title[:50]}...")

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
