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

# Retry configuration
MAX_STEP_RETRIES = 2
RETRY_DELAY_SECONDS = 5


@dataclass
class UploadResult:
    """Result of uploading a single variant."""
    variant_id: int
    success: bool = False
    published: bool = False
    skipped: bool = False
    error: str | None = None
    retries: int = 0


@dataclass
class BatchResult:
    """Result of a batch upload session."""
    total: int = 0
    published: int = 0
    skipped: int = 0
    errors: int = 0
    details: list[UploadResult] = field(default_factory=list)

    @property
    def failed_variant_ids(self) -> list[int]:
        """IDs of variants that failed (for retry)."""
        return [d.variant_id for d in self.details if d.error and not d.skipped]


class KDPUploader:
    """Semi-automated KDP uploader using Playwright.

    Flow:
    1. User logs in manually (browser visible)
    2. Bot fills all form fields automatically
    3. Bot pauses before publish — user reviews and confirms
    4. Bot marks as published in DB
    """

    # Persistent session directory — cookies & storage survive between runs
    SESSION_DIR = Path.home() / ".libro" / "kdp_session"

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
        """Launch browser with persistent session and wait for login.

        Uses a persistent browser context so cookies/session are saved
        between runs — avoids repeated CAPTCHAs.

        Returns True if login detected, False on timeout.
        """
        self.SESSION_DIR.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()

        # Persistent context = cookies, localStorage, etc. saved to disk
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.SESSION_DIR),
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

        # Navigate to KDP
        await self._page.goto(sel.KDP_BOOKSHELF_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Check if already logged in (session from previous run)
        already_logged_in = await self._check_bookshelf()
        if already_logged_in:
            print("\n" + "=" * 60)
            print("  LIBRO KDP UPLOADER — Semi-Automatizado")
            print("=" * 60)
            print("\n  [OK] Sesion anterior detectada — ya estas logueado!")
            print("=" * 60)
            return True

        # Not logged in — ask user to login manually
        print("\n" + "=" * 60)
        print("  LIBRO KDP UPLOADER — Semi-Automatizado")
        print("=" * 60)
        print("\n  1. Inicia sesion en KDP manualmente en el navegador")
        print("  2. Cuando estes en el Bookshelf, presiona Enter aqui")
        print()
        print("  NOTA: Tu sesion se guardara para futuras ejecuciones")
        print("        (no tendras que resolver el CAPTCHA cada vez)")
        print("=" * 60)

        # Wait for user to login
        input("\n  Presiona Enter cuando hayas iniciado sesion... ")

        if await self._check_bookshelf():
            return True

        # Retry: navigate to bookshelf directly
        await self._page.goto(sel.KDP_BOOKSHELF_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        if await self._check_bookshelf():
            return True

        print("\n  [ERROR] No se detecto login. Verifica e intenta de nuevo.")
        return False

    async def _check_bookshelf(self) -> bool:
        """Check if the bookshelf is visible (user is logged in)."""
        try:
            await self._page.wait_for_selector(
                sel.BOOKSHELF_INDICATOR,
                timeout=10000,
            )
            print("\n  [OK] Login detectado — Bookshelf visible")
            return True
        except Exception:
            return False

    async def upload_variant(self, session, variant_id: int) -> UploadResult:
        """Upload a single variant to KDP.

        Fills all forms and pauses for user confirmation before publish.
        Includes retry logic for transient failures (network, timeouts).
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

        # Validate PDFs before attempting upload
        from libro.common.pdf_validation import validate_interior, validate_cover

        iv = validate_interior(
            Path(variant.interior_pdf_path), variant.trim_size, variant.page_count
        )
        if not iv.valid:
            result.error = f"Interior PDF invalid: {iv.summary}"
            return result

        cv = validate_cover(
            Path(variant.cover_pdf_path), variant.trim_size, variant.page_count
        )
        if not cv.valid:
            result.error = f"Cover PDF invalid: {cv.summary}"
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
            # Check session is still valid before starting
            if not await self._ensure_session():
                result.error = "Session expired and could not be restored"
                return result

            # Navigate to create new paperback
            await self._rate_limiter.wait()
            await self._navigate_with_retry(sel.KDP_CREATE_PAPERBACK_URL)
            await asyncio.sleep(3)

            # Step 1: Book Details (with retry)
            print("  [1/3] Llenando detalles del libro...")
            await self._retry_step(
                self._fill_book_details, metadata,
                step_name="Book Details",
            )

            # Click Save and Continue
            await self._rate_limiter.wait()
            await self._click_first_match(sel.SAVE_CONTINUE_1)
            await asyncio.sleep(5)

            # Step 2: Content (manuscript + cover, with retry)
            print("  [2/3] Subiendo manuscrito y portada...")
            await self._retry_step(
                self._upload_content, variant,
                step_name="Content Upload",
            )

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
            elif user_input in ("skip", "s"):
                result.skipped = True
                print("  [SKIP] Saltado — no se marco como publicado")
            else:
                await self._mark_published(session, variant_id)
                result.published = True
                print("  [OK] Marcado como publicado en la base de datos")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            result.error = str(e)
            log.error(f"Upload error for variant #{variant_id}: {e}")
            await self._save_error_screenshot(variant_id)

        return result

    async def upload_batch(
        self,
        session,
        variant_ids: list[int],
        retry_failed: bool = True,
    ) -> BatchResult:
        """Upload a batch of variants with pauses between each.

        If retry_failed is True, variants that fail with transient errors
        are retried once at the end of the batch.
        """
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

        # Retry failed uploads (transient errors only)
        failed_ids = batch.failed_variant_ids
        if retry_failed and failed_ids:
            print(f"\n{'=' * 60}")
            print(f"  REINTENTANDO {len(failed_ids)} libro(s) fallido(s)...")
            print(f"{'=' * 60}")

            for vid in failed_ids:
                await self._rate_limiter.wait()
                print(f"\n  Reintentando Variant #{vid}...")

                try:
                    result = await self.upload_variant(session, vid)
                    result.retries += 1

                    if result.published or result.success:
                        # Replace the failed result with the successful retry
                        batch.details = [d for d in batch.details if d.variant_id != vid]
                        batch.details.append(result)
                        batch.errors -= 1
                        if result.published:
                            batch.published += 1
                        print(f"  [OK] Variant #{vid} exitoso en reintento")
                    else:
                        print(f"  [FAIL] Variant #{vid} fallo de nuevo: {result.error}")

                except KeyboardInterrupt:
                    print("\n  Sesion terminada por el usuario.")
                    break

        # Summary
        print(f"\n{'=' * 60}")
        print(f"  RESUMEN: {batch.published} publicados, "
              f"{batch.skipped} saltados, {batch.errors} errores "
              f"de {batch.total} total")
        print(f"{'=' * 60}")

        return batch

    # --- Recovery & retry helpers ---

    async def _ensure_session(self) -> bool:
        """Verify session is still active; attempt to recover if expired."""
        try:
            await self._page.goto(sel.KDP_BOOKSHELF_URL, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            if await self._check_bookshelf():
                return True
        except Exception as e:
            log.warning(f"Session check failed: {e}")

        # Session expired — ask user to re-login
        print("\n  [!] Sesion expirada. Por favor inicia sesion de nuevo en el navegador.")
        input("  Presiona Enter cuando hayas iniciado sesion... ")

        try:
            await self._page.goto(sel.KDP_BOOKSHELF_URL, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            return await self._check_bookshelf()
        except Exception:
            return False

    async def _navigate_with_retry(self, url: str, max_retries: int = MAX_STEP_RETRIES) -> None:
        """Navigate to a URL with retry on failure."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                return
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    log.warning(f"Navigation failed (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        raise RuntimeError(f"Navigation failed after {max_retries + 1} attempts: {last_error}")

    async def _retry_step(self, step_fn, *args, step_name: str = "step") -> None:
        """Execute a form-filling step with retry on failure."""
        last_error = None
        for attempt in range(MAX_STEP_RETRIES + 1):
            try:
                await step_fn(*args)
                return
            except Exception as e:
                last_error = e
                if attempt < MAX_STEP_RETRIES:
                    log.warning(f"{step_name} failed (attempt {attempt + 1}): {e}")
                    print(f"    [!] {step_name} fallo, reintentando...")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    # Try to recover the page state
                    try:
                        await self._page.reload(wait_until="domcontentloaded")
                        await asyncio.sleep(3)
                    except Exception:
                        pass
        raise RuntimeError(f"{step_name} failed after {MAX_STEP_RETRIES + 1} attempts: {last_error}")

    async def _save_error_screenshot(self, variant_id: int) -> None:
        """Save a debug screenshot on error."""
        path = f"/tmp/libro_kdp_error_{variant_id}.png"
        try:
            await self._page.screenshot(path=path)
            print(f"  [ERROR] Screenshot guardado en {path}")
        except Exception:
            pass

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
        first_name = author_parts[0] if len(author_parts) > 1 else ""
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
                if "cover" in name.lower() or "pdf" in accept.lower() or "image" in accept.lower():
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
        from datetime import UTC, datetime, timedelta
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

        now = datetime.now(UTC)
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
        if self._context:
            await self._context.close()
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
