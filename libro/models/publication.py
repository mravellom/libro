from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libro.database import Base

if TYPE_CHECKING:
    from libro.models.tracking import TrackingSnapshot
    from libro.models.variant import Variant


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), unique=True)
    asin: Mapped[str | None] = mapped_column(String(10), index=True)
    kdp_url: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime | None] = mapped_column(default=None)
    evaluation_start: Mapped[datetime | None] = mapped_column(default=None)
    evaluation_end: Mapped[datetime | None] = mapped_column(default=None)
    # Marketplace
    marketplace: Mapped[str] = mapped_column(String(20), default="com")
    # Impressions tracking (for auto-kill rule)
    impressions_detected: Mapped[bool] = mapped_column(default=False)
    auto_kill_date: Mapped[datetime | None] = mapped_column(default=None)

    # None | scale | iterate | kill
    decision: Mapped[str | None] = mapped_column(String(20))
    decided_at: Mapped[datetime | None] = mapped_column(default=None)

    variant: Mapped["Variant"] = relationship(back_populates="publication")
    snapshots: Mapped[list["TrackingSnapshot"]] = relationship(back_populates="publication")
