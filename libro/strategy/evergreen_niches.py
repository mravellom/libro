"""Curated list of evergreen low-content book niches for KDP."""

# High-demand, year-round niches organized by category.
# Each entry: (keyword, suggested_interior_types)

EVERGREEN_NICHES: list[tuple[str, list[str]]] = [
    # Journals & Self-improvement
    ("gratitude journal", ["gratitude", "lined", "dotted"]),
    ("prayer journal", ["lined", "dotted"]),
    ("mindfulness journal", ["lined", "dotted", "gratitude"]),
    ("self care journal", ["gratitude", "lined", "planner"]),
    ("daily journal", ["lined", "dotted"]),
    ("dream journal", ["lined", "dotted"]),
    ("bible study journal", ["lined", "dotted"]),
    ("manifestation journal", ["lined", "gratitude"]),
    ("shadow work journal", ["lined", "dotted"]),
    ("anxiety journal", ["lined", "gratitude"]),

    # Fitness & Health
    ("fitness logbook", ["grid", "planner"]),
    ("workout log", ["grid", "planner"]),
    ("food diary", ["lined", "planner"]),
    ("meal planner", ["planner", "grid"]),
    ("weight loss tracker", ["grid", "planner"]),
    ("yoga journal", ["lined", "dotted"]),
    ("running log", ["grid", "planner"]),
    ("bodybuilding logbook", ["grid", "planner"]),
    ("calorie tracker", ["grid", "planner"]),
    ("water intake tracker", ["grid", "planner"]),

    # Finance & Business
    ("budget planner", ["planner", "grid"]),
    ("expense tracker", ["grid", "planner"]),
    ("savings tracker", ["grid", "planner"]),
    ("bill organizer", ["planner", "grid"]),
    ("debt payoff planner", ["planner", "grid"]),
    ("small business planner", ["planner", "lined"]),
    ("side hustle journal", ["lined", "planner"]),
    ("income tracker", ["grid", "planner"]),

    # Hobbies & Lifestyle
    ("recipe book blank", ["lined", "grid"]),
    ("reading log", ["lined", "grid"]),
    ("gardening journal", ["lined", "grid"]),
    ("travel journal", ["lined", "dotted"]),
    ("bird watching log", ["lined", "grid"]),
    ("fishing log", ["lined", "grid"]),
    ("wine tasting journal", ["lined", "grid"]),
    ("craft project planner", ["planner", "grid"]),
    ("music practice log", ["lined", "grid"]),
    ("hiking journal", ["lined", "dotted"]),

    # Education & Kids
    ("handwriting practice", ["lined", "dotted"]),
    ("spelling practice notebook", ["lined", "grid"]),
    ("math practice notebook", ["grid", "dotted"]),
    ("story writing notebook", ["lined", "dotted"]),
    ("sight words practice", ["lined", "dotted"]),

    # Productivity
    ("habit tracker", ["grid", "planner"]),
    ("goal planner", ["planner", "lined"]),
    ("daily planner undated", ["planner", "lined"]),
    ("weekly planner", ["planner", "grid"]),
    ("project planner", ["planner", "grid"]),
    ("to do list notebook", ["lined", "planner"]),
    ("time management planner", ["planner", "grid"]),

    # Professional
    ("meeting notes notebook", ["lined", "dotted"]),
    ("password log book", ["lined", "grid"]),
    ("address book", ["lined", "grid"]),
    ("blood pressure log", ["grid", "planner"]),
    ("blood sugar log", ["grid", "planner"]),
    ("medication tracker", ["grid", "planner"]),
    ("vehicle maintenance log", ["lined", "grid"]),
    ("pet health record", ["lined", "grid"]),
]


def get_evergreen_sample(count: int) -> list[tuple[str, list[str]]]:
    """Return a random sample of evergreen niches."""
    import random
    return random.sample(EVERGREEN_NICHES, min(count, len(EVERGREEN_NICHES)))


def get_evergreen_by_category(category: str) -> list[tuple[str, list[str]]]:
    """Get niches by approximate category match."""
    category_lower = category.lower()
    # Simple keyword matching for category filtering
    category_keywords = {
        "journal": ["journal", "diary"],
        "fitness": ["fitness", "workout", "log", "yoga", "running", "bodybuilding", "calorie", "water"],
        "finance": ["budget", "expense", "savings", "bill", "debt", "income", "business"],
        "hobby": ["recipe", "reading", "garden", "travel", "bird", "fish", "wine", "craft", "music", "hiking"],
        "education": ["handwriting", "spelling", "math", "story", "sight"],
        "productivity": ["habit", "goal", "planner", "weekly", "project", "todo", "time"],
        "professional": ["meeting", "password", "address", "blood", "medication", "vehicle", "pet"],
    }

    keywords = category_keywords.get(category_lower, [category_lower])
    return [
        (kw, types) for kw, types in EVERGREEN_NICHES
        if any(k in kw.lower() for k in keywords)
    ]
