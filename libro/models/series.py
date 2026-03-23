"""Series model — groups related variants into product lines."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libro.database import Base

if TYPE_CHECKING:
    from libro.models.brand import Brand
    from libro.models.niche import Niche
    from libro.models.variant import Variant


class Series(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    base_niche_id: Mapped[int] = mapped_column(ForeignKey("niches.id"))
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), default=None)
    # JSON: stores aesthetic config (colors, font, style) for consistency across the line
    style_aesthetic: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    niche: Mapped["Niche"] = relationship()
    brand: Mapped["Brand | None"] = relationship()
    variants: Mapped[list["Variant"]] = relationship(back_populates="series")
