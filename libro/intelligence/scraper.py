"""Playwright-based Amazon scraper for KDP market intelligence."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser

from libro.common.rate_limiter import RateLimiter
from libro.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class RawProduct:
    """Lightweight product data extracted from search results."""
    asin: str
    title: str
    price: float | None = None
    rating: float | None = None
    reviews_count: int = 0
    url: str = ""


@dataclass
class ProductDetail:
    """Full product details from individual product page."""
    asin: str
    title: str
    price: float | None = None
    rating: float | None = None
    reviews_count: int = 0
    bsr: int | None = None
    bsr_category: str | None = None
    page_count: int | None = None
    dimensions: str | None = None
    author: str | None = None
    publisher: str | None = None


class AmazonScraper:
    """Scrapes Amazon search results and product pages for KDP research."""

    def __init__(self, rate_limiter: RateLimiter | None = None, headless: bool = True):
        settings = get_settings()
        self._headless = headless
        self._rate_limiter = rate_limiter or RateLimiter(
            min_delay=settings.scraper_delay_min,
            max_delay=settings.scraper_delay_max,
        )
        self._marketplace = settings.amazon_marketplace
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def _ensure_browser(self) -> Page:
        if self._page is None:
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(headless=self._headless)
            context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            self._page = await context.new_page()
        return self._page

    async def search_keyword(
        self, keyword: str, max_pages: int = 3
    ) -> list[RawProduct]:
        """Search Amazon for keyword, extract products from result pages."""
        page = await self._ensure_browser()
        all_products: list[RawProduct] = []

        for page_num in range(1, max_pages + 1):
            await self._rate_limiter.wait()

            keyword_encoded = keyword.replace(" ", "+")
            url = (
                f"https://www.amazon.{self._marketplace}/s"
                f"?k={keyword_encoded}&i=stripbooks-intl-ship&page={page_num}"
            )

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait for either search results or captcha
                await page.wait_for_selector(
                    "div[data-component-type='s-search-result'], div.s-main-slot, #captchacharacters",
                    timeout=15000,
                )
            except Exception as e:
                log.warning(f"Page {page_num} failed to load: {e}")
                break

            # Check for captcha
            captcha = await page.query_selector("#captchacharacters")
            if captcha:
                log.warning("Amazon CAPTCHA detected — stopping scrape")
                break

            products = await self._parse_search_results(page)
            log.info(f"Page {page_num}: found {len(products)} products")
            if not products:
                # Try taking a screenshot for debugging
                try:
                    await page.screenshot(path="/tmp/libro_debug_search.png")
                    log.info("Debug screenshot saved to /tmp/libro_debug_search.png")
                except Exception:
                    pass
                break
            all_products.extend(products)

        return all_products

    async def _parse_search_results(self, page: Page) -> list[RawProduct]:
        """Extract product data from a search results page."""
        products: list[RawProduct] = []

        items = await page.query_selector_all(
            "div[data-component-type='s-search-result']"
        )

        for item in items:
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

                # Title — try multiple selectors
                title = ""
                for sel in ["h2 a span", "h2 span", "h2"]:
                    title_el = await item.query_selector(sel)
                    if title_el:
                        title = (await title_el.inner_text()).strip()
                        if title:
                            break
                if not title:
                    continue

                # Price
                price = await self._extract_price(item)

                # Rating
                rating = None
                rating_el = await item.query_selector("span.a-icon-alt")
                if rating_el:
                    rating_text = await rating_el.inner_text()
                    match = re.search(r"([\d.]+)\s+out of", rating_text)
                    if match:
                        rating = float(match.group(1))

                # Reviews count
                reviews_count = 0
                for sel in [
                    "span.s-underline-text",
                    "span.a-size-base.s-underline-text",
                    "a[href*='customerReviews'] span",
                ]:
                    reviews_el = await item.query_selector(sel)
                    if reviews_el:
                        reviews_text = await reviews_el.inner_text()
                        reviews_text = reviews_text.replace(",", "").replace(".", "")
                        match = re.search(r"(\d+)", reviews_text)
                        if match:
                            reviews_count = int(match.group(1))
                            break

                url = f"https://www.amazon.{self._marketplace}/dp/{asin}"

                products.append(
                    RawProduct(
                        asin=asin,
                        title=title,
                        price=price,
                        rating=rating,
                        reviews_count=reviews_count,
                        url=url,
                    )
                )
            except Exception as e:
                log.debug(f"Failed to parse item: {e}")
                continue

        return products

    async def _extract_price(self, item) -> float | None:
        """Extract price from a search result item."""
        for sel in [
            "span.a-price span.a-offscreen",
            "span.a-price > span.a-offscreen",
            ".a-price .a-offscreen",
        ]:
            price_el = await item.query_selector(sel)
            if price_el:
                price_text = await price_el.inner_text()
                # Remove currency symbols, keep digits and decimal separators
                cleaned = re.sub(r"[^\d.,]", "", price_text)
                # Handle formats: "6,077" (CLP), "12.99" (USD), "1,234.56"
                if "." in cleaned and "," in cleaned:
                    cleaned = cleaned.replace(",", "")
                elif "," in cleaned and len(cleaned.split(",")[-1]) == 2:
                    cleaned = cleaned.replace(",", ".")
                elif "," in cleaned:
                    cleaned = cleaned.replace(",", "")
                try:
                    return float(cleaned)
                except ValueError:
                    continue
        return None

    async def scrape_product_page(self, asin: str) -> ProductDetail | None:
        """Scrape full details from a single product page."""
        page = await self._ensure_browser()
        await self._rate_limiter.wait()

        url = f"https://www.amazon.{self._marketplace}/dp/{asin}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            return None

        detail = ProductDetail(asin=asin, title="")

        # Title
        title_el = await page.query_selector("#productTitle")
        if title_el:
            detail.title = (await title_el.inner_text()).strip()

        # Price
        price_el = await page.query_selector(
            "#price, span.a-price > span.a-offscreen, #kindle-price"
        )
        if price_el:
            price_text = await price_el.inner_text()
            match = re.search(r"[\d,.]+", price_text.replace(",", ""))
            if match:
                detail.price = float(match.group())

        # Rating
        rating_el = await page.query_selector("#acrPopover span.a-icon-alt")
        if rating_el:
            rating_text = await rating_el.inner_text()
            match = re.search(r"([\d.]+)", rating_text)
            if match:
                detail.rating = float(match.group(1))

        # Reviews count
        reviews_el = await page.query_selector("#acrCustomerReviewText")
        if reviews_el:
            reviews_text = await reviews_el.inner_text()
            match = re.search(r"([\d,]+)", reviews_text.replace(",", ""))
            if match:
                detail.reviews_count = int(match.group(1))

        # BSR — try multiple locations
        detail.bsr, detail.bsr_category = await self._extract_bsr(page)

        # Product details (page count, dimensions, author, publisher)
        await self._extract_product_details(page, detail)

        return detail

    async def _extract_bsr(self, page: Page) -> tuple[int | None, str | None]:
        """Extract BSR from product page. Tries multiple DOM locations."""
        selectors = [
            "#productDetails_detailBullets_sections1",
            "#detailBulletsWrapper_feature_div",
            "#prodDetails",
        ]

        for selector in selectors:
            el = await page.query_selector(selector)
            if not el:
                continue
            text = await el.inner_text()
            # Pattern: "#1,234 in Books" or "#1,234 in Kindle Store"
            match = re.search(
                r"#([\d,]+)\s+in\s+([^\n(]+)", text
            )
            if match:
                bsr = int(match.group(1).replace(",", ""))
                category = match.group(2).strip()
                return bsr, category

        return None, None

    async def _extract_product_details(
        self, page: Page, detail: ProductDetail
    ) -> None:
        """Extract page count, dimensions, author, publisher from detail sections."""
        # Author
        author_el = await page.query_selector(
            "#bylineInfo .author a, .contributorNameID"
        )
        if author_el:
            detail.author = (await author_el.inner_text()).strip()

        # Try to get details from the product information table
        detail_section = await page.query_selector(
            "#productDetails_detailBullets_sections1, #detailBulletsWrapper_feature_div, #prodDetails"
        )
        if not detail_section:
            return

        text = await detail_section.inner_text()

        # Page count
        match = re.search(r"(\d+)\s+pages", text)
        if match:
            detail.page_count = int(match.group(1))

        # Dimensions
        match = re.search(r"([\d.]+\s*x\s*[\d.]+\s*x?\s*[\d.]*)\s*(?:inches|cm)", text)
        if match:
            detail.dimensions = match.group(1).strip()

        # Publisher
        match = re.search(r"Publisher\s*[:\s]+([^\n;]+)", text)
        if match:
            detail.publisher = match.group(1).strip()

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
