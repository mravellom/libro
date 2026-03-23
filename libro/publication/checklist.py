"""Publication readiness checklist — validates everything before KDP upload."""

import logging
from dataclasses import dataclass, field
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
    if not variant.interior_pdf_path:
        result.checks.append(CheckResult("Interior PDF", False, "No interior PDF generated"))
        return

    path = Path(variant.interior_pdf_path)
    if not path.exists():
        result.checks.append(CheckResult("Interior PDF", False, f"File not found: {path}"))
        return

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 650:
        result.checks.append(CheckResult("Interior size", False, f"File too large ({size_mb:.1f} MB, max 650 MB)"))
    else:
        result.checks.append(CheckResult("Interior PDF", True, f"Exists ({size_mb:.1f} MB)"))


def _check_cover(variant: Variant, result: ChecklistResult) -> None:
    if not variant.cover_pdf_path:
        result.checks.append(CheckResult("Cover", False, "No cover generated"))
        return

    path = Path(variant.cover_pdf_path)
    if not path.exists():
        result.checks.append(CheckResult("Cover", False, f"File not found: {path}"))
        return

    result.checks.append(CheckResult("Cover", True, f"Exists: {path.name}"))


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
