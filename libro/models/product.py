from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libro.database import Base

if TYPE_CHECKING:
    from libro.models.niche import Niche


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    asin: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    niche_id: Mapped[int] = mapped_column(ForeignKey("niches.id"))
    title: Mapped[str] = mapped_column(String(500))
    bsr: Mapped[int | None] = mapped_column(default=None)
    price: Mapped[float | None] = mapped_column(default=None)
    reviews_count: Mapped[int] = mapped_column(default=0)
    rating: Mapped[float | None] = mapped_column(default=None)
    page_count: Mapped[int | None] = mapped_column(default=None)
    dimensions: Mapped[str | None] = mapped_column(String(50))
    author: Mapped[str | None] = mapped_column(String(255))
    publisher: Mapped[str | None] = mapped_column(String(255))

    # Keepa enrichment
    bsr_history_json: Mapped[str | None] = mapped_column(Text)
    bsr_30d_avg: Mapped[float | None] = mapped_column(default=None)
    bsr_90d_avg: Mapped[float | None] = mapped_column(default=None)
    # rising | stable | falling
    bsr_trend: Mapped[str | None] = mapped_column(String(20))
    review_velocity_30d: Mapped[float | None] = mapped_column(default=None)

    scraped_at: Mapped[datetime] = mapped_column(default=func.now())

    niche: Mapped["Niche"] = relationship(back_populates="products")
