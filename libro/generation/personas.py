"""Buyer personas — audience segmentation for targeted book generation.

Each persona defines a specific buyer profile with preferences that inform
title framing, interior type, color palette, and keyword strategy.
"""

from dataclasses import dataclass


@dataclass
class Persona:
    """A specific buyer profile that shapes product generation."""
    name: str
    label: str                  # Short label for titles (e.g., "Busy Moms")
    pain_points: list[str]      # What problem they're solving
    preferred_interiors: list[str]
    preferred_palette: str      # Key from brand_manager.COLOR_PALETTES
    time_framing: str           # How they think about time commitment
    price_tolerance: str        # low ($6.99), mid ($9.99), high ($12.99)
    title_hooks: list[str]      # Emotional hooks for titles
    keywords_extra: list[str]   # Additional keywords specific to this persona
    categories: list[str]       # Niche categories this persona fits


# ---------------------------------------------------------------------------
# Persona database — organized by life situation, not demographics
# ---------------------------------------------------------------------------

PERSONAS: list[Persona] = [
    # --- Wellness & Mental Health ---
    Persona(
        name="overwhelmed_professional",
        label="Busy Professionals",
        pain_points=["burnout", "work-life balance", "mental clarity"],
        preferred_interiors=["planner", "gratitude", "lined"],
        preferred_palette="slate",
        time_framing="5-Minute",
        price_tolerance="mid",
        title_hooks=[
            "Reclaim Your Peace",
            "From Burnout to Balance",
            "Clear Your Mind",
            "Your Daily Reset",
        ],
        keywords_extra=["stress relief", "work life balance", "professional wellness"],
        categories=["journal", "fitness", "productivity"],
    ),
    Persona(
        name="new_mom",
        label="New Moms",
        pain_points=["postpartum anxiety", "sleep deprivation", "self-identity"],
        preferred_interiors=["gratitude", "lined", "planner"],
        preferred_palette="blush",
        time_framing="5-Minute",
        price_tolerance="mid",
        title_hooks=[
            "Motherhood Without the Guilt",
            "5 Minutes Just for You",
            "Finding Yourself Again",
            "Small Moments, Big Joy",
        ],
        keywords_extra=["new mom gift", "postpartum journal", "mom self care"],
        categories=["journal", "fitness"],
    ),
    Persona(
        name="anxiety_warrior",
        label="Anyone With Anxiety",
        pain_points=["racing thoughts", "overwhelm", "panic episodes"],
        preferred_interiors=["anxiety", "gratitude", "lined"],
        preferred_palette="sage",
        time_framing="Daily",
        price_tolerance="mid",
        title_hooks=[
            "Quiet the Noise",
            "One Thought at a Time",
            "Ground Yourself Today",
            "From Anxious to Anchored",
        ],
        keywords_extra=["anxiety relief", "CBT journal", "mental health workbook"],
        categories=["journal"],
    ),
    # --- Fitness & Health ---
    Persona(
        name="fitness_beginner",
        label="Fitness Beginners",
        pain_points=["don't know where to start", "lack of consistency", "intimidation"],
        preferred_interiors=["fitness", "grid", "planner"],
        preferred_palette="ocean",
        time_framing="90-Day",
        price_tolerance="mid",
        title_hooks=[
            "Your First 90 Days",
            "Start Simple, Stay Strong",
            "The No-Gym Fitness Log",
            "Every Rep Counts",
        ],
        keywords_extra=["beginner workout log", "fitness tracker notebook", "exercise journal"],
        categories=["fitness"],
    ),
    Persona(
        name="weight_loss_journey",
        label="Weight Loss Warriors",
        pain_points=["accountability", "emotional eating", "plateaus"],
        preferred_interiors=["grid", "planner", "gratitude"],
        preferred_palette="forest",
        time_framing="12-Week",
        price_tolerance="mid",
        title_hooks=[
            "Track It to Transform It",
            "The Honest Food Diary",
            "Your Body, Your Data",
            "Small Changes, Big Results",
        ],
        keywords_extra=["food diary", "calorie counter notebook", "weight loss tracker"],
        categories=["fitness"],
    ),
    # --- Finance ---
    Persona(
        name="debt_free_dreamer",
        label="Debt-Free Dreamers",
        pain_points=["debt stress", "no savings", "financial illiteracy"],
        preferred_interiors=["budget", "grid", "planner"],
        preferred_palette="midnight",
        time_framing="52-Week",
        price_tolerance="low",
        title_hooks=[
            "Every Dollar Has a Job",
            "From Broke to Budget Boss",
            "The Paycheck Planner",
            "Your Debt-Free Roadmap",
        ],
        keywords_extra=["budget planner", "debt payoff tracker", "money management"],
        categories=["finance"],
    ),
    Persona(
        name="side_hustler",
        label="Side Hustlers",
        pain_points=["income tracking", "tax prep", "time management"],
        preferred_interiors=["planner", "grid", "lined"],
        preferred_palette="sunset",
        time_framing="Monthly",
        price_tolerance="mid",
        title_hooks=[
            "Build Your Empire on the Side",
            "The Hustler's Logbook",
            "Track Every Stream",
            "Side Income, Serious Results",
        ],
        keywords_extra=["small business planner", "income tracker", "freelance journal"],
        categories=["finance"],
    ),
    # --- Education & Kids ---
    Persona(
        name="homeschool_parent",
        label="Homeschool Families",
        pain_points=["curriculum planning", "tracking progress", "keeping kids engaged"],
        preferred_interiors=["lined", "dotted", "grid"],
        preferred_palette="sage",
        time_framing="Weekly",
        price_tolerance="low",
        title_hooks=[
            "Learn at Your Own Pace",
            "The Home Classroom Companion",
            "Write, Draw, Discover",
            "Practice Makes Progress",
        ],
        keywords_extra=["homeschool workbook", "kids writing practice", "educational notebook"],
        categories=["education"],
    ),
    # --- Hobbies ---
    Persona(
        name="avid_reader",
        label="Book Lovers",
        pain_points=["forgetting what they read", "tracking reading goals", "book recommendations"],
        preferred_interiors=["reading", "lined", "grid"],
        preferred_palette="midnight",
        time_framing="365-Day",
        price_tolerance="mid",
        title_hooks=[
            "Every Book Tells Your Story",
            "Read. Reflect. Repeat.",
            "The Bibliophile's Logbook",
            "Your Reading Life, Organized",
        ],
        keywords_extra=["reading log", "book tracker", "reading journal"],
        categories=["hobby"],
    ),
    Persona(
        name="outdoor_adventurer",
        label="Outdoor Enthusiasts",
        pain_points=["documenting experiences", "tracking trails", "planning trips"],
        preferred_interiors=["lined", "dotted", "grid"],
        preferred_palette="forest",
        time_framing="365-Day",
        price_tolerance="mid",
        title_hooks=[
            "Trail Notes & Memories",
            "Wander. Write. Remember.",
            "The Explorer's Field Journal",
            "Peak by Peak",
        ],
        keywords_extra=["hiking journal", "nature log", "camping journal", "travel notebook"],
        categories=["hobby"],
    ),
    # --- Productivity ---
    Persona(
        name="goal_setter",
        label="Goal Setters",
        pain_points=["lack of focus", "abandoned resolutions", "no system"],
        preferred_interiors=["planner", "grid", "lined"],
        preferred_palette="minimal",
        time_framing="90-Day",
        price_tolerance="mid",
        title_hooks=[
            "Goals Without the Fluff",
            "Plan. Execute. Repeat.",
            "The 90-Day Sprint",
            "Make It Happen",
        ],
        keywords_extra=["goal planner", "productivity journal", "action planner"],
        categories=["productivity"],
    ),
    Persona(
        name="creative_journaler",
        label="Creative Souls",
        pain_points=["creative block", "self-expression", "mindfulness"],
        preferred_interiors=["dotted", "lined"],
        preferred_palette="blush",
        time_framing="Daily",
        price_tolerance="mid",
        title_hooks=[
            "Let the Pages Speak",
            "Ink Your Imagination",
            "Blank Pages, Bold Ideas",
            "Create Without Limits",
        ],
        keywords_extra=["creative journal", "dot grid notebook", "art journal"],
        categories=["journal", "hobby"],
    ),
    # --- Professional / Medical ---
    Persona(
        name="chronic_illness",
        label="Health Trackers",
        pain_points=["symptom tracking", "medication management", "doctor communication"],
        preferred_interiors=["grid", "planner"],
        preferred_palette="ocean",
        time_framing="Daily",
        price_tolerance="mid",
        title_hooks=[
            "Know Your Body's Patterns",
            "Your Health, Your Data",
            "The Patient's Companion",
            "Track Today, Heal Tomorrow",
        ],
        keywords_extra=["symptom tracker", "medication log", "health journal"],
        categories=["professional"],
    ),
    Persona(
        name="retiree",
        label="Retirees",
        pain_points=["finding purpose", "memory preservation", "daily structure"],
        preferred_interiors=["lined", "gratitude", "planner"],
        preferred_palette="forest",
        time_framing="Daily",
        price_tolerance="mid",
        title_hooks=[
            "The Best Chapter Starts Now",
            "Stories Worth Keeping",
            "A Life Well Lived, Well Written",
            "Your Golden Pages",
        ],
        keywords_extra=["retirement journal", "memory book", "legacy journal"],
        categories=["journal"],
    ),
]


# ---------------------------------------------------------------------------
# Category → Persona mapping for niche matching
# ---------------------------------------------------------------------------

# Maps niche category keywords to relevant personas
_CATEGORY_MAP: dict[str, list[str]] = {}
for _p in PERSONAS:
    for _cat in _p.categories:
        _CATEGORY_MAP.setdefault(_cat, []).append(_p.name)


def get_personas_for_niche(niche_keyword: str) -> list[Persona]:
    """Return personas relevant to a niche keyword.

    Matches via category keywords and direct keyword overlap.
    Returns at least 2 personas, falling back to general-purpose ones.
    """
    keyword_lower = niche_keyword.lower()
    matched: list[Persona] = []
    seen: set[str] = set()

    # Direct keyword match in persona keywords_extra and pain_points
    for p in PERSONAS:
        all_terms = p.keywords_extra + p.pain_points + [p.label.lower()]
        for term in all_terms:
            if term in keyword_lower or keyword_lower in term:
                if p.name not in seen:
                    matched.append(p)
                    seen.add(p.name)
                break

    # Category match via evergreen niche categories
    _NICHE_CATEGORY_HINTS = {
        "journal": "journal", "diary": "journal", "gratitude": "journal",
        "prayer": "journal", "mindfulness": "journal", "anxiety": "journal",
        "dream": "journal", "manifestation": "journal", "shadow": "journal",
        "fitness": "fitness", "workout": "fitness", "exercise": "fitness",
        "yoga": "fitness", "running": "fitness", "bodybuilding": "fitness",
        "weight": "fitness", "calorie": "fitness", "food": "fitness",
        "meal": "fitness", "water": "fitness",
        "budget": "finance", "expense": "finance", "savings": "finance",
        "debt": "finance", "bill": "finance", "income": "finance",
        "business": "finance", "hustle": "finance",
        "recipe": "hobby", "reading": "hobby", "garden": "hobby",
        "travel": "hobby", "bird": "hobby", "fish": "hobby",
        "wine": "hobby", "craft": "hobby", "music": "hobby", "hiking": "hobby",
        "handwriting": "education", "spelling": "education", "math": "education",
        "story": "education", "sight": "education",
        "habit": "productivity", "goal": "productivity", "planner": "productivity",
        "todo": "productivity", "time management": "productivity",
        "meeting": "professional", "password": "professional",
        "blood": "professional", "medication": "professional",
        "vehicle": "professional", "pet": "professional",
    }

    for hint_kw, category in _NICHE_CATEGORY_HINTS.items():
        if hint_kw in keyword_lower:
            for pname in _CATEGORY_MAP.get(category, []):
                if pname not in seen:
                    persona = next(p for p in PERSONAS if p.name == pname)
                    matched.append(persona)
                    seen.add(pname)
            break

    # Fallback: general-purpose personas
    if len(matched) < 2:
        fallbacks = ["overwhelmed_professional", "goal_setter", "creative_journaler"]
        for fb_name in fallbacks:
            if fb_name not in seen:
                persona = next(p for p in PERSONAS if p.name == fb_name)
                matched.append(persona)
                seen.add(fb_name)
            if len(matched) >= 2:
                break

    return matched


def get_persona_by_name(name: str) -> Persona | None:
    """Look up a persona by its internal name."""
    for p in PERSONAS:
        if p.name == name:
            return p
    return None
