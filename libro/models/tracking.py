from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libro.database import Base

if TYPE_CHECKING:
    from libro.models.publication import Publication


class TrackingSnapshot(Base):
    __tablename__ = "tracking_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"))
    bsr: Mapped[int | None] = mapped_column(default=None)
    reviews_count: Mapped[int] = mapped_column(default=0)
    rating: Mapped[float | None] = mapped_column(default=None)
    estimated_daily_sales: Mapped[float | None] = mapped_column(default=None)
    estimated_monthly_revenue: Mapped[float | None] = mapped_column(default=None)
    captured_at: Mapped[datetime] = mapped_column(default=func.now())

    publication: Mapped["Publication"] = relationship(back_populates="snapshots")
