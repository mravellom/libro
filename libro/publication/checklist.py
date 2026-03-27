"""Publication readiness checklist — validates everything before KDP upload."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from libro.models.variant import Variant

log = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    passed: bool
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ChecklistResult:
    """Full checklist result."""
    variant_id: int
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "error")

    @property
    def errors(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "error"]

    @property
    def warnings(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "warning"]


def run_checklist(session: Session, variant_id: int) -> ChecklistResult:
    """Run all publication readiness checks on a variant."""
    result = ChecklistResult(variant_id=variant_id)

    variant = session.get(Variant, variant_id)
    if not variant:
        result.checks.append(CheckResult("Variant exists", False, f"Variant #{variant_id} not found"))
        return result

    result.checks.append(CheckResult("Variant exists", True, f"#{variant_id}: {variant.title}"))

    # Title checks
    _check_title(variant, result)

    # Interior PDF
    _check_interior(variant, result)

    # Cover
    _check_cover(variant, result)

    # Keywords
    _check_keywords(variant, result)

    # Description
    _check_description(variant, result)

    # Page count
    _check_page_count(variant, result)

    return result


def _check_title(variant: Variant, result: ChecklistResult) -> None:
    title = variant.title or ""
    if not title:
        result.checks.append(CheckResult("Title", False, "Title is empty"))
        return

    if len(title) > 200:
        result.checks.append(CheckResult("Title length", False, f"Title too long ({len(title)} chars, max 200)", "error"))
    else:
        result.checks.append(CheckResult("Title", True, f"'{title[:50]}...' ({len(title)} chars)"))

    if variant.subtitle and len(variant.subtitle) > 200:
        result.checks.append(CheckResult("Subtitle length", False, f"Subtitle too long ({len(variant.subtitle)} chars)", "warning"))


def _check_interior(variant: Variant, result: ChecklistResult) -> None:
    from libro.common.pdf_validation import validate_interior

    if not variant.interior_pdf_path:
        result.checks.append(CheckResult("Interior PDF", False, "No interior PDF generated"))
        return

    path = Path(variant.interior_pdf_path)
    vr = validate_interior(path, variant.trim_size, variant.page_count)

    if not vr.valid:
        for err in vr.errors:
            result.checks.append(CheckResult("Interior PDF", False, err))
    else:
        size_mb = path.stat().st_size / (1024 * 1024)
        result.checks.append(CheckResult(
            "Interior PDF", True,
            f"Valid ({vr.page_count} pages, {size_mb:.1f} MB)",
        ))
    for warn in vr.warnings:
        result.checks.append(CheckResult("Interior PDF", False, warn, "warning"))


def _check_cover(variant: Variant, result: ChecklistResult) -> None:
    from libro.common.pdf_validation import validate_cover

    if not variant.cover_pdf_path:
        result.checks.append(CheckResult("Cover", False, "No cover generated"))
        return

    path = Path(variant.cover_pdf_path)
    vr = validate_cover(path, variant.trim_size, variant.page_count)

    if not vr.valid:
        for err in vr.errors:
            result.checks.append(CheckResult("Cover", False, err))
    else:
        size_mb = path.stat().st_size / (1024 * 1024)
        result.checks.append(CheckResult(
            "Cover", True,
            f"Valid ({vr.width_pts:.0f}x{vr.height_pts:.0f} pts, {size_mb:.2f} MB)",
        ))
    for warn in vr.warnings:
        result.checks.append(CheckResult("Cover", False, warn, "warning"))


def _check_keywords(variant: Variant, result: ChecklistResult) -> None:
    if not variant.keywords:
        result.checks.append(CheckResult("Keywords", False, "No keywords set", "warning"))
        return

    kw_list = [k.strip() for k in variant.keywords.split(",")]
    if len(kw_list) > 7:
        result.checks.append(CheckResult("Keywords", False, f"Too many keywords ({len(kw_list)}, max 7)", "warning"))
    else:
        result.checks.append(CheckResult("Keywords", True, f"{len(kw_list)} keywords set"))

    # Check individual keyword length
    for kw in kw_list:
        if len(kw) > 50:
            result.checks.append(CheckResult("Keyword length", False, f"'{kw[:30]}...' too long ({len(kw)} chars, max 50)", "warning"))


def _check_description(variant: Variant, result: ChecklistResult) -> None:
    desc = variant.description or ""
    if not desc:
        result.checks.append(CheckResult("Description", False, "No description set", "warning"))
    elif len(desc) > 4000:
        result.checks.append(CheckResult("Description", False, f"Too long ({len(desc)} chars, max 4000)", "warning"))
    else:
        result.checks.append(CheckResult("Description", True, f"{len(desc)} chars"))


def _check_page_count(variant: Variant, result: ChecklistResult) -> None:
    if variant.page_count < 24:
        result.checks.append(CheckResult("Page count", False, f"Too few pages ({variant.page_count}, min 24)"))
    elif variant.page_count > 828:
        result.checks.append(CheckResult("Page count", False, f"Too many pages ({variant.page_count}, max 828)"))
    else:
        result.checks.append(CheckResult("Page count", True, f"{variant.page_count} pages"))


# ---------------------------------------------------------------------------
# KDP 5.4.8 Compliance Checks
# ---------------------------------------------------------------------------

# Trademarked brands — using these in titles is the #1 trigger for account action
TRADEMARK_TERMS = [
    "disney", "marvel", "pokemon", "pikachu", "harry potter", "hogwarts",
    "barbie", "star wars", "jedi", "sith", "nfl", "nba", "fifa", "mlb",
    "nhl", "super bowl", "world cup", "olympics", "olympic", "nintendo",
    "zelda", "mario bros", "minecraft", "roblox", "fortnite", "lego",
    "peppa pig", "paw patrol", "cocomelon", "bluey", "sesame street",
    "elmo", "spongebob", "dora", "frozen", "moana", "encanto",
    "coca-cola", "coca cola", "nike", "adidas", "supreme", "gucci",
    "louis vuitton", "chanel", "tesla", "apple", "iphone", "ipad",
    "google", "facebook", "instagram", "tiktok", "snapchat", "twitter",
    "youtube", "netflix", "amazon", "kindle", "alexa",
    "hello kitty", "sanrio", "pusheen", "care bears",
    "dc comics", "batman", "superman", "wonder woman", "spiderman",
    "spider-man", "avengers", "transformers", "power rangers",
    "winnie the pooh", "mickey mouse", "minnie mouse",
]

# Quotes with known attribution — using without credit may trigger rights claims
KNOWN_ATTRIBUTED_QUOTES = {
    "be the change you wish to see": "Mahatma Gandhi (common misattribution)",
    "the only way to do great work is to love": "Steve Jobs",
    "in the middle of difficulty lies opportunity": "Albert Einstein",
    "it does not matter how slowly you go": "Confucius",
    "the future belongs to those who believe": "Eleanor Roosevelt",
    "life is what happens when you": "John Lennon",
    "to be yourself in a world": "Oscar Wilde (disputed)",
    "the greatest glory in living": "Nelson Mandela (common misattribution)",
    "if you look at what you have in life": "Oprah Winfrey",
    "the way to get started is to quit talking": "Walt Disney",
    "it is during our darkest moments": "Aristotle (common misattribution)",
    "spread love everywhere you go": "Mother Teresa",
    "do one thing every day that scares you": "Eleanor Roosevelt (disputed)",
    "happiness is not something ready made": "Dalai Lama",
    "you miss 100% of the shots you don": "Wayne Gretzky",
}


def run_compliance_checklist(session: Session, variant_id: int) -> ChecklistResult:
    """Run KDP 5.4.8 compliance checks (superset of standard checklist).

    Includes trademark detection, quote attribution, catalog-wide similarity,
    and publishing velocity checks.
    """
    result = run_checklist(session, variant_id)

    variant = session.get(Variant, variant_id)
    if not variant:
        return result

    _check_trademark_title(variant, result)
    _check_quote_copyright(variant, result)
    _check_catalog_similarity_compliance(session, variant, result)
    _check_publishing_velocity(session, result)

    return result


def _check_trademark_title(variant: Variant, result: ChecklistResult) -> None:
    """Check title and subtitle for trademarked terms (5.4.8 rights violation risk)."""
    text = f"{variant.title or ''} {variant.subtitle or ''}".lower()

    found = []
    for term in TRADEMARK_TERMS:
        if term in text:
            found.append(term)

    if found:
        result.checks.append(CheckResult(
            "Trademark check",
            False,
            f"BLOCKED: Title contains trademarked terms: {', '.join(found)}. "
            "KDP 5.4.8 — third-party rights claim risk, royalties may be withheld.",
            "error",
        ))
    else:
        result.checks.append(CheckResult("Trademark check", True, "No trademarked terms detected"))


def _check_quote_copyright(variant: Variant, result: ChecklistResult) -> None:
    """Check if the variant's interior may include copyrighted quotes."""
    # Only relevant for custom templates that embed quotes (gratitude journals)
    if variant.interior_type != "custom":
        result.checks.append(CheckResult("Quote attribution", True, "N/A — no embedded quotes"))
        return

    # Check description and keywords for quote-related content hints
    text = f"{variant.title or ''} {variant.description or ''}".lower()

    flagged = []
    for quote_fragment, attribution in KNOWN_ATTRIBUTED_QUOTES.items():
        if quote_fragment in text:
            flagged.append(f"'{quote_fragment}...' — {attribution}")

    if flagged:
        result.checks.append(CheckResult(
            "Quote attribution",
            False,
            f"Quotes may require attribution: {'; '.join(flagged)}. "
            "Review interior for copyrighted content before publishing.",
            "warning",
        ))
    else:
        result.checks.append(CheckResult("Quote attribution", True, "No flagged quotes detected"))


def _check_catalog_similarity_compliance(
    session: Session, variant: Variant, result: ChecklistResult
) -> None:
    """Cross-catalog similarity check (5.4.8 spam/duplicate content risk)."""
    from libro.common.similarity import check_catalog_similarity
    from libro.config import get_settings

    settings = get_settings()
    warnings = check_catalog_similarity(
        session,
        variant.title,
        threshold=settings.compliance_similarity_threshold,
        max_similar=settings.compliance_max_similar_catalog,
        exclude_variant_id=variant.id,
    )

    if warnings:
        # First warning is the SPAM RISK summary if threshold exceeded
        is_blocked = any("SPAM RISK" in w for w in warnings)
        result.checks.append(CheckResult(
            "Catalog similarity",
            False,
            warnings[0],
            "error" if is_blocked else "warning",
        ))
    else:
        result.checks.append(CheckResult(
            "Catalog similarity", True, "No cross-catalog duplication detected"
        ))


def _check_publishing_velocity(session: Session, result: ChecklistResult) -> None:
    """Check publishing velocity for spam pattern detection (5.4.8 fraud risk)."""
    from libro.models.publication import Publication
    from libro.config import get_settings

    settings = get_settings()
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

    alerts = []
    if count_7d > settings.compliance_velocity_7d_max:
        alerts.append(f"{count_7d} books in 7 days (max {settings.compliance_velocity_7d_max})")
    if count_30d > settings.compliance_velocity_30d_max:
        alerts.append(f"{count_30d} books in 30 days (max {settings.compliance_velocity_30d_max})")

    if alerts:
        result.checks.append(CheckResult(
            "Publishing velocity",
            False,
            f"High velocity detected: {'; '.join(alerts)}. "
            "KDP 5.4.8 — may trigger deceptive activity flag.",
            "warning",
        ))
    else:
        result.checks.append(CheckResult(
            "Publishing velocity", True,
            f"Normal velocity: {count_7d}/7d, {count_30d}/30d",
        ))
