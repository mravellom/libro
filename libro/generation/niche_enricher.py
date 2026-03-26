"""Niche enricher — expands generic niches into targeted micro-niches.

Transforms broad keywords like "anxiety journal" into specific,
lower-competition micro-niches like "anxiety journal for college students".
"""

import random
from dataclasses import dataclass


@dataclass
class MicroNiche:
    """A specific sub-niche derived from a broader keyword."""
    keyword: str
    parent_keyword: str
    angle: str               # The differentiating angle
    suggested_interiors: list[str]
    competition_modifier: float  # 0.0-1.0, lower = less competition


# ---------------------------------------------------------------------------
# Angle templates — what makes a micro-niche different
# ---------------------------------------------------------------------------

AUDIENCE_ANGLES = [
    ("for college students", 0.3),
    ("for new moms", 0.3),
    ("for teens", 0.4),
    ("for men", 0.4),
    ("for couples", 0.3),
    ("for seniors", 0.3),
    ("for teachers", 0.3),
    ("for nurses", 0.2),
    ("for entrepreneurs", 0.4),
    ("for kids ages 8-12", 0.3),
    ("for women over 50", 0.2),
    ("for Christian women", 0.3),
]

METHOD_ANGLES = [
    ("with CBT exercises", 0.2, ["lined", "gratitude"]),
    ("with daily prompts", 0.5, ["gratitude", "lined"]),
    ("with habit tracker", 0.3, ["grid", "planner"]),
    ("with mood tracker", 0.3, ["grid", "lined"]),
    ("with coloring pages", 0.2, ["dotted"]),
    ("with weekly reviews", 0.4, ["planner", "lined"]),
    ("with goal setting", 0.4, ["planner", "grid"]),
    ("with affirmations", 0.3, ["gratitude", "lined"]),
    ("with reflection prompts", 0.4, ["lined", "gratitude"]),
    ("with progress charts", 0.3, ["grid", "planner"]),
]

TIME_ANGLES = [
    ("5-minute daily", 0.3),
    ("52-week", 0.4),
    ("90-day", 0.4),
    ("one-year", 0.5),
    ("morning and evening", 0.3),
    ("3-month", 0.3),
    ("100-day challenge", 0.2),
    ("365-day", 0.4),
]


# ---------------------------------------------------------------------------
# Seasonal niche calendar
# ---------------------------------------------------------------------------

SEASONAL_NICHES: dict[int, list[tuple[str, list[str]]]] = {
    1: [  # January
        ("new year goal planner", ["planner", "grid"]),
        ("new year resolution journal", ["lined", "gratitude"]),
        ("fitness challenge tracker", ["grid", "planner"]),
        ("dry january journal", ["lined", "gratitude"]),
        ("vision board planner", ["dotted", "lined"]),
    ],
    2: [  # February
        ("self love journal", ["gratitude", "lined"]),
        ("couples journal", ["lined", "gratitude"]),
        ("valentines day gift journal", ["lined", "dotted"]),
        ("heart health tracker", ["grid", "planner"]),
    ],
    3: [  # March
        ("spring cleaning planner", ["planner", "grid"]),
        ("garden planner", ["grid", "planner"]),
        ("spring habit tracker", ["grid", "planner"]),
        ("womens history journal", ["lined", "dotted"]),
    ],
    4: [  # April
        ("earth day journal", ["lined", "dotted"]),
        ("spring fitness tracker", ["grid", "planner"]),
        ("tax organization planner", ["grid", "planner"]),
        ("easter activity book", ["dotted", "lined"]),
    ],
    5: [  # May
        ("mothers day journal", ["gratitude", "lined"]),
        ("teacher appreciation journal", ["lined", "gratitude"]),
        ("graduation planner", ["planner", "lined"]),
        ("mental health awareness journal", ["lined", "gratitude"]),
    ],
    6: [  # June
        ("fathers day journal", ["lined", "gratitude"]),
        ("summer bucket list planner", ["planner", "lined"]),
        ("vacation planner", ["planner", "grid"]),
        ("summer reading log", ["lined", "grid"]),
    ],
    7: [  # July
        ("teacher planner next year", ["planner", "grid"]),
        ("summer fitness challenge", ["grid", "planner"]),
        ("back to school planner", ["planner", "grid"]),
        ("camping journal", ["lined", "dotted"]),
    ],
    8: [  # August
        ("back to school planner", ["planner", "grid"]),
        ("college planner", ["planner", "grid"]),
        ("student planner", ["planner", "grid"]),
        ("homeschool planner", ["planner", "grid"]),
    ],
    9: [  # September
        ("fall planner", ["planner", "grid"]),
        ("self improvement journal fall", ["lined", "gratitude"]),
        ("meal prep planner", ["planner", "grid"]),
        ("academic planner", ["planner", "grid"]),
    ],
    10: [  # October
        ("halloween activity book", ["dotted", "lined"]),
        ("spooky journal", ["lined", "dotted"]),
        ("breast cancer awareness journal", ["lined", "gratitude"]),
        ("autumn gratitude journal", ["gratitude", "lined"]),
    ],
    11: [  # November
        ("gratitude journal thanksgiving", ["gratitude", "lined"]),
        ("nanowrimo writing journal", ["lined", "dotted"]),
        ("holiday planner", ["planner", "grid"]),
        ("thankfulness journal for kids", ["lined", "gratitude"]),
    ],
    12: [  # December
        ("christmas planner", ["planner", "grid"]),
        ("gift tracker planner", ["grid", "planner"]),
        ("new year planner next year", ["planner", "grid"]),
        ("year in review journal", ["lined", "gratitude"]),
        ("holiday budget tracker", ["grid", "planner"]),
    ],
}


def expand_to_micro_niches(
    keyword: str,
    count: int = 5,
    seed: int | None = None,
) -> list[MicroNiche]:
    """Expand a broad keyword into targeted micro-niches.

    Args:
        keyword: Broad niche keyword (e.g., "anxiety journal").
        count: Number of micro-niches to generate.
        seed: For reproducible results.

    Returns:
        List of MicroNiche with specific targeting angles.
    """
    rng = random.Random(seed)
    results: list[MicroNiche] = []
    seen: set[str] = set()

    # Mix audience, method, and time angles
    all_angles: list[tuple[str, float, list[str] | None]] = []

    for angle, comp in AUDIENCE_ANGLES:
        all_angles.append((angle, comp, None))
    for angle, comp, interiors in METHOD_ANGLES:
        all_angles.append((angle, comp, interiors))
    for angle, comp in TIME_ANGLES:
        all_angles.append((angle, comp, None))

    rng.shuffle(all_angles)

    default_interiors = ["lined", "dotted", "gratitude"]

    for angle_text, comp_mod, interiors in all_angles:
        micro_kw = f"{keyword} {angle_text}"
        if micro_kw not in seen:
            seen.add(micro_kw)
            results.append(MicroNiche(
                keyword=micro_kw,
                parent_keyword=keyword,
                angle=angle_text,
                suggested_interiors=interiors or default_interiors,
                competition_modifier=comp_mod,
            ))
        if len(results) >= count:
            break

    return results


def get_seasonal_niches(month: int | None = None) -> list[tuple[str, list[str]]]:
    """Get seasonal niches for a given month.

    Args:
        month: 1-12. If None, uses current month.

    Returns:
        List of (keyword, suggested_interior_types).
    """
    if month is None:
        from datetime import datetime
        month = datetime.now().month

    return SEASONAL_NICHES.get(month, [])


def get_seasonal_with_lead_time(weeks_ahead: int = 6) -> list[tuple[str, list[str]]]:
    """Get seasonal niches for upcoming period.

    KDP books need ~2 weeks to go live, so we plan ahead.

    Args:
        weeks_ahead: How many weeks to plan ahead.

    Returns:
        Seasonal niches for the target period.
    """
    from datetime import datetime, timedelta

    target_date = datetime.now() + timedelta(weeks=weeks_ahead)
    target_month = target_date.month

    niches = get_seasonal_niches(target_month)

    # Also include next month's early-demand niches
    next_month = (target_month % 12) + 1
    niches.extend(get_seasonal_niches(next_month)[:2])

    return niches
