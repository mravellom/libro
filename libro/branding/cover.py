"""Cover generation — creates KDP-compliant book covers using Pillow."""

import json
import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from libro.common.pdf_utils import get_cover_dimensions, CoverDimensions

log = logging.getLogger(__name__)

# KDP requires 300 DPI minimum
DPI = 300


def _inches_to_px(inches: float) -> int:
    return int(inches * DPI)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Try to load a font, fall back to default."""
    # Common font paths on Linux
    font_paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVu{name}.ttf",
        f"/usr/share/fonts/truetype/liberation/Liberation{name}-Regular.ttf",
        f"/usr/share/fonts/truetype/freefont/Free{name}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-Regular.ttf",
    ]

    # Map generic names to DejaVu variants
    dejavu_map = {
        "Sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "Sans-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "Serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "Serif-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    }

    if name in dejavu_map:
        try:
            return ImageFont.truetype(dejavu_map[name], size)
        except OSError:
            pass

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue

    # Last resort: try any available system font
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        log.warning("No TrueType fonts found, using default bitmap font")
        return ImageFont.load_default()


class CoverGenerator:
    """Generates KDP-compliant book covers."""

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
    ) -> Path:
        """Generate a complete book cover (front + spine + back).

        Args:
            title: Book title.
            subtitle: Optional subtitle.
            author: Author/brand name.
            trim_size: KDP trim size.
            page_count: For spine width calculation.
            output_path: Where to save. Auto-generated if None.
            primary_color: Main background color (hex).
            secondary_color: Text/accent color (hex).
            accent_color: Decorative elements color (hex).
            font_name: Font family name.
            template_path: Optional background image to use as template.

        Returns:
            Path to generated cover image (PNG at 300 DPI).
        """
        dims = get_cover_dimensions(trim_size, page_count)
        total_w = _inches_to_px(dims.total_width)
        total_h = _inches_to_px(dims.total_height)

        # Create canvas
        if template_path and template_path.exists():
            img = Image.open(template_path).resize((total_w, total_h))
        else:
            bg_color = _hex_to_rgb(primary_color)
            img = Image.new("RGB", (total_w, total_h), bg_color)

        draw = ImageDraw.Draw(img)

        # Calculate zones
        bleed_px = _inches_to_px(dims.bleed)
        front_w = _inches_to_px(dims.width)
        spine_w = _inches_to_px(dims.spine_width)
        back_w = front_w

        # Front cover zone (right side)
        front_left = bleed_px + back_w + spine_w
        front_right = front_left + front_w
        front_center_x = front_left + front_w // 2

        # Draw decorative elements on front cover
        self._draw_front_decoration(
            draw, front_left, bleed_px, front_w, total_h - 2 * bleed_px,
            _hex_to_rgb(accent_color), _hex_to_rgb(secondary_color)
        )

        # Draw title
        text_color = _hex_to_rgb(secondary_color)
        title_font = _get_font(f"{font_name}-Bold", 72)
        self._draw_centered_text(
            draw, title, front_center_x,
            bleed_px + _inches_to_px(1.8),
            front_w - _inches_to_px(1.0),
            title_font, text_color
        )

        # Draw subtitle
        if subtitle:
            subtitle_font = _get_font(font_name, 36)
            self._draw_centered_text(
                draw, subtitle, front_center_x,
                bleed_px + _inches_to_px(4.0),
                front_w - _inches_to_px(1.2),
                subtitle_font, text_color
            )

        # Draw author
        if author:
            author_font = _get_font(font_name, 32)
            author_y = total_h - bleed_px - _inches_to_px(1.2)
            self._draw_centered_text(
                draw, author, front_center_x,
                author_y,
                front_w - _inches_to_px(1.0),
                author_font, text_color
            )

        # Draw spine text (if spine is wide enough)
        if spine_w > _inches_to_px(0.3):
            spine_left = bleed_px + back_w
            spine_center_x = spine_left + spine_w // 2
            self._draw_spine(
                draw, title, author, spine_center_x,
                bleed_px, total_h - 2 * bleed_px,
                spine_w, font_name, text_color, img
            )

        # Draw back cover
        back_left = bleed_px
        back_center_x = back_left + back_w // 2
        self._draw_back_cover(
            draw, back_center_x, bleed_px, back_w,
            total_h - 2 * bleed_px, font_name,
            text_color, _hex_to_rgb(accent_color)
        )

        # Save
        if output_path is None:
            output_path = Path("cover.png")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        img.save(str(output_path), dpi=(DPI, DPI))
        log.info(f"Cover generated: {output_path} ({total_w}x{total_h} px)")
        return output_path

    def _draw_front_decoration(
        self, draw: ImageDraw.Draw,
        x: int, y: int, w: int, h: int,
        accent: tuple, secondary: tuple
    ) -> None:
        """Draw decorative elements on front cover."""
        # Top accent bar
        bar_h = int(h * 0.02)
        draw.rectangle([x, y, x + w, y + bar_h], fill=accent)

        # Bottom accent bar
        draw.rectangle([x, y + h - bar_h, x + w, y + h], fill=accent)

        # Decorative line under title area
        line_y = y + int(h * 0.45)
        line_margin = int(w * 0.15)
        draw.line(
            [x + line_margin, line_y, x + w - line_margin, line_y],
            fill=(*accent, 180), width=3
        )

    def _draw_centered_text(
        self, draw: ImageDraw.Draw,
        text: str, center_x: int, y: int, max_width: int,
        font: ImageFont.FreeTypeFont, color: tuple
    ) -> int:
        """Draw text centered horizontally, wrapping if needed. Returns bottom y."""
        # Estimate chars per line
        avg_char_w = font.size * 0.55
        chars_per_line = max(10, int(max_width / avg_char_w))
        lines = textwrap.wrap(text, width=chars_per_line)

        current_y = y
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text(
                (center_x - text_w // 2, current_y),
                line, font=font, fill=color
            )
            current_y += text_h + 10

        return current_y

    def _draw_spine(
        self, draw: ImageDraw.Draw,
        title: str, author: str | None,
        center_x: int, top_y: int, height: int, spine_w: int,
        font_name: str, color: tuple, img: Image.Image
    ) -> None:
        """Draw rotated text on spine."""
        # Create a temporary image for rotated text
        spine_font_size = max(14, min(24, spine_w - 10))
        font = _get_font(font_name, spine_font_size)

        spine_text = title[:40]
        if author:
            spine_text += f"  |  {author}"

        # Create text image
        bbox = font.getbbox(spine_text)
        text_w = bbox[2] - bbox[0] + 20
        text_h = bbox[3] - bbox[1] + 10

        txt_img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((10, 5), spine_text, font=font, fill=(*color, 255))

        # Rotate 90 degrees (bottom to top reading direction)
        rotated = txt_img.rotate(90, expand=True)

        # Paste centered on spine
        paste_x = center_x - rotated.width // 2
        paste_y = top_y + (height - rotated.height) // 2

        img.paste(rotated, (paste_x, paste_y), rotated)

    def _draw_back_cover(
        self, draw: ImageDraw.Draw,
        center_x: int, top_y: int, width: int, height: int,
        font_name: str, text_color: tuple, accent: tuple
    ) -> None:
        """Draw minimal back cover content."""
        font = _get_font(font_name, 24)
        y = top_y + int(height * 0.4)

        # Simple barcode placeholder area
        bar_w = _inches_to_px(2.0)
        bar_h = _inches_to_px(1.2)
        bar_x = center_x - bar_w // 2
        bar_y = top_y + height - _inches_to_px(1.5) - bar_h

        draw.rectangle(
            [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
            fill=(255, 255, 255), outline=(200, 200, 200), width=2
        )

        barcode_font = _get_font(font_name, 16)
        draw.text(
            (bar_x + 10, bar_y + bar_h // 2 - 10),
            "ISBN / Barcode Area",
            font=barcode_font, fill=(150, 150, 150)
        )
