"""Integration tests — full pipeline: niche → variants → interior → cover → checklist → package."""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libro.database import Base
import libro.models  # noqa: F401


@pytest.fixture
def integration_session(tmp_path, monkeypatch):
    """In-memory DB session with output_dir pointed to tmp."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Point output_dir to temp so generated files don't pollute the repo
    from libro.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "output_dir", tmp_path / "output")

    yield session
    session.close()


@pytest.fixture
def niche_with_products(integration_session):
    """Create a scored niche with competitor products."""
    from libro.models import Niche, Product

    niche = Niche(
        keyword="gratitude journal",
        category="Self-Help",
        opportunity_score=0.75,
        demand_score=0.8,
        competition_score=0.7,
        avg_bsr=60000,
        avg_price=8.99,
        avg_reviews=30,
        status="scored",
    )
    integration_session.add(niche)
    integration_session.flush()

    products = [
        Product(asin="B0INT0001", niche_id=niche.id, title="Gratitude Journal for Women",
                bsr=45000, price=7.99, reviews_count=23, page_count=120),
        Product(asin="B0INT0002", niche_id=niche.id, title="Daily Gratitude Workbook",
                bsr=82000, price=9.99, reviews_count=56, page_count=150),
        Product(asin="B0INT0003", niche_id=niche.id, title="5 Minute Gratitude Journal",
                bsr=35000, price=6.99, reviews_count=8, page_count=100),
    ]
    integration_session.add_all(products)
    integration_session.commit()

    return niche


def test_generate_variants(integration_session, niche_with_products):
    """Generate variant records from a scored niche."""
    from libro.generation.variant_engine import generate_variants

    variants = generate_variants(integration_session, niche_with_products.id, count=2)
    assert len(variants) == 2
    for v in variants:
        assert v.title
        assert v.niche_id == niche_with_products.id
        assert v.status == "draft"
        assert v.trim_size
        assert v.page_count >= 24


def test_generate_interior_for_variant(integration_session, niche_with_products, tmp_path):
    """Generate interior PDF for a variant."""
    from libro.generation.variant_engine import generate_variants
    from libro.generation.interior import generate_interior

    variants = generate_variants(integration_session, niche_with_products.id, count=1)
    variant = variants[0]

    output_path = tmp_path / f"interior_{variant.id}.pdf"
    template = variant.interior_type or "lined"
    path = generate_interior(
        template_name=template,
        output_path=output_path,
        trim_size=variant.trim_size,
        page_count=variant.page_count,
        seed=variant.id,
    )

    assert path.exists()
    assert path.stat().st_size > 0

    # Update variant with path
    variant.interior_pdf_path = str(path)
    integration_session.commit()


def test_generate_cover_for_variant(integration_session, niche_with_products, tmp_path):
    """Generate cover PDF for a variant."""
    from libro.generation.variant_engine import generate_variants
    from libro.branding.cover import CoverGenerator

    variants = generate_variants(integration_session, niche_with_products.id, count=1)
    variant = variants[0]

    gen = CoverGenerator()
    cover_path = gen.generate(
        title=variant.title,
        subtitle=variant.subtitle or "",
        trim_size=variant.trim_size,
        page_count=variant.page_count,
        output_path=tmp_path / "cover.pdf",
        seed=variant.id,
    )

    assert cover_path.exists()
    assert cover_path.suffix == ".pdf"

    variant.cover_pdf_path = str(cover_path)
    integration_session.commit()


def test_full_pipeline(integration_session, niche_with_products, tmp_path):
    """End-to-end: variant → interior → cover → validate → checklist → package."""
    from libro.generation.variant_engine import generate_variants
    from libro.generation.interior import generate_interior
    from libro.branding.cover import CoverGenerator
    from libro.common.pdf_validation import validate_interior, validate_cover
    from libro.publication.checklist import run_checklist
    from libro.publication.packager import package_variant

    # Step 1: Generate variant
    variants = generate_variants(integration_session, niche_with_products.id, count=1)
    variant = variants[0]
    assert variant.title

    # Step 2: Generate interior
    interior_path = tmp_path / f"interior_{variant.id}.pdf"
    template = variant.interior_type or "lined"
    generate_interior(
        template_name=template,
        output_path=interior_path,
        trim_size=variant.trim_size,
        page_count=variant.page_count,
        seed=variant.id,
    )
    variant.interior_pdf_path = str(interior_path)

    # Step 3: Generate cover
    cover_path = CoverGenerator().generate(
        title=variant.title,
        subtitle=variant.subtitle or "",
        trim_size=variant.trim_size,
        page_count=variant.page_count,
        output_path=tmp_path / "cover.pdf",
        seed=variant.id,
    )
    variant.cover_pdf_path = str(cover_path)
    integration_session.commit()

    # Step 4: Validate PDFs
    iv = validate_interior(interior_path, variant.trim_size, variant.page_count)
    assert iv.valid, f"Interior invalid: {iv.errors}"

    cv = validate_cover(cover_path, variant.trim_size, variant.page_count)
    assert cv.valid, f"Cover invalid: {cv.errors}"

    # Step 5: Run checklist
    checklist = run_checklist(integration_session, variant.id)
    # Checklist may have warnings (missing keywords/description) but core checks pass
    core_errors = [c for c in checklist.checks
                   if not c.passed and c.severity == "error"
                   and c.name in ("Interior PDF", "Cover", "Variant exists")]
    assert not core_errors, f"Core checks failed: {core_errors}"

    # Step 6: Package
    result = package_variant(integration_session, variant.id)
    assert result.interior_path and result.interior_path.exists()
    assert result.cover_path and result.cover_path.exists()
    assert result.metadata_path.exists()
