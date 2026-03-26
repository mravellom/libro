"""AI background generation for book covers using Stable Diffusion on CPU.

Generates unique, high-quality background images per niche/variant using
SD Turbo (1-4 inference steps) running on CPU. Images are cached so each
variant only generates once.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Prompt templates by niche category for high-quality backgrounds
STYLE_PROMPTS = {
    # Floral / botanical — most popular for women's journals
    "floral": (
        "elegant watercolor floral border frame, soft pink roses and eucalyptus leaves, "
        "delicate botanical illustration, pastel colors, white center space for text, "
        "high quality, detailed, feminine, book cover design"
    ),
    "botanical": (
        "lush green botanical leaf pattern border, tropical monstera and fern leaves, "
        "watercolor illustration, soft natural tones, clean center area, "
        "elegant book cover background, detailed foliage"
    ),
    # Watercolor / artistic
    "watercolor": (
        "abstract watercolor wash background, soft blending pastel colors, "
        "pink lavender and gold tones, organic paint splashes, artistic texture, "
        "elegant feminine design, book cover background"
    ),
    "sunset": (
        "dreamy watercolor sunset sky background, soft gradient from peach to lavender, "
        "golden clouds, serene and peaceful atmosphere, artistic book cover background"
    ),
    # Texture / premium
    "marble": (
        "elegant white and gold marble texture background, luxury veining pattern, "
        "sophisticated book cover design, premium quality, clean and modern"
    ),
    "linen": (
        "soft linen fabric texture background, natural beige tones, subtle woven pattern, "
        "clean minimal design, elegant book cover background, organic feel"
    ),
    # Nature / wellness
    "nature": (
        "serene nature landscape background, soft morning light through trees, "
        "misty forest with green tones, peaceful wellness atmosphere, book cover design"
    ),
    "ocean": (
        "calming ocean waves watercolor background, soft blue and turquoise tones, "
        "beach serenity, peaceful water texture, elegant book cover design"
    ),
    # Mindfulness / spiritual
    "mandala": (
        "delicate golden mandala pattern on dark blue background, sacred geometry, "
        "spiritual zen design, elegant line art, meditation book cover"
    ),
    "zen": (
        "minimalist zen stone garden background, soft sand texture with ripples, "
        "peaceful neutral tones, calm and balanced, meditation book cover design"
    ),
    # Default / generic
    "default": (
        "elegant abstract background with soft gradient, pastel colors blending smoothly, "
        "modern and clean design, book cover background, feminine and sophisticated"
    ),
}

# Map niche keywords to style categories
NICHE_TO_STYLE = {
    "journal": "floral",
    "gratitude": "watercolor",
    "mindfulness": "zen",
    "meditation": "mandala",
    "prayer": "mandala",
    "dream": "sunset",
    "fitness": "nature",
    "running": "nature",
    "yoga": "zen",
    "planner": "botanical",
    "tracker": "linen",
    "log": "botanical",
    "notebook": "floral",
    "practice": "watercolor",
    "recipe": "floral",
    "reading": "linen",
    "music": "watercolor",
    "garden": "botanical",
    "wellness": "nature",
    "self-care": "watercolor",
    "budget": "marble",
    "savings": "marble",
    "income": "marble",
    "manifestation": "sunset",
    "affirmation": "sunset",
    "pet": "watercolor",
    "baby": "floral",
    "pregnancy": "floral",
    "wedding": "floral",
    "travel": "ocean",
    "fishing": "ocean",
}

# Negative prompt to avoid bad generations
NEGATIVE_PROMPT = (
    "text, words, letters, numbers, watermark, logo, signature, blurry, "
    "low quality, distorted, ugly, deformed, disfigured, bad anatomy, "
    "photograph of people, faces, hands, fingers"
)


def _get_style_for_niche(niche_keyword: str) -> str:
    """Map a niche keyword to a style category."""
    niche_lower = niche_keyword.lower()
    for keyword, style in NICHE_TO_STYLE.items():
        if keyword in niche_lower:
            return style
    return "default"


def _get_cache_path(variant_id: int, output_dir: Path) -> Path:
    """Get the cached background image path."""
    return output_dir / f"bg_{variant_id}.png"


def generate_background(
    variant_id: int,
    niche_keyword: str,
    output_dir: Path,
    width: int = 512,
    height: int = 768,
    seed: int | None = None,
    num_steps: int = 4,
    force: bool = False,
) -> Path | None:
    """Generate an AI background image for a book cover.

    Uses SD Turbo on CPU. Slow (~3-8 min) but free and produces quality results.
    Images are cached — subsequent calls return the cached path immediately.

    Args:
        variant_id: For cache key.
        niche_keyword: e.g. "mindfulness journal" — mapped to a style prompt.
        output_dir: Where to save the generated image.
        width: Image width (512 recommended for speed).
        height: Image height (768 for portrait book covers).
        seed: Reproducibility seed.
        num_steps: Inference steps (1-4 for SD Turbo, more = better quality).
        force: Regenerate even if cached.

    Returns:
        Path to the generated PNG, or None on failure.
    """
    cache_path = _get_cache_path(variant_id, output_dir)

    if cache_path.exists() and not force:
        log.info(f"Background cached: {cache_path}")
        return cache_path

    output_dir.mkdir(parents=True, exist_ok=True)

    style = _get_style_for_niche(niche_keyword)
    prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["default"])

    log.info(f"Generating background for variant #{variant_id} (style={style}, steps={num_steps})...")
    log.info("This may take 3-8 minutes on CPU...")

    try:
        import torch
        from diffusers import AutoPipelineForText2Image

        pipe = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sd-turbo",
            torch_dtype=torch.float32,
            variant="fp16",
        )
        pipe.to("cpu")

        # Seed for reproducibility
        generator = torch.Generator("cpu")
        if seed is not None:
            generator.manual_seed(seed)

        result = pipe(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            num_inference_steps=num_steps,
            guidance_scale=0.0,  # SD Turbo doesn't use guidance
            width=width,
            height=height,
            generator=generator,
        )

        image = result.images[0]
        image.save(str(cache_path))
        log.info(f"Background generated: {cache_path} ({width}x{height})")

        # Free memory
        del pipe
        if hasattr(torch, 'cuda'):
            torch.cuda.empty_cache()
        import gc
        gc.collect()

        return cache_path

    except Exception as e:
        log.error(f"Background generation failed: {e}")
        return None


def has_cached_background(variant_id: int, output_dir: Path) -> bool:
    """Check if a background is already cached."""
    return _get_cache_path(variant_id, output_dir).exists()
