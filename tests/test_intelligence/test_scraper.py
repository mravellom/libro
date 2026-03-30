"""Tests for AmazonScraper — focus on lifecycle (Playwright leak fix) and data parsing."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libro.intelligence.scraper import AmazonScraper, RawProduct, ProductDetail


class TestScraperLifecycle:
    """Tests for the Playwright instance leak fix."""

    @patch("libro.intelligence.scraper.get_settings")
    @patch("libro.intelligence.scraper.async_playwright")
    def test_close_stops_playwright_instance(self, mock_apw, mock_settings):
        """Closing the scraper must stop the Playwright instance to avoid leaks."""
        mock_settings.return_value = MagicMock(
            scraper_delay_min=0, scraper_delay_max=0, amazon_marketplace="com"
        )

        # Setup mock Playwright chain
        mock_pw_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_apw.return_value.start = AsyncMock(return_value=mock_pw_instance)
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        scraper = AmazonScraper()

        # Simulate opening and closing
        asyncio.run(scraper._ensure_browser())
        asyncio.run(scraper.close())

        mock_browser.close.assert_called_once()
        mock_pw_instance.stop.assert_called_once()

    @patch("libro.intelligence.scraper.get_settings")
    @patch("libro.intelligence.scraper.async_playwright")
    def test_close_without_open_is_safe(self, mock_apw, mock_settings):
        """Closing a scraper that was never opened should not raise."""
        mock_settings.return_value = MagicMock(
            scraper_delay_min=0, scraper_delay_max=0, amazon_marketplace="com"
        )
        scraper = AmazonScraper()
        # Should not raise
        asyncio.run(scraper.close())

    @patch("libro.intelligence.scraper.get_settings")
    @patch("libro.intelligence.scraper.async_playwright")
    def test_pw_attribute_initialized_none(self, mock_apw, mock_settings):
        mock_settings.return_value = MagicMock(
            scraper_delay_min=0, scraper_delay_max=0, amazon_marketplace="com"
        )
        scraper = AmazonScraper()
        assert scraper._pw is None
        assert scraper._browser is None
        assert scraper._page is None

    @patch("libro.intelligence.scraper.get_settings")
    @patch("libro.intelligence.scraper.async_playwright")
    def test_close_nullifies_all_references(self, mock_apw, mock_settings):
        """After close, all references should be None."""
        mock_settings.return_value = MagicMock(
            scraper_delay_min=0, scraper_delay_max=0, amazon_marketplace="com"
        )

        mock_pw_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_apw.return_value.start = AsyncMock(return_value=mock_pw_instance)
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        scraper = AmazonScraper()
        asyncio.run(scraper._ensure_browser())

        assert scraper._pw is not None
        assert scraper._browser is not None
        assert scraper._page is not None

        asyncio.run(scraper.close())

        assert scraper._pw is None
        assert scraper._browser is None
        assert scraper._page is None


class TestRawProductDataclass:
    def test_defaults(self):
        p = RawProduct(asin="B001", title="Test")
        assert p.price is None
        assert p.rating is None
        assert p.reviews_count == 0
        assert p.url == ""

    def test_full_construction(self):
        p = RawProduct(
            asin="B001", title="Test", price=9.99,
            rating=4.5, reviews_count=100, url="https://example.com"
        )
        assert p.price == 9.99
        assert p.reviews_count == 100


class TestProductDetailDataclass:
    def test_defaults(self):
        d = ProductDetail(asin="B001", title="Test")
        assert d.bsr is None
        assert d.page_count is None
        assert d.author is None

    def test_full_construction(self):
        d = ProductDetail(
            asin="B001", title="Test", bsr=50000,
            page_count=120, author="John Doe"
        )
        assert d.bsr == 50000
        assert d.author == "John Doe"
