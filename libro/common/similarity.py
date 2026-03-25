"""Similarity guard — prevents publishing too-similar books that Amazon flags."""

import hashlib
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from libro.models.variant import Variant


def title_similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two titles (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def content_fingerprint(
    title: str, interior_type: str, trim_size: str, seed: int | None = None
) -> str:
    """Generate a fingerprint hash for deduplication."""
    raw = f"{title.lower().strip()}|{interior_type}|{trim_size}|{seed or 0}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def check_similarity(
    session: Session,
    title: str,
    niche_id: int,
    threshold: float = 0.7,
    max_similar: int = 3,
) -> list[str]:
    """Check if a proposed title is too similar to existing active variants.

    Returns list of warning messages. Empty list = safe to proceed.
    """
    warnings: list[str] = []

    active_variants = (
        session.query(Variant)
        .filter(
            Variant.niche_id == niche_id,
            Variant.status.in_(["draft", "ready", "selected", "published"]),
        )
        .all()
    )

    similar_count = 0
    for v in active_variants:
        sim = title_similarity(title, v.title)
        if sim >= threshold:
            similar_count += 1
            warnings.append(
                f"Title '{title}' is {sim:.0%} similar to existing variant #{v.id}: '{v.title}'"
            )

    if similar_count >= max_similar:
        warnings.insert(
            0,
            f"BLOCKED: {similar_count} similar titles already exist (max {max_similar}). "
            "Amazon may flag this as duplicate content.",
        )

    return warnings


def check_catalog_similarity(
    session: Session,
    title: str,
    threshold: float = 0.85,
    max_similar: int = 5,
    exclude_variant_id: int | None = None,
) -> list[str]:
    """Check title similarity across the ENTIRE catalog (cross-niche).

    Unlike check_similarity() which is scoped to a single niche, this detects
    catalog-wide patterns that Amazon may classify as spam under 5.4.8.

    Returns list of warning messages. Empty list = safe.
    """
    warnings: list[str] = []

    query = session.query(Variant).filter(
        Variant.status.in_(["ready", "selected", "published", "pending_review"]),
    )
    if exclude_variant_id:
        query = query.filter(Variant.id != exclude_variant_id)

    # Limit to 200 most recent for performance (O(N) comparisons)
    active_variants = query.order_by(Variant.created_at.desc()).limit(200).all()

    similar_count = 0
    for v in active_variants:
        sim = title_similarity(title, v.title)
        if sim >= threshold:
            similar_count += 1
            warnings.append(
                f"Cross-catalog match: '{v.title}' (#{v.id}) — {sim:.0%} similar"
            )

    if similar_count >= max_similar:
        warnings.insert(
            0,
            f"SPAM RISK: {similar_count} catalog-wide titles with >{threshold:.0%} similarity. "
            "Amazon 5.4.8 may flag as deceptive/duplicate content pattern.",
        )

    return warnings
