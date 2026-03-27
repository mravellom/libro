"""Publication monitor — captures periodic BSR/reviews snapshots."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from libro.common.amazon import estimate_daily_sales, estimate_monthly_revenue
from libro.intelligence.scraper import AmazonScraper
from libro.models.publication import Publication
from libro.models.tracking import TrackingSnapshot

log = logging.getLogger(__name__)


async def _capture_snapshot_async(
    scraper: AmazonScraper,
    publication: Publication,
    session: Session,
) -> TrackingSnapshot | None:
    """Scrape current data for a published book and create a snapshot."""
    if not publication.asin:
        log.warning(f"Publication #{publication.id} has no ASIN, skipping")
        return None

    detail = await scraper.scrape_product_page(publication.asin)
    if detail is None:
        log.warning(f"Could not scrape ASIN {publication.asin}")
        return None

    # Calculate estimated sales
    daily_sales = None
    monthly_rev = None
    if detail.bsr is not None:
        daily_sales = estimate_daily_sales(detail.bsr)
        price = detail.price or 0
        if price > 0:
            monthly_rev = estimate_monthly_revenue(detail.bsr, price)

    snapshot = TrackingSnapshot(
        publication_id=publication.id,
        bsr=detail.bsr,
        reviews_count=detail.reviews_count,
        rating=detail.rating,
        estimated_daily_sales=daily_sales,
        estimated_monthly_revenue=monthly_rev,
    )
    session.add(snapshot)
    session.flush()

    log.info(
        f"Snapshot for ASIN {publication.asin}: "
        f"BSR={detail.bsr}, reviews={detail.reviews_count}, "
        f"est_daily_sales={daily_sales:.1f}" if daily_sales else ""
    )
    return snapshot


def capture_snapshot(
    session: Session,
    publication_id: int,
    headless: bool = True,
) -> TrackingSnapshot | None:
    """Capture a single snapshot for a publication."""
    pub = session.get(Publication, publication_id)
    if not pub:
        log.error(f"Publication #{publication_id} not found")
        return None

    async def _run():
        scraper = AmazonScraper(headless=headless)
        try:
            return await _capture_snapshot_async(scraper, pub, session)
        finally:
            await scraper.close()

    return asyncio.run(_run())


def capture_all_active(
    session: Session,
    headless: bool = True,
) -> list[TrackingSnapshot]:
    """Capture snapshots for all publications in evaluation period."""
    now = datetime.now(UTC)

    active_pubs = (
        session.query(Publication)
        .filter(
            Publication.asin.isnot(None),
            Publication.decision.is_(None),
            Publication.evaluation_end >= now,
        )
        .all()
    )

    if not active_pubs:
        log.info("No active publications to track")
        return []

    log.info(f"Tracking {len(active_pubs)} active publications")

    async def _run():
        scraper = AmazonScraper(headless=headless)
        snapshots = []
        try:
            for pub in active_pubs:
                snapshot = await _capture_snapshot_async(scraper, pub, session)
                if snapshot:
                    snapshots.append(snapshot)
        finally:
            await scraper.close()
        return snapshots

    return asyncio.run(_run())
