"""Discovery pipeline — orchestrates keyword → scrape → store → enrich."""

import asyncio
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from libro.common.rate_limiter import RateLimiter
from libro.intelligence.scraper import AmazonScraper, RawProduct, ProductDetail
from libro.models.niche import Niche
from libro.models.product import Product


@dataclass
class DiscoveryResult:
    """Detached result from discovery pipeline (safe to use after session close)."""
    niche_id: int
    keyword: str
    products_count: int
    avg_bsr: float | None
    avg_price: float | None
    avg_reviews: float | None


class DiscoveryPipeline:
    """Discovers niches by scraping Amazon and storing results."""

    def __init__(self, session: Session, headless: bool = True):
        self._session = session
        self._headless = headless

    async def discover(
        self, keyword: str, max_pages: int = 3, enrich_details: bool = True
    ) -> Niche:
        """Full pipeline: search → store products → optionally scrape detail pages.

        Args:
            keyword: Search term for Amazon.
            max_pages: Number of search result pages to scrape.
            enrich_details: If True, also scrape individual product pages for BSR/details.

        Returns:
            The created or updated Niche with associated Products.
        """
        # Get or create niche
        niche = (
            self._session.query(Niche)
            .filter(Niche.keyword == keyword)
            .first()
        )
        if niche is None:
            niche = Niche(keyword=keyword)
            self._session.add(niche)
            self._session.flush()

        scraper = AmazonScraper(headless=self._headless)
        try:
            # Step 1: Search
            raw_products = await scraper.search_keyword(keyword, max_pages=max_pages)

            # Step 2: Store basic product data
            stored = self._store_products(niche, raw_products)

            # Step 3: Optionally enrich with detail page data
            if enrich_details and stored:
                await self._enrich_product_details(scraper, stored)

            # Step 4: Update niche aggregates
            self._update_niche_aggregates(niche)

        finally:
            await scraper.close()

        self._session.commit()
        return niche

    def _store_products(
        self, niche: Niche, raw_products: list[RawProduct]
    ) -> list[Product]:
        """Store or update products from search results."""
        stored: list[Product] = []

        for raw in raw_products:
            existing = (
                self._session.query(Product)
                .filter(Product.asin == raw.asin)
                .first()
            )

            if existing:
                existing.title = raw.title
                existing.price = raw.price
                existing.rating = raw.rating
                existing.reviews_count = raw.reviews_count
                existing.scraped_at = datetime.utcnow()
                stored.append(existing)
            else:
                product = Product(
                    asin=raw.asin,
                    niche_id=niche.id,
                    title=raw.title,
                    price=raw.price,
                    rating=raw.rating,
                    reviews_count=raw.reviews_count,
                )
                self._session.add(product)
                stored.append(product)

        self._session.flush()
        return stored

    async def _enrich_product_details(
        self, scraper: AmazonScraper, products: list[Product]
    ) -> None:
        """Scrape individual product pages for BSR, page count, etc."""
        for product in products:
            detail = await scraper.scrape_product_page(product.asin)
            if detail is None:
                continue

            if detail.bsr is not None:
                product.bsr = detail.bsr
            if detail.page_count is not None:
                product.page_count = detail.page_count
            if detail.dimensions is not None:
                product.dimensions = detail.dimensions
            if detail.author is not None:
                product.author = detail.author
            if detail.publisher is not None:
                product.publisher = detail.publisher

        self._session.flush()

    def _update_niche_aggregates(self, niche: Niche) -> None:
        """Recalculate niche aggregate stats from its products."""
        products = (
            self._session.query(Product)
            .filter(Product.niche_id == niche.id)
            .all()
        )

        if not products:
            return

        niche.top_products_count = len(products)

        # Average BSR (only products that have it)
        bsrs = [p.bsr for p in products if p.bsr is not None]
        niche.avg_bsr = sum(bsrs) / len(bsrs) if bsrs else None

        # Average price
        prices = [p.price for p in products if p.price is not None]
        niche.avg_price = sum(prices) / len(prices) if prices else None

        # Average reviews
        reviews = [p.reviews_count for p in products]
        niche.avg_reviews = sum(reviews) / len(reviews) if reviews else None

        self._session.flush()


def run_discovery(
    keyword: str,
    max_pages: int = 3,
    enrich_details: bool = True,
    headless: bool = True,
) -> DiscoveryResult:
    """Synchronous wrapper for the discovery pipeline."""
    from libro.database import get_session_factory

    factory = get_session_factory()
    session = factory()

    try:
        pipeline = DiscoveryPipeline(session, headless=headless)
        niche = asyncio.run(
            pipeline.discover(keyword, max_pages, enrich_details)
        )
        session.commit()
        # Extract data before closing session
        result = DiscoveryResult(
            niche_id=niche.id,
            keyword=niche.keyword,
            products_count=niche.top_products_count,
            avg_bsr=niche.avg_bsr,
            avg_price=niche.avg_price,
            avg_reviews=niche.avg_reviews,
        )
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
