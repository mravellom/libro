from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libro.database import Base

if TYPE_CHECKING:
    from libro.models.product import Product
    from libro.models.variant import Variant


class Niche(Base):
    __tablename__ = "niches"
    __table_args__ = (
        UniqueConstraint("keyword", "marketplace", name="uq_niche_keyword_marketplace"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(255))

    # Scoring (weighted formula)
    demand_score: Mapped[float] = mapped_column(default=0.0)
    competition_score: Mapped[float] = mapped_column(default=0.0)
    trend_score: Mapped[float] = mapped_column(default=0.0)
    stability_score: Mapped[float] = mapped_column(default=0.0)
    price_score: Mapped[float] = mapped_column(default=0.0)
    opportunity_score: Mapped[float] = mapped_column(default=0.0)

    # Aggregated market data
    avg_bsr: Mapped[float | None] = mapped_column(default=None)
    avg_price: Mapped[float | None] = mapped_column(default=None)
    avg_reviews: Mapped[float | None] = mapped_column(default=None)
    avg_review_velocity: Mapped[float | None] = mapped_column(default=None)
    top_products_count: Mapped[int] = mapped_column(default=0)

    # Niche classification: evergreen | trending
    niche_type: Mapped[str] = mapped_column(String(20), default="evergreen")
    # Marketplace: com | de | co.jp | co.uk | etc.
    marketplace: Mapped[str] = mapped_column(String(20), default="com")

    # Status: discovered | scored | generating | testing | scaled | killed
    status: Mapped[str] = mapped_column(String(20), default="discovered")
    notes: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(default=func.now())
    scored_at: Mapped[datetime | None] = mapped_column(default=None)

    products: Mapped[list["Product"]] = relationship(back_populates="niche")
    variants: Mapped[list["Variant"]] = relationship(back_populates="niche")
