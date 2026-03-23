"""KDP semi-automated uploader — fills forms, user confirms publish."""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from libro.common.rate_limiter import RateLimiter
from libro.config import get_settings
from libro.kdp import selectors as sel

log = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of uploading a single variant."""
    variant_id: int
    success: bool = False
    published: bool = False
    skipped: bool = False
    error: str | None = None


@dataclass
class BatchResult:
    """Result of a batch upload session."""
    total: int = 0
    published: int = 0
    skipped: int = 0
    errors: int = 0
    details: list[UploadResult] = field(default_factory=list)


class KDPUploader:
    """Semi-automated KDP uploader using Playwright.

    Flow:
    1. User logs in manually (browser visible)
    2. Bot fills all form fields automatically
    3. Bot pauses before publish — user reviews and confirms
    4. Bot marks as published in DB
    """

    def __init__(
        self,
        headless: bool = False,
        delay_min: float = 3.0,
        delay_max: float = 8.0,
    ):
        self.headless = headless
        self._rate_limiter = RateLimiter(min_delay=delay_min, max_delay=delay_max)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def start(self) -> bool:
        """Launch browser and wait for manual login.

        Returns True if login detected, False on timeout.
        """
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        self._page = await self._context.new_page()

        # Navigate to KDP
        await self._page.goto(sel.KDP_BOOKSHELF_URL, wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("  LIBRO KDP UPLOADER — Semi-Automatizado")
        print("=" * 60)
        print("\n  1. Inicia sesion en KDP manualmente en el navegador")
        print("  2. Cuando estes en el Bookshelf, presiona Enter aqui")
        print("=" * 60)

        # Wait for user to login
        input("\n  Presiona Enter cuando hayas iniciado sesion... ")

        # Verify login by checking for bookshelf
        try:
            await self._page.wait_for_selector(
                sel.BOOKSHELF_INDICATOR,
                timeout=10000,
            )
            print("\n  [OK] Login detectado — Bookshelf visible")
            return True
        except Exception:
            # Maybe they're on a different page but logged in — try navigating
            await self._page.goto(sel.KDP_BOOKSHELF_URL, wait_until="domcontentloaded")
            try:
                await self._page.wait_for_selector(
                    sel.BOOKSHELF_INDICATOR,
                    timeout=10000,
                )
                print("\n  [OK] Login detectado — Bookshelf visible")
                return True
            except Exception:
                print("\n  [ERROR] No se detecto login. Verifica e intenta de nuevo.")
                return False

    async def upload_variant(self, session, variant_id: int) -> UploadResult:
        """Upload a single variant to KDP.

        Fills all forms and pauses for user confirmation before publish.
        """
        from libro.models.variant import Variant
        from libro.publication.metadata import generate_metadata
        from libro.publication.checklist import run_checklist

        result = UploadResult(variant_id=variant_id)

        # Validate variant
        variant = session.get(Variant, variant_id)
        if not variant:
            result.error = f"Variant #{variant_id} not found"
            return result

        if not variant.interior_pdf_path or not variant.cover_pdf_path:
            result.error = f"Variant #{variant_id} missing interior or cover PDF"
            return result

        # Run checklist
        checklist = run_checklist(session, variant_id)
        if not checklist.passed:
            errors = [c.message for c in checklist.checks if not c.passed and c.severity == "error"]
            result.error = f"Checklist failed: {'; '.join(errors)}"
            return result

        # Generate metadata
        author = ""
        if variant.brand:
            author = variant.brand.name
        metadata = generate_metadata(variant, author=author)

        print(f"\n  --- Subiendo: {variant.title[:50]}... ---")

        try:
            # Navigate to create new paperback
            await self._rate_limiter.wait()
            await self._page.goto(
                sel.KDP_CREATE_PAPERBACK_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await asyncio.sleep(3)  # Let page fully load

            # Step 1: Book Details
            print("  [1/3] Llenando detalles del libro...")
            await self._fill_book_details(metadata)

            # Click Save and Continue
            await self._rate_limiter.wait()
            await self._click_first_match(sel.SAVE_CONTINUE_1)
            await asyncio.sleep(5)  # Wait for page transition

            # Step 2: Content (manuscript + cover)
            print("  [2/3] Subiendo manuscrito y portada...")
            await self._upload_content(variant)

            # Click Save and Continue
            await self._rate_limiter.wait()
            await self._click_first_match(sel.SAVE_CONTINUE_2)
            await asyncio.sleep(5)

            # Step 3: Pricing
            print("  [3/3] Configurando precio...")
            await self._set_pricing(metadata.price_suggestion)

            # PAUSE — User reviews and confirms
            result.success = True
            print("\n" + "=" * 60)
            print(f"  LIBRO LISTO: {variant.title[:50]}")
            print(f"  Precio: {metadata.price_suggestion}")
            print("=" * 60)
            print("  Revisa todo en el navegador.")
            print("  - Enter  → Marcar como publicado en DB")
            print("  - 'skip' → Saltar sin publicar")
            print("  - 'quit' → Terminar sesion")
            print("=" * 60)

            user_input = input("\n  Tu decision: ").strip().lower()

            if user_input == "quit":
                result.skipped = True
                raise KeyboardInterrupt("User quit")
            elif user_input == "skip" or user_input == "s":
                result.skipped = True
                print("  [SKIP] Saltado — no se marco como publicado")
            else:
                # Mark as published in DB
                await self._mark_published(session, variant_id)
                result.published = True
                print("  [OK] Marcado como publicado en la base de datos")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            result.error = str(e)
            log.error(f"Upload error for variant #{variant_id}: {e}")
            # Take debug screenshot
            try:
                await self._page.screenshot(path="/tmp/libro_kdp_error.png")
                print(f"  [ERROR] Screenshot guardado en /tmp/libro_kdp_error.png")
            except Exception:
                pass

        return result

    async def upload_batch(
        self,
        session,
        variant_ids: list[int],
    ) -> BatchResult:
        """Upload a batch of variants with pauses between each."""
        batch = BatchResult(total=len(variant_ids))

        for i, vid in enumerate(variant_ids, 1):
            print(f"\n{'=' * 60}")
            print(f"  Libro {i}/{len(variant_ids)} — Variant #{vid}")
            print(f"{'=' * 60}")

            try:
                result = await self.upload_variant(session, vid)
                batch.details.append(result)

                if result.published:
                    batch.published += 1
                elif result.skipped:
                    batch.skipped += 1
                elif result.error:
                    batch.errors += 1
                    print(f"  [ERROR] {result.error}")

            except KeyboardInterrupt:
                print("\n  Sesion terminada por el usuario.")
                break

            # Pause between books
            if i < len(variant_ids):
                await self._rate_limiter.wait()

        return batch

    async def _fill_book_details(self, metadata) -> None:
        """Fill Step 1: Book Details form."""
        page = self._page

        # Language (English)
        await self._try_select(sel.LANGUAGE_SELECT, "en_US")
        await self._rate_limiter.wait()

        # Title
        await self._try_fill(sel.TITLE_INPUT, metadata.title)
        await self._rate_limiter.wait()

        # Subtitle
        if metadata.subtitle:
            await self._try_fill(sel.SUBTITLE_INPUT, metadata.subtitle)
            await self._rate_limiter.wait()

        # Author (split into first/last)
        author_parts = metadata.author.rsplit(" ", 1) if metadata.author else ["", ""]
        first_name = author_parts[0] if len(author_parts) > 0 else ""
        last_name = author_parts[1] if len(author_parts) > 1 else author_parts[0]

        await self._try_fill(sel.AUTHOR_FIRST_NAME, first_name)
        await self._rate_limiter.wait()
        await self._try_fill(sel.AUTHOR_LAST_NAME, last_name)
        await self._rate_limiter.wait()

        # Description — try iframe first, then textarea
        try:
            iframe_el = await page.query_selector(sel.DESCRIPTION_IFRAME)
            if iframe_el:
                frame = await iframe_el.content_frame()
                if frame:
                    await frame.click("body")
                    await frame.fill("body", metadata.description)
            else:
                await self._try_fill(sel.DESCRIPTION_TEXTAREA, metadata.description)
        except Exception as e:
            log.warning(f"Description fill failed: {e}")
        await self._rate_limiter.wait()

        # Publishing rights — own copyright
        await self._try_click(sel.RIGHTS_OWN)
        await self._rate_limiter.wait()

        # Keywords (up to 7)
        for i, kw in enumerate(metadata.keywords[:7]):
            selector = sel.KEYWORD_INPUT_TEMPLATE.format(index=i)
            await self._try_fill(selector, kw)
            await asyncio.sleep(0.5)
        await self._rate_limiter.wait()

        # Adult content — No
        await self._try_click(sel.ADULT_CONTENT_NO)

    async def _upload_content(self, variant) -> None:
        """Fill Step 2: Upload manuscript and cover."""
        page = self._page

        # Trim size
        trim_map = {
            "5x8": "5x8", "5.06x7.81": "5.06x7.81",
            "5.5x8.5": "5.5x8.5", "6x9": "6x9",
            "8.5x11": "8.5x11",
        }
        trim_value = trim_map.get(variant.trim_size, "6x9")
        await self._try_select(sel.TRIM_SIZE_SELECT, trim_value)
        await self._rate_limiter.wait()

        # Paper type — white
        await self._try_click(sel.PAPER_WHITE)
        await self._rate_limiter.wait()

        # No bleed (for low-content books)
        await self._try_click(sel.NO_BLEED)
        await self._rate_limiter.wait()

        # Matte finish
        await self._try_click(sel.MATTE_FINISH)
        await self._rate_limiter.wait()

        # Upload manuscript PDF
        interior_path = Path(variant.interior_pdf_path)
        if interior_path.exists():
            print(f"    Subiendo manuscrito: {interior_path.name}")
            file_inputs = await page.query_selector_all("input[type='file']")
            for fi in file_inputs:
                accept = await fi.get_attribute("accept") or ""
                if "pdf" in accept.lower() or "interior" in (await fi.get_attribute("name") or "").lower():
                    await fi.set_input_files(str(interior_path))
                    break
            else:
                # Fallback: try first file input
                if file_inputs:
                    await file_inputs[0].set_input_files(str(interior_path))

            # Wait for upload to process
            print("    Esperando procesamiento del manuscrito...")
            await asyncio.sleep(15)  # PDF processing takes time on KDP
        else:
            log.warning(f"Interior PDF not found: {interior_path}")

        await self._rate_limiter.wait()

        # Upload cover
        cover_path = Path(variant.cover_pdf_path)
        if cover_path.exists():
            # Select "Upload a cover" tab
            await self._try_click(sel.COVER_UPLOAD_TAB)
            await asyncio.sleep(2)

            print(f"    Subiendo portada: {cover_path.name}")
            file_inputs = await page.query_selector_all("input[type='file']")
            for fi in file_inputs:
                accept = await fi.get_attribute("accept") or ""
                name = await fi.get_attribute("name") or ""
                if "image" in accept.lower() or "cover" in name.lower():
                    await fi.set_input_files(str(cover_path))
                    break

            # Wait for upload
            print("    Esperando procesamiento de la portada...")
            await asyncio.sleep(10)
        else:
            log.warning(f"Cover file not found: {cover_path}")

    async def _set_pricing(self, price_suggestion: str) -> None:
        """Fill Step 3: Set pricing."""
        # Extract numeric price
        price = price_suggestion.replace("$", "").strip()

        await self._try_fill(sel.PRICE_INPUT, price)
        await self._rate_limiter.wait()

    async def _mark_published(self, session, variant_id: int) -> None:
        """Mark variant as published in the database."""
        from datetime import datetime, timedelta
        from libro.models.variant import Variant
        from libro.models.publication import Publication

        settings = get_settings()
        variant = session.get(Variant, variant_id)
        if not variant:
            return

        # Check if already published
        existing = (
            session.query(Publication)
            .filter(Publication.variant_id == variant_id)
            .first()
        )
        if existing:
            return

        now = datetime.utcnow()
        pub = Publication(
            variant_id=variant_id,
            published_at=now,
            evaluation_start=now,
            evaluation_end=now + timedelta(days=settings.evaluation_period_days),
            auto_kill_date=now + timedelta(days=settings.auto_kill_days),
        )
        session.add(pub)
        variant.status = "published"

        if variant.niche:
            variant.niche.status = "testing"

        session.flush()

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # --- Helper methods ---

    async def _try_fill(self, selector_chain: str, value: str) -> bool:
        """Try multiple selectors (comma-separated) to fill a field."""
        for selector in selector_chain.split(","):
            selector = selector.strip()
            try:
                el = await self._page.query_selector(selector)
                if el:
                    await el.click()
                    await el.fill("")  # Clear first
                    await el.fill(value)
                    return True
            except Exception:
                continue
        log.debug(f"Could not fill any selector: {selector_chain[:50]}")
        return False

    async def _try_click(self, selector_chain: str) -> bool:
        """Try multiple selectors to click an element."""
        for selector in selector_chain.split(","):
            selector = selector.strip()
            try:
                el = await self._page.query_selector(selector)
                if el:
                    await el.click()
                    return True
            except Exception:
                continue
        log.debug(f"Could not click any selector: {selector_chain[:50]}")
        return False

    async def _try_select(self, selector_chain: str, value: str) -> bool:
        """Try multiple selectors to select a dropdown value."""
        for selector in selector_chain.split(","):
            selector = selector.strip()
            try:
                el = await self._page.query_selector(selector)
                if el:
                    await el.select_option(value=value)
                    return True
            except Exception:
                continue
        return False

    async def _click_first_match(self, selector_chain: str) -> bool:
        """Click the first visible, enabled element matching any selector."""
        for selector in selector_chain.split(","):
            selector = selector.strip()
            try:
                el = await self._page.query_selector(selector)
                if el and await el.is_visible() and await el.is_enabled():
                    await el.click()
                    return True
            except Exception:
                continue
        # Last resort: try clicking by text
        try:
            await self._page.click("text=Save and Continue", timeout=5000)
            return True
        except Exception:
            return False
