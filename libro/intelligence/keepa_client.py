"""Keepa API client for BSR history and product enrichment."""

import json
import logging
import time
from dataclasses import dataclass

import httpx

from libro.config import get_settings

log = logging.getLogger(__name__)

KEEPA_API_BASE = "https://api.keepa.com"


@dataclass
class KeepaProduct:
    """Parsed Keepa product data."""
    asin: str
    bsr_history: list[tuple[int, int]]  # [(timestamp_minutes, bsr), ...]
    bsr_current: int | None = None
    bsr_30d_avg: float | None = None
    bsr_90d_avg: float | None = None
    bsr_trend: str | None = None  # rising | stable | falling
    price_current: float | None = None
    review_count: int | None = None
    rating: float | None = None


class KeepaClient:
    """Thin wrapper around Keepa API with token budget management."""

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self._api_key = api_key or settings.keepa_api_key
        if not self._api_key:
            raise ValueError(
                "Keepa API key not configured. Set LIBRO_KEEPA_API_KEY in .env"
            )
        self._tokens_left: int | None = None
        self._client = httpx.Client(timeout=30.0)

    def _request(self, endpoint: str, params: dict) -> dict:
        """Make a Keepa API request and track token usage."""
        params["key"] = self._api_key
        url = f"{KEEPA_API_BASE}/{endpoint}"

        response = self._client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Track remaining tokens
        self._tokens_left = data.get("tokensLeft")
        tokens_consumed = data.get("tokensConsumed", 0)
        log.info(
            f"Keepa: consumed {tokens_consumed} tokens, {self._tokens_left} remaining"
        )

        if self._tokens_left is not None and self._tokens_left < 5:
            log.warning(f"Keepa token budget low: {self._tokens_left} tokens remaining")

        return data

    def get_product(self, asin: str, domain: int = 1) -> KeepaProduct | None:
        """Fetch product data from Keepa.

        Args:
            asin: Amazon ASIN.
            domain: Amazon domain ID (1=com, 2=co.uk, 3=de, 4=fr, 5=co.jp, etc.)

        Returns:
            KeepaProduct with parsed BSR history or None if not found.
        """
        try:
            data = self._request("product", {
                "asin": asin,
                "domain": domain,
                "stats": 90,  # Include 90-day stats
            })
        except httpx.HTTPStatusError as e:
            log.error(f"Keepa API error for {asin}: {e}")
            return None

        products = data.get("products", [])
        if not products:
            log.warning(f"No Keepa data for ASIN {asin}")
            return None

        product = products[0]
        return self._parse_product(asin, product)

    def get_products_bulk(
        self, asins: list[str], domain: int = 1
    ) -> list[KeepaProduct]:
        """Fetch multiple products in one API call (up to 100 ASINs).

        More token-efficient than individual calls.
        """
        if len(asins) > 100:
            raise ValueError("Keepa bulk limit is 100 ASINs per request")

        try:
            data = self._request("product", {
                "asin": ",".join(asins),
                "domain": domain,
                "stats": 90,
            })
        except httpx.HTTPStatusError as e:
            log.error(f"Keepa bulk API error: {e}")
            return []

        results = []
        for product_data in data.get("products", []):
            asin = product_data.get("asin", "")
            parsed = self._parse_product(asin, product_data)
            if parsed:
                results.append(parsed)

        return results

    def _parse_product(self, asin: str, data: dict) -> KeepaProduct | None:
        """Parse raw Keepa product data into KeepaProduct."""
        # BSR history is in csv format: [timestamp, value, timestamp, value, ...]
        # Index 3 = Sales Rank
        csv_data = data.get("csv", [])
        bsr_history = self._parse_bsr_csv(csv_data)

        # Stats from Keepa's built-in analysis
        stats = data.get("stats", {})

        # Current BSR
        bsr_current = None
        if bsr_history:
            bsr_current = bsr_history[-1][1]

        # Calculate averages from history
        bsr_30d_avg = self._calc_avg_bsr(bsr_history, days=30)
        bsr_90d_avg = self._calc_avg_bsr(bsr_history, days=90)

        # Trend detection
        bsr_trend = self._detect_trend(bsr_history, days=30)

        # Price (Keepa stores in cents)
        price_current = None
        price_csv = csv_data[0] if csv_data else None
        if price_csv and len(price_csv) >= 2:
            last_price = price_csv[-1]
            if last_price and last_price > 0:
                price_current = last_price / 100.0

        # Reviews
        review_count = stats.get("current", {}).get("RATING", [None, None])
        rating_val = None
        review_count_val = None

        # Parse review count from stats
        count_history = csv_data[16] if len(csv_data) > 16 else None
        if count_history and len(count_history) >= 2:
            review_count_val = count_history[-1]

        rating_history = csv_data[17] if len(csv_data) > 17 else None
        if rating_history and len(rating_history) >= 2:
            raw_rating = rating_history[-1]
            if raw_rating and raw_rating > 0:
                rating_val = raw_rating / 10.0

        return KeepaProduct(
            asin=asin,
            bsr_history=bsr_history,
            bsr_current=bsr_current,
            bsr_30d_avg=bsr_30d_avg,
            bsr_90d_avg=bsr_90d_avg,
            bsr_trend=bsr_trend,
            price_current=price_current,
            review_count=review_count_val,
            rating=rating_val,
        )

    def _parse_bsr_csv(self, csv_data: list) -> list[tuple[int, int]]:
        """Parse BSR from Keepa CSV format.

        Keepa CSV index 3 = Sales Rank (BSR).
        Format: [time1, value1, time2, value2, ...]
        Time is in Keepa minutes (minutes since epoch 2011-01-01).
        """
        if not csv_data or len(csv_data) <= 3:
            return []

        bsr_csv = csv_data[3]
        if not bsr_csv:
            return []

        history = []
        for i in range(0, len(bsr_csv) - 1, 2):
            timestamp = bsr_csv[i]
            value = bsr_csv[i + 1]
            if value is not None and value > 0:
                history.append((timestamp, value))

        return history

    def _calc_avg_bsr(
        self, history: list[tuple[int, int]], days: int
    ) -> float | None:
        """Calculate average BSR over the last N days."""
        if not history:
            return None

        # Keepa minutes: minutes since 2011-01-01
        # Current Keepa time ≈ (unix_now - 1293836400) / 60
        now_keepa = int((time.time() - 1293836400) / 60)
        cutoff = now_keepa - (days * 24 * 60)

        recent = [bsr for ts, bsr in history if ts >= cutoff]
        if not recent:
            return None

        return sum(recent) / len(recent)

    def _detect_trend(
        self, history: list[tuple[int, int]], days: int = 30
    ) -> str | None:
        """Detect BSR trend over last N days using simple slope.

        Returns: 'rising' (BSR going down = more sales),
                 'falling' (BSR going up = fewer sales),
                 'stable'
        """
        if not history or len(history) < 3:
            return None

        now_keepa = int((time.time() - 1293836400) / 60)
        cutoff = now_keepa - (days * 24 * 60)
        recent = [(ts, bsr) for ts, bsr in history if ts >= cutoff]

        if len(recent) < 3:
            return None

        # Simple linear regression slope
        n = len(recent)
        sum_x = sum(ts for ts, _ in recent)
        sum_y = sum(bsr for _, bsr in recent)
        sum_xy = sum(ts * bsr for ts, bsr in recent)
        sum_x2 = sum(ts * ts for ts, _ in recent)

        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return "stable"

        slope = (n * sum_xy - sum_x * sum_y) / denom

        # Normalize slope relative to mean BSR
        mean_bsr = sum_y / n
        if mean_bsr == 0:
            return "stable"

        # Slope as percentage of mean per day
        daily_change_pct = (slope * 60 * 24) / mean_bsr * 100

        # BSR going down = demand rising (note: inverted)
        if daily_change_pct < -0.5:
            return "rising"  # BSR decreasing = sales increasing
        elif daily_change_pct > 0.5:
            return "falling"  # BSR increasing = sales decreasing
        else:
            return "stable"

    @property
    def tokens_remaining(self) -> int | None:
        return self._tokens_left

    def close(self) -> None:
        self._client.close()
