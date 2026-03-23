"""Similarity guard — prevents publishing too-similar books that Amazon flags."""

import hashlib
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from libro.models.variant import Variant


def title_similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two titles (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def content_fingerprint(title: str, interior_type: str, trim_size: str) -> str:
    """Generate a fingerprint hash for deduplication."""
    raw = f"{title.lower().strip()}|{interior_type}|{trim_size}"
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
