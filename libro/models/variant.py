from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libro.database import Base

if TYPE_CHECKING:
    from libro.models.brand import Brand
    from libro.models.niche import Niche
    from libro.models.publication import Publication
    from libro.models.series import Series


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    niche_id: Mapped[int] = mapped_column(ForeignKey("niches.id"))
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), default=None)
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[str | None] = mapped_column(Text)
    interior_type: Mapped[str] = mapped_column(String(50))  # lined | dotted | grid | custom
    trim_size: Mapped[str] = mapped_column(String(20))  # "6x9", "8.5x11"
    page_count: Mapped[int] = mapped_column(default=120)
    interior_pdf_path: Mapped[str | None] = mapped_column(String(500))
    cover_pdf_path: Mapped[str | None] = mapped_column(String(500))

    # Similarity guard: hash of title+interior for dedup
    content_fingerprint: Mapped[str | None] = mapped_column(String(64))

    # Series grouping (for product line generation)
    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"), default=None)
    series_name: Mapped[str | None] = mapped_column(String(255))

    # draft | ready | selected | published | rejected
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    niche: Mapped["Niche"] = relationship(back_populates="variants")
    brand: Mapped["Brand"] = relationship(back_populates="variants")
    publication: Mapped["Publication | None"] = relationship(back_populates="variant")
    series: Mapped["Series | None"] = relationship(back_populates="variants")
