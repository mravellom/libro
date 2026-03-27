"""Cover generation — creates KDP-compliant book covers using Pillow.

Supports 8 distinct layout styles selected by seed for visual variety.
Each layout uses gradients, transparency, shadows, and decorative elements
to produce professional-looking covers.
"""

import logging
import math
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from libro.common.pdf_utils import get_cover_dimensions

log = logging.getLogger(__name__)

DPI = 300

LAYOUTS = [
    "_layout_geometric",
    "_layout_gradient_band",
    "_layout_frame",
    "_layout_split",
    "_layout_pattern",
    "_layout_minimal_modern",
    "_layout_watercolor",
    "_layout_layered_shapes",
]


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _px(inches: float) -> int:
    return int(inches * DPI)


def _hex(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _blend(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * max(0, min(1, t))) for a, b in zip(c1, c2))


def _darken(c: tuple, f: float = 0.6) -> tuple:
    return tuple(max(0, int(v * f)) for v in c)


def _lighten(c: tuple, f: float = 0.3) -> tuple:
    return tuple(min(255, int(v + (255 - v) * f)) for v in c)


def _rgba(c: tuple, a: int = 255) -> tuple:
    return (*c[:3], a)


def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    dejavu = {
        "Sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "Sans-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "Serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "Serif-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    }
    if name in dejavu:
        try:
            return ImageFont.truetype(dejavu[name], size)
        except OSError:
            pass
    for p in [
        f"/usr/share/fonts/truetype/dejavu/DejaVu{name}.ttf",
        f"/usr/share/fonts/truetype/liberation/Liberation{name}-Regular.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _vgradient(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
               c_top: tuple, c_bot: tuple) -> None:
    """Draw a vertical gradient rectangle."""
    for row in range(h):
        t = row / max(h - 1, 1)
        c = _blend(c_top, c_bot, t)
        draw.line([x, y + row, x + w, y + row], fill=_rgba(c))


def _hgradient(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
               c_left: tuple, c_right: tuple) -> None:
    """Draw a horizontal gradient rectangle."""
    for col in range(w):
        t = col / max(w - 1, 1)
        c = _blend(c_left, c_right, t)
        draw.line([x + col, y, x + col, y + h], fill=_rgba(c))


def _radial_gradient(size: tuple, center: tuple, radius: int,
                     inner: tuple, outer: tuple) -> Image.Image:
    """Create a radial gradient RGBA image."""
    img = Image.new("RGBA", size, (*outer[:3], 0))
    draw = ImageDraw.Draw(img)
    steps = min(radius, 120)
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        c = _blend(inner, outer, 1.0 - t)
        a = int(inner[3] * t) if len(inner) > 3 else int(255 * t)
        draw.ellipse([center[0] - r, center[1] - r, center[0] + r, center[1] + r],
                     fill=(*c[:3], a))
    return img


# ---------------------------------------------------------------------------
# CoverGenerator
# ---------------------------------------------------------------------------

class CoverGenerator:
    """Generates KDP-compliant book covers with 8 visual layout styles."""

    def generate(
        self,
        title: str,
        subtitle: str | None = None,
        author: str | None = None,
        trim_size: str = "6x9",
        page_count: int = 120,
        output_path: Path | None = None,
        primary_color: str = "#2C3E50",
        secondary_color: str = "#ECF0F1",
        accent_color: str = "#E74C3C",
        font_name: str = "Sans",
        template_path: Path | None = None,
        seed: int | None = None,
    ) -> Path:
        dims = get_cover_dimensions(trim_size, page_count)
        tw = _px(dims.total_width)
        th = _px(dims.total_height)

        primary = _hex(primary_color)
        secondary = _hex(secondary_color)
        accent = _hex(accent_color)

        if template_path and Path(template_path).exists():
            img = Image.open(template_path).resize((tw, th)).convert("RGBA")
        else:
            img = Image.new("RGBA", (tw, th), _rgba(primary))

        draw = ImageDraw.Draw(img)

        bleed = _px(dims.bleed)
        fw = _px(dims.width)
        sw = _px(dims.spine_width)
        bw = fw
        fl = bleed + bw + sw  # front left
        fcx = fl + fw // 2    # front center x
        ch = th - 2 * bleed   # content height

        # --- Apply layout ---
        layout_name = "legacy"
        if seed is not None:
            rng = random.Random(seed)
            idx = rng.randint(0, len(LAYOUTS) - 1)
            layout_name = LAYOUTS[idx]
            tp = getattr(self, layout_name)(img, draw, fl, bleed, fw, ch,
                                            primary, secondary, accent, rng)
        else:
            tp = self._layout_legacy(draw, fl, bleed, fw, ch, accent, secondary)

        # Refresh draw after alpha_composite operations
        draw = ImageDraw.Draw(img)

        text_color = tp.get("text_color", secondary)
        shadow_color = _darken(primary, 0.3)
        margin_in = tp.get("margin_inches", 0.5)
        max_tw = fw - _px(margin_in * 2)

        # --- Title with shadow ---
        tsz = tp.get("title_font_size", 72)
        tf = _get_font(f"{font_name}-Bold", tsz)
        ty = bleed + int(ch * tp.get("title_y_pct", 0.20))
        self._draw_text_shadow(draw, title, fcx, ty, max_tw, tf, text_color, shadow_color, offset=4)

        # --- Subtitle with shadow ---
        if subtitle:
            ssz = tp.get("subtitle_font_size", 36)
            sf = _get_font(font_name, ssz)
            sy = bleed + int(ch * tp.get("subtitle_y_pct", 0.48))
            self._draw_text_shadow(draw, subtitle, fcx, sy, max_tw, sf, text_color, shadow_color, offset=2)

        # --- Author with shadow ---
        if author:
            asz = tp.get("author_font_size", 32)
            af = _get_font(font_name, asz)
            ay = bleed + int(ch * tp.get("author_y_pct", 0.85))
            self._draw_text_shadow(draw, author, fcx, ay, max_tw, af, text_color, shadow_color, offset=2)

        # --- Spine ---
        if sw > _px(0.3):
            self._draw_spine(draw, title, author, bleed + bw + sw // 2,
                             bleed, ch, sw, font_name, text_color, img)
            draw = ImageDraw.Draw(img)

        # --- Back cover ---
        self._draw_back_cover(draw, bleed + bw // 2, bleed, bw, ch,
                              font_name, secondary, accent, primary)

        # Save as PDF (KDP requires PDF for paperback covers)
        output_path = Path(output_path or "cover.pdf")
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(str(output_path), format="PDF", resolution=DPI)
        log.info(f"Cover: {output_path} ({tw}x{th}px, {layout_name})")
        return output_path

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    def _draw_centered_text(self, draw, text, cx, y, max_w, font, color) -> int:
        cpl = max(10, int(max_w / (font.size * 0.55)))
        lines = textwrap.wrap(text, width=cpl)
        cur_y = y
        for line in lines:
            bb = draw.textbbox((0, 0), line, font=font)
            lw, lh = bb[2] - bb[0], bb[3] - bb[1]
            draw.text((cx - lw // 2, cur_y), line, font=font, fill=color)
            cur_y += lh + 10
        return cur_y

    def _draw_text_shadow(self, draw, text, cx, y, max_w, font, color, shadow, offset=3):
        """Draw text with a drop shadow for depth."""
        self._draw_centered_text(draw, text, cx + offset, y + offset, max_w, font,
                                 _rgba(shadow, 100))
        return self._draw_centered_text(draw, text, cx, y, max_w, font, color)

    def _draw_spine(self, draw, title, author, cx, top, h, sw, fn, color, img):
        fsz = max(14, min(24, sw - 10))
        font = _get_font(fn, fsz)
        txt = title[:40] + (f"  |  {author}" if author else "")
        bb = font.getbbox(txt)
        tw, th = bb[2] - bb[0] + 20, bb[3] - bb[1] + 10
        ti = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(ti).text((10, 5), txt, font=font, fill=_rgba(color))
        rot = ti.rotate(90, expand=True)
        img.paste(rot, (cx - rot.width // 2, top + (h - rot.height) // 2), rot)

    # ------------------------------------------------------------------
    # Back cover
    # ------------------------------------------------------------------

    def _draw_back_cover(self, draw, cx, top, w, h, fn, secondary, accent, primary):
        hw = w // 2
        # Accent bands
        bh = int(h * 0.025)
        draw.rectangle([cx - hw, top, cx + hw, top + bh], fill=_rgba(accent, 180))
        draw.rectangle([cx - hw, top + h - bh, cx + hw, top + h], fill=_rgba(accent, 180))

        # Thin inner line
        draw.rectangle([cx - hw + 15, top + bh + 8, cx + hw - 15, top + bh + 10],
                       fill=_rgba(accent, 60))

        # Description area with subtle gradient
        dw, dh = int(w * 0.72), int(h * 0.22)
        dx, dy = cx - dw // 2, top + int(h * 0.28)
        draw.rectangle([dx, dy, dx + dw, dy + dh], fill=_rgba(secondary, 18))
        draw.rectangle([dx, dy, dx + dw, dy + dh], outline=_rgba(accent, 35), width=1)

        # Barcode
        baw, bah = _px(2.0), _px(1.2)
        bax = cx - baw // 2
        bay = top + h - _px(1.8) - bah
        draw.rectangle([bax, bay, bax + baw, bay + bah], fill=(255, 255, 255, 255),
                       outline=_rgba(accent, 120), width=2)
        bf = _get_font(fn, 16)
        draw.text((bax + 10, bay + bah // 2 - 10), "ISBN / Barcode Area",
                  font=bf, fill=(150, 150, 150))

    # ------------------------------------------------------------------
    # Legacy (seed=None)
    # ------------------------------------------------------------------

    def _layout_legacy(self, draw, x, y, w, h, accent, secondary) -> dict:
        bh = int(h * 0.02)
        draw.rectangle([x, y, x + w, y + bh], fill=accent)
        draw.rectangle([x, y + h - bh, x + w, y + h], fill=accent)
        ly = y + int(h * 0.45)
        m = int(w * 0.15)
        draw.line([x + m, ly, x + w - m, ly], fill=_rgba(accent, 180), width=3)
        return {"title_y_pct": 0.20, "subtitle_y_pct": 0.48, "author_y_pct": 0.85}

    # ==================================================================
    # LAYOUT 0: GEOMETRIC — radial gradients + bold overlapping circles
    # ==================================================================

    def _layout_geometric(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        # Full-cover gradient base
        dark = _darken(primary, 0.35)
        _vgradient(draw, x, y, w, h, primary, dark)

        # Large glowing circles
        for _ in range(rng.randint(6, 10)):
            cx = x + rng.randint(-int(w * 0.1), int(w * 1.1))
            cy = y + rng.randint(-int(h * 0.1), int(h * 1.1))
            r = rng.randint(int(w * 0.18), int(w * 0.50))
            color = rng.choice([accent, _lighten(accent, 0.3), _blend(accent, secondary, 0.4)])
            alpha = rng.randint(40, 90)
            grad = _radial_gradient(img.size, (cx, cy), r, (*color, alpha), (*color, 0))
            img = Image.alpha_composite(img, grad)

        # Ring outlines for extra detail
        draw2 = ImageDraw.Draw(img)
        for _ in range(rng.randint(2, 4)):
            cx = x + rng.randint(int(w * 0.1), int(w * 0.9))
            cy = y + rng.randint(int(h * 0.1), int(h * 0.9))
            r = rng.randint(int(w * 0.10), int(w * 0.30))
            draw2.ellipse([cx - r, cy - r, cx + r, cy + r],
                          outline=_rgba(secondary, rng.randint(40, 80)), width=3)

        # Title backdrop
        by = y + int(h * 0.16)
        bh2 = int(h * 0.30)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle([x + int(w * 0.04), by, x + int(w * 0.96), by + bh2],
                             radius=20, fill=_rgba(primary, 170))
        img = Image.alpha_composite(img, layer)

        # Divider line
        draw3 = ImageDraw.Draw(img)
        ly = by + bh2 + int(h * 0.03)
        m = int(w * 0.12)
        draw3.line([x + m, ly, x + w - m, ly], fill=_rgba(accent, 140), width=2)

        # Small dots on divider
        for dx in range(x + m, x + w - m, int(w * 0.06)):
            draw3.ellipse([dx - 3, ly - 3, dx + 3, ly + 3], fill=_rgba(accent, 160))

        return {"title_y_pct": 0.19, "subtitle_y_pct": 0.50, "author_y_pct": 0.86,
                "title_font_size": 74}

    # ==================================================================
    # LAYOUT 1: GRADIENT BAND — rich dual gradient + bold accent band
    # ==================================================================

    def _layout_gradient_band(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        # Dual-tone gradient (primary → accent-tinted dark)
        dark = _darken(_blend(primary, accent, 0.15), 0.3)
        _vgradient(draw, x, y, w, h, primary, dark)

        # Accent band with inner gradient
        bp = rng.uniform(0.30, 0.38)
        bh = int(h * rng.uniform(0.16, 0.22))
        bt = y + int(h * bp)
        _vgradient(draw, x, bt, w, bh, accent, _darken(accent, 0.7))

        # Band edge highlights
        draw.line([x, bt, x + w, bt], fill=_rgba(secondary, 130), width=2)
        draw.line([x, bt + bh, x + w, bt + bh], fill=_rgba(secondary, 130), width=2)
        # Inner thin gold-ish lines
        draw.line([x + 15, bt + 6, x + w - 15, bt + 6], fill=_rgba(secondary, 50), width=1)
        draw.line([x + 15, bt + bh - 6, x + w - 15, bt + bh - 6], fill=_rgba(secondary, 50), width=1)

        # Subtle top decoration
        for i in range(3):
            oy = y + int(h * 0.05) + i * 12
            m = int(w * (0.30 - i * 0.05))
            draw.line([x + m, oy, x + w - m, oy], fill=_rgba(accent, 40 + i * 15), width=1)

        # Author area underline
        ay = y + int(h * 0.88)
        m = int(w * 0.25)
        draw.line([x + m, ay, x + w - m, ay], fill=_rgba(accent, 100), width=1)

        return {
            "title_y_pct": bp + 0.02, "title_font_size": 70,
            "subtitle_y_pct": bp + bh / h + 0.04,
            "author_y_pct": 0.83, "text_color": secondary,
        }

    # ==================================================================
    # LAYOUT 2: FRAME — elegant triple border with ornaments
    # ==================================================================

    def _layout_frame(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        # Subtle gradient base
        _vgradient(draw, x, y, w, h, primary, _darken(primary, 0.7))

        i1 = int(min(w, h) * 0.05)
        i2 = int(min(w, h) * 0.08)
        i3 = int(min(w, h) * 0.11)

        # Three nested frames
        draw.rectangle([x + i1, y + i1, x + w - i1, y + h - i1],
                       outline=_rgba(accent, 255), width=5)
        draw.rectangle([x + i2, y + i2, x + w - i2, y + h - i2],
                       outline=_rgba(accent, 120), width=2)
        draw.rectangle([x + i3, y + i3, x + w - i3, y + h - i3],
                       outline=_rgba(accent, 70), width=1)

        # Corner diamonds (larger, filled with gradient feel)
        ds = int(min(w, h) * 0.05)
        corners = [(x + i1, y + i1), (x + w - i1, y + i1),
                   (x + i1, y + h - i1), (x + w - i1, y + h - i1)]
        for cx_d, cy_d in corners:
            # Outer diamond
            draw.polygon([(cx_d, cy_d - ds), (cx_d + ds, cy_d),
                          (cx_d, cy_d + ds), (cx_d - ds, cy_d)],
                         fill=_rgba(accent, 220))
            # Inner diamond
            s2 = ds // 2
            draw.polygon([(cx_d, cy_d - s2), (cx_d + s2, cy_d),
                          (cx_d, cy_d + s2), (cx_d - s2, cy_d)],
                         fill=_rgba(primary, 200))

        # Corner arcs (thicker)
        ar = int(min(w, h) * 0.10)
        draw.arc([x + i2, y + i2, x + i2 + ar, y + i2 + ar], 180, 270,
                 fill=_rgba(accent, 200), width=3)
        draw.arc([x + w - i2 - ar, y + i2, x + w - i2, y + i2 + ar], 270, 360,
                 fill=_rgba(accent, 200), width=3)
        draw.arc([x + i2, y + h - i2 - ar, x + i2 + ar, y + h - i2], 90, 180,
                 fill=_rgba(accent, 200), width=3)
        draw.arc([x + w - i2 - ar, y + h - i2 - ar, x + w - i2, y + h - i2], 0, 90,
                 fill=_rgba(accent, 200), width=3)

        # Ornamental dividers (double line with dots)
        my = y + int(h * 0.47)
        m = int(w * 0.18)
        draw.line([x + m, my, x + w - m, my], fill=_rgba(accent, 160), width=2)
        draw.line([x + m, my + 10, x + w - m, my + 10], fill=_rgba(accent, 90), width=1)
        # Center ornament
        ocx = x + w // 2
        draw.ellipse([ocx - 8, my - 4, ocx + 8, my + 14], fill=_rgba(accent, 180))
        draw.ellipse([ocx - 4, my, ocx + 4, my + 10], fill=_rgba(primary, 220))

        # Side flourishes
        for offset in [m + 10, w - m - 10]:
            fx = x + offset
            draw.ellipse([fx - 4, my + 1, fx + 4, my + 9], fill=_rgba(accent, 130))

        return {"title_y_pct": 0.16, "subtitle_y_pct": 0.52,
                "author_y_pct": 0.80, "margin_inches": 0.9}

    # ==================================================================
    # LAYOUT 3: SPLIT — bold diagonal/horizontal with texture
    # ==================================================================

    def _layout_split(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        diagonal = rng.random() > 0.5

        # Gradient on primary side
        _vgradient(draw, x, y, w, h, primary, _darken(primary, 0.5))

        if diagonal:
            sp = rng.uniform(0.30, 0.70)
            pts = [(x + int(w * sp), y), (x + w, y), (x + w, y + h),
                   (x + int(w * (1 - sp)), y + h)]
            # Accent polygon with gradient simulation
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.polygon(pts, fill=_rgba(accent, 200))
            # Lighter overlay at top
            ld.polygon(pts[:2] + [(x + w, y + h // 3), (x + int(w * (sp + 0.1)), y)],
                       fill=_rgba(_lighten(accent, 0.2), 50))
            img = Image.alpha_composite(img, layer)
            draw2 = ImageDraw.Draw(img)
            # Edge line with glow
            draw2.line([(x + int(w * sp), y), (x + int(w * (1 - sp)), y + h)],
                       fill=_rgba(secondary, 220), width=5)
            draw2.line([(x + int(w * sp) + 6, y), (x + int(w * (1 - sp)) + 6, y + h)],
                       fill=_rgba(secondary, 60), width=2)
        else:
            sp_y = y + int(h * rng.uniform(0.38, 0.52))
            # Accent top half with gradient
            _vgradient(draw, x, y, w, sp_y - y, _lighten(accent, 0.15), accent)
            draw.line([x, sp_y, x + w, sp_y], fill=_rgba(secondary, 220), width=5)
            draw.line([x, sp_y + 6, x + w, sp_y + 6], fill=_rgba(secondary, 60), width=2)

        # Title backdrop panel
        layer2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld2 = ImageDraw.Draw(layer2)
        py = y + int(h * 0.12)
        ph = int(h * 0.28)
        ld2.rounded_rectangle([x + int(w * 0.06), py, x + int(w * 0.94), py + ph],
                              radius=15, fill=_rgba(primary, 180))
        img = Image.alpha_composite(img, layer2)

        return {"title_y_pct": 0.14, "title_font_size": 78,
                "subtitle_y_pct": 0.46, "author_y_pct": 0.86}

    # ==================================================================
    # LAYOUT 4: PATTERN — rich tiled pattern with gradient base
    # ==================================================================

    def _layout_pattern(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        # Gradient base
        _vgradient(draw, x, y, w, h, primary, _darken(primary, 0.55))

        pat = rng.choice(["dots", "diamonds", "hexagons", "crosses"])
        spacing = w // rng.randint(9, 13)
        jitter = int(spacing * 0.12)

        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        base_alpha = rng.randint(30, 55)
        sz = max(5, spacing // 3)

        row = 0
        cy = y + spacing // 2
        while cy < y + h:
            cx = x + spacing // 2 + (spacing // 2 if row % 2 else 0)
            while cx < x + w:
                jx = cx + rng.randint(-jitter, jitter)
                jy = cy + rng.randint(-jitter, jitter)
                # Fade alpha towards edges for depth
                dist_from_center = abs(jy - (y + h // 2)) / (h // 2)
                alpha = int(base_alpha * (1.0 - dist_from_center * 0.5))
                color = accent if rng.random() > 0.25 else _lighten(accent, 0.3)

                if pat == "dots":
                    ld.ellipse([jx - sz, jy - sz, jx + sz, jy + sz], fill=_rgba(color, alpha))
                elif pat == "diamonds":
                    ld.polygon([(jx, jy - sz), (jx + sz, jy), (jx, jy + sz), (jx - sz, jy)],
                               fill=_rgba(color, alpha))
                elif pat == "hexagons":
                    pts = [(jx + int(sz * math.cos(math.radians(a + 30))),
                            jy + int(sz * math.sin(math.radians(a + 30))))
                           for a in range(0, 360, 60)]
                    ld.polygon(pts, fill=_rgba(color, alpha))
                elif pat == "crosses":
                    s2 = sz // 2
                    ld.rectangle([jx - s2, jy - sz, jx + s2, jy + sz], fill=_rgba(color, alpha))
                    ld.rectangle([jx - sz, jy - s2, jx + sz, jy + s2], fill=_rgba(color, alpha))

                cx += spacing
            cy += spacing
            row += 1

        img = Image.alpha_composite(img, layer)

        # Title panel
        layer2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld2 = ImageDraw.Draw(layer2)
        py = y + int(h * 0.14)
        ph = int(h * 0.28)
        ld2.rounded_rectangle([x + int(w * 0.05), py, x + int(w * 0.95), py + ph],
                              radius=18, fill=_rgba(primary, 200))
        # Panel border
        ld2.rounded_rectangle([x + int(w * 0.05), py, x + int(w * 0.95), py + ph],
                              radius=18, outline=_rgba(accent, 80), width=2)
        img = Image.alpha_composite(img, layer2)

        # Author underline
        draw3 = ImageDraw.Draw(img)
        ay = y + int(h * 0.88)
        m = int(w * 0.20)
        draw3.line([x + m, ay, x + w - m, ay], fill=_rgba(accent, 110), width=2)

        return {"title_y_pct": 0.17, "subtitle_y_pct": 0.48, "author_y_pct": 0.83,
                "title_font_size": 72}

    # ==================================================================
    # LAYOUT 5: MINIMAL MODERN — bold type, subtle elegance
    # ==================================================================

    def _layout_minimal_modern(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        # Very subtle gradient
        _vgradient(draw, x, y, w, h, primary, _blend(primary, accent, 0.08))

        # Large accent block at top
        block_h = int(h * 0.06)
        draw.rectangle([x, y, x + w, y + block_h], fill=_rgba(accent, 230))
        # Gradient fade below block
        for i in range(40):
            a = int(60 * (1.0 - i / 40.0))
            draw.line([x, y + block_h + i, x + w, y + block_h + i],
                      fill=_rgba(accent, a))

        # Thin accent line with ornaments
        ly = y + int(h * 0.60)
        m = int(w * 0.18)
        draw.line([x + m, ly, x + w - m, ly], fill=_rgba(accent, 180), width=2)
        # Center diamond ornament
        ocx = x + w // 2
        ds = 10
        draw.polygon([(ocx, ly - ds), (ocx + ds, ly), (ocx, ly + ds), (ocx - ds, ly)],
                     fill=_rgba(accent, 220))
        draw.polygon([(ocx, ly - ds + 3), (ocx + ds - 3, ly), (ocx, ly + ds - 3), (ocx - ds + 3, ly)],
                     fill=_rgba(primary, 220))
        # End dots
        draw.ellipse([x + m - 4, ly - 4, x + m + 4, ly + 4], fill=_rgba(accent, 180))
        draw.ellipse([x + w - m - 4, ly - 4, x + w - m + 4, ly + 4], fill=_rgba(accent, 180))

        # Bottom accent bar
        bb_y = y + h - int(h * 0.04)
        draw.rectangle([x, bb_y, x + w, y + h], fill=_rgba(accent, 200))

        # Author area thin lines
        ay = y + int(h * 0.87)
        m2 = int(w * 0.30)
        draw.line([x + m2, ay, x + w - m2, ay], fill=_rgba(accent, 80), width=1)
        draw.line([x + m2, ay + 6, x + w - m2, ay + 6], fill=_rgba(accent, 50), width=1)

        return {
            "title_y_pct": 0.25, "title_font_size": 96,
            "subtitle_y_pct": 0.64, "subtitle_font_size": 30,
            "author_y_pct": 0.82, "author_font_size": 30,
            "margin_inches": 0.7,
        }

    # ==================================================================
    # LAYOUT 6: WATERCOLOR — organic blurred blobs with depth
    # ==================================================================

    def _layout_watercolor(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        # Gradient base
        _vgradient(draw, x, y, w, h, _lighten(primary, 0.1), _darken(primary, 0.3))

        # Large soft blobs
        for _ in range(rng.randint(7, 12)):
            blob = Image.new("RGBA", img.size, (0, 0, 0, 0))
            bd = ImageDraw.Draw(blob)
            cx = x + rng.randint(int(w * -0.1), int(w * 1.1))
            cy = y + rng.randint(int(h * -0.1), int(h * 1.1))
            rx = rng.randint(int(w * 0.12), int(w * 0.45))
            ry = rng.randint(int(h * 0.08), int(h * 0.35))
            alpha = rng.randint(35, 80)
            colors = [accent, _lighten(accent, 0.3), _blend(accent, secondary, 0.4),
                      _blend(primary, accent, 0.6)]
            color = rng.choice(colors)
            bd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=_rgba(color, alpha))
            blur_r = rng.randint(30, 60)
            blob = blob.filter(ImageFilter.GaussianBlur(radius=blur_r))
            img = Image.alpha_composite(img, blob)

        # Bright accent spots
        for _ in range(rng.randint(3, 6)):
            spot = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(spot)
            cx = x + rng.randint(int(w * 0.1), int(w * 0.9))
            cy = y + rng.randint(int(h * 0.1), int(h * 0.9))
            r = rng.randint(int(w * 0.05), int(w * 0.12))
            sd.ellipse([cx - r, cy - r, cx + r, cy + r],
                       fill=_rgba(_lighten(accent, 0.4), rng.randint(30, 60)))
            spot = spot.filter(ImageFilter.GaussianBlur(radius=rng.randint(15, 30)))
            img = Image.alpha_composite(img, spot)

        # Title backdrop
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        py = y + int(h * 0.14)
        ph = int(h * 0.32)
        ld.rounded_rectangle([x + int(w * 0.04), py, x + int(w * 0.96), py + ph],
                             radius=25, fill=_rgba(primary, 160))
        layer = layer.filter(ImageFilter.GaussianBlur(radius=5))
        img = Image.alpha_composite(img, layer)

        # Re-draw sharper panel border
        draw2 = ImageDraw.Draw(img)
        draw2.rounded_rectangle([x + int(w * 0.04), py, x + int(w * 0.96), py + ph],
                                radius=25, outline=_rgba(secondary, 50), width=2)

        return {"title_y_pct": 0.17, "subtitle_y_pct": 0.52, "author_y_pct": 0.84,
                "title_font_size": 72}

    # ==================================================================
    # LAYOUT 7: LAYERED SHAPES — bold abstract composition
    # ==================================================================

    def _layout_layered_shapes(self, img, draw, x, y, w, h, primary, secondary, accent, rng) -> dict:
        # Rich gradient base
        _vgradient(draw, x, y, w, h, primary, _darken(_blend(primary, accent, 0.1), 0.4))

        # Large background shapes (low opacity, blurred)
        bg_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bld = ImageDraw.Draw(bg_layer)
        for _ in range(rng.randint(4, 7)):
            sx = x + rng.randint(-int(w * 0.1), int(w * 0.9))
            sy = y + rng.randint(-int(h * 0.1), int(h * 0.9))
            sw = rng.randint(int(w * 0.20), int(w * 0.50))
            sh = rng.randint(int(h * 0.15), int(h * 0.40))
            alpha = rng.randint(25, 50)
            color = rng.choice([accent, _lighten(accent, 0.3), _blend(accent, secondary, 0.3)])
            if rng.random() > 0.4:
                bld.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=15,
                                      fill=_rgba(color, alpha))
            else:
                r = (sw + sh) // 4
                bld.ellipse([sx, sy, sx + r * 2, sy + r * 2], fill=_rgba(color, alpha))

        bg_layer = bg_layer.filter(ImageFilter.GaussianBlur(radius=8))
        img = Image.alpha_composite(img, bg_layer)

        # Foreground sharp shapes (higher opacity)
        fg_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        fld = ImageDraw.Draw(fg_layer)
        for _ in range(rng.randint(6, 12)):
            sx = x + rng.randint(0, w)
            sy = y + rng.randint(0, h)
            sw = rng.randint(int(w * 0.06), int(w * 0.25))
            sh = rng.randint(int(h * 0.04), int(h * 0.18))
            alpha = rng.randint(35, 75)
            color = rng.choice([accent, _lighten(accent, 0.2), _darken(accent, 0.7)])
            if rng.random() > 0.5:
                r = (sw + sh) // 4
                fld.ellipse([sx - r, sy - r, sx + r, sy + r], fill=_rgba(color, alpha))
            else:
                fld.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=8,
                                      fill=_rgba(color, alpha))
                # Outline on some
                if rng.random() > 0.6:
                    fld.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=8,
                                          outline=_rgba(secondary, alpha // 2), width=2)
        img = Image.alpha_composite(img, fg_layer)

        # Title backdrop
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        py = y + int(h * 0.12)
        ph = int(h * 0.33)
        ld.rounded_rectangle([x + int(w * 0.03), py, x + int(w * 0.97), py + ph],
                             radius=18, fill=_rgba(primary, 185))
        ld.rounded_rectangle([x + int(w * 0.03), py, x + int(w * 0.97), py + ph],
                             radius=18, outline=_rgba(accent, 60), width=2)
        img = Image.alpha_composite(img, layer)

        # Author strip
        layer2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld2 = ImageDraw.Draw(layer2)
        ay = y + int(h * 0.78)
        ah = int(h * 0.10)
        ld2.rounded_rectangle([x + int(w * 0.10), ay, x + int(w * 0.90), ay + ah],
                              radius=12, fill=_rgba(primary, 160))
        img = Image.alpha_composite(img, layer2)

        return {"title_y_pct": 0.15, "title_font_size": 76,
                "subtitle_y_pct": 0.34, "author_y_pct": 0.80}
