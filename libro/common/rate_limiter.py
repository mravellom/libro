"""Simple rate limiter for scraping requests."""

import asyncio
import random
import time


class RateLimiter:
    """Enforces minimum delay between requests with random jitter."""

    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request: float = 0.0

    async def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request = time.monotonic()

    def wait_sync(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request = time.monotonic()
