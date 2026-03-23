"""Publication packager — bundles everything for KDP upload."""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from libro.config import get_settings
from libro.models.variant import Variant
from libro.publication.checklist import run_checklist
from libro.publication.metadata import generate_metadata

log = logging.getLogger(__name__)


@dataclass
class PackageResult:
    """Result of packaging a variant for KDP."""
    output_dir: Path
    interior_path: Path | None
    cover_path: Path | None
    metadata_path: Path
    checklist_passed: bool
    errors: list[str]


def package_variant(
    session: Session,
    variant_id: int,
    author: str = "",
) -> PackageResult:
    """Bundle a variant into a KDP-ready package.

    Creates a directory with:
    - manuscript.pdf (interior)
    - cover.png
    - metadata.txt (all KDP fields)
    - checklist.txt (validation results)

    Args:
        session: DB session.
        variant_id: Variant to package.
        author: Author/brand name for metadata.

    Returns:
        PackageResult with paths and validation status.
    """
    settings = get_settings()
    variant = session.get(Variant, variant_id)
    if not variant:
        raise ValueError(f"Variant #{variant_id} not found")

    # Get author from brand if not provided
    if not author and variant.brand:
        author = variant.brand.name

    # Output directory
    output_dir = settings.output_dir / f"package_{variant_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

    # Run checklist
    checklist = run_checklist(session, variant_id)
    checklist_path = output_dir / "checklist.txt"
    _write_checklist(checklist_path, checklist)

    # Copy interior PDF
    interior_dest = None
    if variant.interior_pdf_path:
        src = Path(variant.interior_pdf_path)
        if src.exists():
            interior_dest = output_dir / "manuscript.pdf"
            shutil.copy2(src, interior_dest)
        else:
            errors.append(f"Interior PDF not found: {src}")
    else:
        errors.append("No interior PDF generated")

    # Copy cover
    cover_dest = None
    if variant.cover_pdf_path:
        src = Path(variant.cover_pdf_path)
        if src.exists():
            suffix = src.suffix
            cover_dest = output_dir / f"cover{suffix}"
            shutil.copy2(src, cover_dest)
        else:
            errors.append(f"Cover not found: {src}")
    else:
        errors.append("No cover generated")

    # Generate metadata
    metadata = generate_metadata(variant, author=author)
    metadata_path = output_dir / "metadata.txt"
    metadata_path.write_text(metadata.to_text())

    # Write upload instructions
    _write_instructions(output_dir, variant, metadata)

    return PackageResult(
        output_dir=output_dir,
        interior_path=interior_dest,
        cover_path=cover_dest,
        metadata_path=metadata_path,
        checklist_passed=checklist.passed,
        errors=errors,
    )


def _write_checklist(path: Path, checklist) -> None:
    """Write checklist results to a text file."""
    lines = ["PUBLICATION CHECKLIST", "=" * 40, ""]
    for check in checklist.checks:
        icon = "PASS" if check.passed else "FAIL"
        lines.append(f"[{icon}] {check.name}: {check.message}")
    lines.append("")
    lines.append(f"Result: {'READY' if checklist.passed else 'NOT READY'}")
    path.write_text("\n".join(lines))


def _write_instructions(output_dir: Path, variant: Variant, metadata) -> None:
    """Write step-by-step upload instructions."""
    instructions = f"""\
KDP UPLOAD INSTRUCTIONS
=======================

1. Go to https://kdp.amazon.com
2. Click "Create New Title" → "Paperback"

STEP 1 - Book Details:
  - Language: {metadata.language}
  - Title: {metadata.title}
  - Subtitle: {metadata.subtitle}
  - Author: {metadata.author}
  - Description: (copy from metadata.txt)
  - Keywords: (copy each from metadata.txt, 1 per box)
  - Categories: {metadata.categories[0]}
                {metadata.categories[1] if len(metadata.categories) > 1 else ''}

STEP 2 - Content:
  - ISBN: Get free KDP ISBN
  - Publication date: Leave blank (auto)
  - Interior: Black & white, {metadata.trim_size.replace('x', '" x ')}",
              {variant.page_count} pages
  - Upload manuscript: manuscript.pdf
  - Upload cover: cover.png

STEP 3 - Pricing:
  - Marketplace: Amazon.com
  - Suggested price: {metadata.price_suggestion}
  - Select all available marketplaces

Files in this package:
  - manuscript.pdf  → Upload as manuscript
  - cover.png       → Upload as cover
  - metadata.txt    → Reference for filling forms
  - checklist.txt   → Validation results
"""
    (output_dir / "INSTRUCTIONS.txt").write_text(instructions)
