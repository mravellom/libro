"""Scaler — Phase 3 logic: multi-marketplace cloning."""

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from libro.common.similarity import content_fingerprint
from libro.config import get_settings
from libro.models.niche import Niche
from libro.models.variant import Variant

log = logging.getLogger(__name__)

# Day-of-week translations for planner/journal interiors
WEEKDAY_TRANSLATIONS: dict[str, list[str]] = {
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    "co.jp": ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"],
    "co.uk": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "fr": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
    "es": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
    "it": ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"],
}

# Title localization hints (minimal — journals don't need full translation)
TITLE_HINTS: dict[str, dict[str, str]] = {
    "de": {
        "journal": "Tagebuch",
        "notebook": "Notizbuch",
        "planner": "Planer",
        "tracker": "Tracker",
        "log": "Logbuch",
    },
    "co.jp": {
        "journal": "ジャーナル",
        "notebook": "ノートブック",
        "planner": "プランナー",
        "tracker": "トラッカー",
        "log": "ログ",
    },
}


@dataclass
class CloneResult:
    """Summary of marketplace cloning."""
    source_variant_id: int = 0
    marketplace: str = ""
    new_variant_id: int | None = None
    new_niche_id: int | None = None
    notes: list[str] = field(default_factory=list)


def clone_for_marketplace(
    session: Session,
    variant_id: int,
    marketplace: str,
) -> CloneResult:
    """Clone a variant for a different Amazon marketplace.

    For low-content books (journals, planners), the main adaptations are:
    - Title hints for discoverability in local language
    - Day-of-week names if interior has days
    - Marketplace field on niche/publication

    The interior PDFs are largely language-independent (lined, dotted, grid).
    """
    result = CloneResult(source_variant_id=variant_id, marketplace=marketplace)

    variant = session.get(Variant, variant_id)
    if not variant:
        result.notes.append(f"Variant #{variant_id} not found")
        return result

    if not variant.niche:
        result.notes.append("Source variant has no niche")
        return result

    settings = get_settings()
    if marketplace not in settings.marketplaces:
        result.notes.append(f"Marketplace '{marketplace}' not in configured list: {settings.marketplaces}")
        return result

    # Create marketplace-specific niche
    mp_keyword = f"{variant.niche.keyword}"
    mp_niche = (
        session.query(Niche)
        .filter(Niche.keyword == mp_keyword, Niche.marketplace == marketplace)
        .first()
    )
    if not mp_niche:
        mp_niche = Niche(
            keyword=mp_keyword,
            niche_type=variant.niche.niche_type,
            marketplace=marketplace,
            status="generating",
        )
        session.add(mp_niche)
        session.flush()

    result.new_niche_id = mp_niche.id

    # Adapt title with locale hints
    title = _localize_title(variant.title, marketplace)

    # Create cloned variant
    fp = content_fingerprint(title, variant.interior_type, variant.trim_size)

    clone = Variant(
        niche_id=mp_niche.id,
        brand_id=variant.brand_id,
        title=title,
        subtitle=variant.subtitle,
        description=variant.description,
        keywords=variant.keywords,
        interior_type=variant.interior_type,
        trim_size=variant.trim_size,
        page_count=variant.page_count,
        content_fingerprint=fp,
        series_id=variant.series_id,
        series_name=variant.series_name,
        status="draft",
    )
    session.add(clone)
    session.flush()

    result.new_variant_id = clone.id
    result.notes.append(f"Cloned variant #{variant_id} → #{clone.id} for marketplace '{marketplace}'")
    result.notes.append(f"Title: {title}")

    # Copy interior PDF if exists (same content works across marketplaces for low-content)
    if variant.interior_pdf_path:
        clone.interior_pdf_path = variant.interior_pdf_path
        result.notes.append("Interior PDF reused (language-independent)")

    # Cover needs to be regenerated with localized title
    result.notes.append("Cover needs regeneration with localized title")

    return result


def _localize_title(title: str, marketplace: str) -> str:
    """Add locale-specific hints to the title for discoverability.

    For low-content books, we keep English title but add local keyword.
    Example: "Gratitude Journal" → "Gratitude Journal | Tagebuch" (for DE)
    """
    hints = TITLE_HINTS.get(marketplace, {})
    if not hints:
        return title

    # Find which hint applies
    title_lower = title.lower()
    for eng_word, local_word in hints.items():
        if eng_word in title_lower:
            return f"{title} | {local_word}"

    return title


def get_marketplace_weekdays(marketplace: str) -> list[str] | None:
    """Get day-of-week names for a marketplace (for planner interiors)."""
    return WEEKDAY_TRANSLATIONS.get(marketplace)
