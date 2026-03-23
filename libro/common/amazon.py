"""Amazon URL builders, ASIN parsing, and BSR-to-sales estimation."""

import re

ASIN_PATTERN = re.compile(r"[A-Z0-9]{10}")


def extract_asin(text: str) -> str | None:
    match = ASIN_PATTERN.search(text)
    return match.group(0) if match else None


def amazon_search_url(keyword: str, marketplace: str = "com", page: int = 1) -> str:
    keyword_encoded = keyword.replace(" ", "+")
    return (
        f"https://www.amazon.{marketplace}/s"
        f"?k={keyword_encoded}&i=stripbooks-intl-ship&page={page}"
    )


def amazon_product_url(asin: str, marketplace: str = "com") -> str:
    return f"https://www.amazon.{marketplace}/dp/{asin}"


def estimate_daily_sales(bsr: int) -> float:
    """Estimate daily sales from BSR using empirical power-law formula.

    Based on widely-used KDP community approximations:
    - BSR 1 ≈ 500+ sales/day
    - BSR 1,000 ≈ 25 sales/day
    - BSR 10,000 ≈ 5 sales/day
    - BSR 100,000 ≈ 0.5 sales/day
    - BSR 500,000 ≈ 0.05 sales/day

    Formula: sales ≈ 100000 / (BSR ^ 0.8)
    """
    if bsr <= 0:
        return 0.0
    return 100_000 / (bsr ** 0.8)


def estimate_monthly_revenue(bsr: int, price: float) -> float:
    """Estimate monthly revenue from BSR and price.

    KDP royalty is ~60% for books priced $2.99-$9.99 (paperback ~40%).
    Using 40% as conservative estimate for low-content paperbacks.
    """
    daily_sales = estimate_daily_sales(bsr)
    royalty_rate = 0.40
    return daily_sales * 30 * price * royalty_rate
