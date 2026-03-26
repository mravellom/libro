"""Title engine — generates compelling, market-aware book titles.

Replaces mechanical combinatorial titles with persona-driven, hook-based
titles that target specific buyer pain points and emotions.
"""

import logging
import random
from dataclasses import dataclass

from libro.generation.personas import Persona

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Title templates organized by emotional angle
# ---------------------------------------------------------------------------

# {hook} comes from persona.title_hooks
# {keyword} is the niche keyword (title-cased)
# {time} comes from persona.time_framing
# {audience} comes from persona.label

HOOK_FIRST_TEMPLATES = [
    "{hook}: A {time} {keyword} Journal",
    "{hook}: The {keyword} Journal for {audience}",
    "{hook} — {time} {keyword} Companion",
    "{hook}: Your Personal {keyword} Guide",
]

KEYWORD_FIRST_TEMPLATES = [
    "{keyword} Journal: {hook}",
    "The {time} {keyword} Journal — {hook}",
    "{keyword} for {audience}: {hook}",
    "{time} {keyword}: {hook}",
]

BENEFIT_TEMPLATES = [
    "{hook} — A Guided {keyword} Journal",
    "{hook}: {time} Prompts for {audience}",
    "The {keyword} Workbook: {hook}",
    "{hook}: A Practical {keyword} Notebook",
]

ALL_TEMPLATE_SETS = [
    HOOK_FIRST_TEMPLATES,
    KEYWORD_FIRST_TEMPLATES,
    BENEFIT_TEMPLATES,
]


# ---------------------------------------------------------------------------
# Subtitle templates — more descriptive, keyword-rich
# ---------------------------------------------------------------------------

SUBTITLE_TEMPLATES = [
    "A {time} Guided Journal for {pain_point}",
    "{time} Prompts and Exercises for {audience}",
    "A Practical Workbook to {benefit}",
    "Guided Prompts for {audience} — {time} Edition",
    "{time} Pages to {benefit}",
    "The Complete {keyword} Companion for {audience}",
]


# ---------------------------------------------------------------------------
# Description templates — copywriting with benefits and bullet points
# ---------------------------------------------------------------------------

DESCRIPTION_TEMPLATE = """\
{opening_hook}

{value_proposition}

What's Inside:
{bullet_points}

Perfect For:
{audience_bullets}

Specs:
• {page_count} thoughtfully designed pages
• {trim_size} portable size — fits in your bag
• Premium matte cover
• Printed on quality white paper

{closing_cta}"""

OPENING_HOOKS = [
    "Tired of {pain_point}? This journal was designed with you in mind.",
    "You deserve more than a blank notebook. You deserve a system.",
    "What if {time_lower} of journaling could change everything?",
    "This isn't just another {keyword} — it's your personal roadmap.",
    "The hardest part is showing up. This journal makes it easy.",
]

CLOSING_CTAS = [
    "Start today. Your future self will thank you.",
    "Scroll up and click 'Buy Now' to begin your journey.",
    "Make today the day you start. Add to cart now.",
    "Every great transformation starts with a single page. Start yours today.",
    "Don't wait for the perfect moment — create it. Order now.",
]


@dataclass
class GeneratedTitle:
    """A generated title with all metadata."""
    title: str
    subtitle: str
    description: str
    keywords: list[str]
    persona_name: str


def generate_title(
    niche_keyword: str,
    persona: Persona,
    seed: int,
    interior_type: str = "lined",
    page_count: int = 120,
    trim_size: str = "6x9",
    competitor_keywords: list[str] | None = None,
) -> GeneratedTitle:
    """Generate a compelling title, subtitle, and description.

    Args:
        niche_keyword: The niche (e.g., "anxiety journal").
        persona: Target buyer persona.
        seed: For reproducible randomness.
        interior_type: The interior template being used.
        page_count: Number of pages.
        trim_size: KDP trim size.
        competitor_keywords: Optional keywords from competitor analysis.

    Returns:
        GeneratedTitle with title, subtitle, description, and keywords.
    """
    rng = random.Random(seed)

    keyword = _clean_keyword(niche_keyword)
    hook = rng.choice(persona.title_hooks)
    time = persona.time_framing
    audience = persona.label

    # --- Title ---
    template_set = rng.choice(ALL_TEMPLATE_SETS)
    template = rng.choice(template_set)
    title = template.format(
        hook=hook,
        keyword=keyword,
        time=time,
        audience=audience,
    )

    # Ensure title doesn't exceed KDP limit
    if len(title) > 200:
        title = title[:197] + "..."

    # --- Subtitle ---
    pain_point = rng.choice(persona.pain_points)
    benefit = _pain_to_benefit(pain_point)
    sub_template = rng.choice(SUBTITLE_TEMPLATES)
    subtitle = sub_template.format(
        time=time,
        audience=audience,
        pain_point=pain_point,
        benefit=benefit,
        keyword=keyword,
    )

    if len(subtitle) > 200:
        subtitle = subtitle[:197] + "..."

    # --- Description ---
    description = _generate_description(
        niche_keyword=niche_keyword,
        persona=persona,
        interior_type=interior_type,
        page_count=page_count,
        trim_size=trim_size,
        seed=seed,
    )

    # --- Keywords (max 7) ---
    keywords = _generate_keywords(
        niche_keyword, persona, competitor_keywords,
    )

    return GeneratedTitle(
        title=title,
        subtitle=subtitle,
        description=description,
        keywords=keywords,
        persona_name=persona.name,
    )


def _clean_keyword(niche_keyword: str) -> str:
    """Remove trailing type words to avoid duplication in templates.

    E.g., "anxiety journal" → "Anxiety" (since templates add "Journal").
    """
    type_words = {"journal", "notebook", "planner", "log", "tracker", "diary", "logbook", "book"}
    words = niche_keyword.strip().split()
    # Only strip if the keyword has more than one word and ends with a type word
    if len(words) > 1 and words[-1].lower() in type_words:
        return " ".join(words[:-1]).title()
    return niche_keyword.title()


def _pain_to_benefit(pain_point: str) -> str:
    """Convert a pain point into a positive benefit statement."""
    mappings = {
        "burnout": "Recover Your Energy",
        "work-life balance": "Find Your Balance",
        "mental clarity": "Gain Mental Clarity",
        "postpartum anxiety": "Find Calm in the Chaos",
        "sleep deprivation": "Rest Better",
        "self-identity": "Rediscover Yourself",
        "racing thoughts": "Quiet Your Mind",
        "overwhelm": "Feel In Control Again",
        "panic episodes": "Build Inner Calm",
        "don't know where to start": "Take the First Step",
        "lack of consistency": "Build Lasting Habits",
        "intimidation": "Build Confidence",
        "accountability": "Stay Accountable",
        "emotional eating": "Understand Your Patterns",
        "plateaus": "Break Through Plateaus",
        "debt stress": "Take Control of Your Money",
        "no savings": "Build Your Safety Net",
        "financial illiteracy": "Master Your Finances",
        "income tracking": "Track Every Dollar",
        "tax prep": "Stay Organized Year-Round",
        "time management": "Own Your Schedule",
        "curriculum planning": "Plan With Confidence",
        "tracking progress": "See Your Growth",
        "keeping kids engaged": "Make Learning Fun",
        "forgetting what they read": "Remember Every Book",
        "tracking reading goals": "Reach Your Reading Goals",
        "documenting experiences": "Capture Every Moment",
        "tracking trails": "Log Your Adventures",
        "lack of focus": "Sharpen Your Focus",
        "abandoned resolutions": "Follow Through This Time",
        "no system": "Build Your System",
        "creative block": "Unlock Your Creativity",
        "self-expression": "Express Yourself Freely",
        "symptom tracking": "Understand Your Body",
        "medication management": "Stay On Track",
        "doctor communication": "Communicate Better With Your Doctor",
        "finding purpose": "Find Your Purpose",
        "memory preservation": "Preserve Your Memories",
        "daily structure": "Add Structure to Your Days",
    }
    return mappings.get(pain_point, "Transform Your Life")


def _generate_description(
    niche_keyword: str,
    persona: Persona,
    interior_type: str,
    page_count: int,
    trim_size: str,
    seed: int,
) -> str:
    """Generate a compelling product description with benefits."""
    rng = random.Random(seed + 1000)

    pain_point = rng.choice(persona.pain_points)
    keyword_lower = niche_keyword.lower()
    time_lower = persona.time_framing.lower()

    opening = rng.choice(OPENING_HOOKS).format(
        pain_point=pain_point,
        time_lower=time_lower,
        keyword=keyword_lower,
    )

    # Interior-specific value proposition
    interior_features = {
        "lined": "clean lined pages designed for free-flowing thoughts",
        "dotted": "dot-grid pages for flexible writing, sketching, and organizing",
        "grid": "structured grid pages for precise tracking and data logging",
        "gratitude": "guided gratitude prompts to shift your mindset daily",
        "planner": "structured daily planning pages with schedule, priorities, and notes",
    }

    value_prop = (
        f"This {niche_keyword} features {page_count} pages of "
        f"{interior_features.get(interior_type, 'thoughtfully designed interior')}. "
        f"Built specifically for {persona.label.lower()} who want to "
        f"{_pain_to_benefit(pain_point).lower()}."
    )

    # Bullet points based on interior type and persona
    bullets = _generate_bullet_points(persona, interior_type, rng)
    bullet_text = "\n".join(f"• {b}" for b in bullets)

    # Audience bullets
    audience_bullets = [
        f"• {persona.label} looking for a practical {keyword_lower}",
        f"• Anyone who wants to {_pain_to_benefit(rng.choice(persona.pain_points)).lower()}",
        f"• Gift for someone who loves self-improvement",
    ]
    audience_text = "\n".join(audience_bullets)

    closing = rng.choice(CLOSING_CTAS)

    desc = DESCRIPTION_TEMPLATE.format(
        opening_hook=opening,
        value_proposition=value_prop,
        bullet_points=bullet_text,
        audience_bullets=audience_text,
        page_count=page_count,
        trim_size=trim_size,
        closing_cta=closing,
    )

    # KDP description max is 4000 chars
    return desc[:4000]


def _generate_bullet_points(
    persona: Persona,
    interior_type: str,
    rng: random.Random,
) -> list[str]:
    """Generate benefit-focused bullet points."""
    generic_bullets = [
        "Undated format — start anytime, no wasted pages",
        "Premium matte cover that feels great in your hands",
        "Lays flat for easy writing",
    ]

    interior_bullets = {
        "lined": [
            "Clean, evenly spaced lines for comfortable writing",
            "Generous margins for notes and doodles",
        ],
        "dotted": [
            "Versatile dot grid for writing, sketching, or bullet journaling",
            "Subtle dots that guide without distracting",
        ],
        "grid": [
            "Precise grid layout for tracking, charts, and structured logging",
            "Easy-to-read grid squares for clean data entry",
        ],
        "gratitude": [
            "Daily guided prompts to build a gratitude habit",
            "Thoughtful questions that go beyond 'what are you grateful for'",
            "Space for reflection and intention-setting",
        ],
        "planner": [
            "Daily schedule blocks from morning to evening",
            "Priority checklist to focus on what matters",
            "Notes section for ideas and reminders",
        ],
    }

    bullets = interior_bullets.get(interior_type, [])[:2]
    bullets.extend(rng.sample(generic_bullets, min(2, len(generic_bullets))))
    return bullets


def _generate_keywords(
    niche_keyword: str,
    persona: Persona,
    competitor_keywords: list[str] | None = None,
) -> list[str]:
    """Generate 7 optimized KDP keywords.

    Priority: competitor keywords > persona keywords > generic combinations.
    """
    keywords: list[str] = []
    seen: set[str] = set()

    def _add(kw: str) -> bool:
        kw_clean = kw.strip().lower()
        if kw_clean and kw_clean not in seen and len(kw_clean) <= 50:
            seen.add(kw_clean)
            keywords.append(kw.strip())
            return True
        return False

    # 1. Competitor keywords first (most valuable)
    if competitor_keywords:
        for kw in competitor_keywords:
            _add(kw)
            if len(keywords) >= 3:
                break

    # 2. Persona-specific keywords
    for kw in persona.keywords_extra:
        _add(kw)
        if len(keywords) >= 5:
            break

    # 3. Niche + persona combinations
    _add(niche_keyword)
    _add(f"{niche_keyword} for {persona.label.lower()}")
    _add(f"{persona.time_framing.lower()} {niche_keyword}")

    return keywords[:7]
