"""Seed-based interior style generation for unique book interiors.

Each variant uses its ID as a seed to generate reproducible but unique
visual parameters: spacing, colors, decorations, prompts, etc.
This ensures no two books have identical interior PDFs.
"""

import random
from dataclasses import dataclass, field


# --- Color palettes for subtle variation ---
LINE_COLORS = [
    (0.78, 0.78, 0.78),  # classic gray
    (0.80, 0.82, 0.85),  # cool blue-gray
    (0.75, 0.80, 0.75),  # sage gray
    (0.82, 0.78, 0.75),  # warm gray
    (0.72, 0.76, 0.82),  # steel blue
    (0.80, 0.75, 0.78),  # mauve gray
    (0.78, 0.82, 0.80),  # mint gray
    (0.85, 0.82, 0.78),  # sand
    (0.76, 0.76, 0.80),  # lavender gray
    (0.80, 0.80, 0.76),  # olive gray
]

PROMPT_COLORS = [
    (0.40, 0.40, 0.40),  # dark gray
    (0.35, 0.38, 0.42),  # blue-gray
    (0.38, 0.42, 0.38),  # green-gray
    (0.42, 0.38, 0.35),  # warm dark
    (0.36, 0.36, 0.40),  # purple-gray
]

PAGE_NUMBER_FONTS = ["Helvetica", "Times-Roman", "Courier"]

HEADER_STYLES = ["line", "box", "dotted_line", "none"]
HEADER_DECORATIONS = ["none", "thin_rule", "dots", "corner_marks"]
FOOTER_DECORATIONS = ["none", "thin_rule", "dots"]
PAGE_NUMBER_POSITIONS = ["centered", "outer_corner", "inner_corner"]

# --- Gratitude prompt sets ---
GRATITUDE_PROMPT_SETS = [
    [
        "Today I am grateful for:",
        "What made today special:",
        "One positive thing that happened:",
        "How I can make tomorrow better:",
    ],
    [
        "Three things I appreciate today:",
        "A moment that brought me joy:",
        "Someone who made a difference today:",
        "What I learned about myself today:",
    ],
    [
        "What filled my heart today:",
        "A small blessing I noticed:",
        "How I grew as a person today:",
        "My intention for tomorrow:",
    ],
    [
        "Today's highlight:",
        "I am thankful for this person:",
        "Something beautiful I witnessed:",
        "A goal I moved closer to today:",
    ],
    [
        "What brought me peace today:",
        "An unexpected gift today was:",
        "How I showed kindness today:",
        "What I want to carry into tomorrow:",
    ],
    [
        "Three wins from today:",
        "A challenge I handled well:",
        "What made me smile today:",
        "How I took care of myself today:",
    ],
    [
        "Today I noticed:",
        "A relationship I'm grateful for:",
        "Something I accomplished today:",
        "What inspires me right now:",
    ],
    [
        "My favorite moment today:",
        "Something I take for granted but shouldn't:",
        "A lesson from today:",
        "Tomorrow I look forward to:",
    ],
]

# --- Quote bank for interstitial pages ---
QUOTE_BANK = [
    "The only way to do great work is to love what you do.",
    "In the middle of difficulty lies opportunity.",
    "What you get by achieving your goals is not as important as what you become.",
    "The journey of a thousand miles begins with a single step.",
    "Be the change you wish to see in the world.",
    "Every moment is a fresh beginning.",
    "Believe you can and you're halfway there.",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "You are never too old to set another goal or to dream a new dream.",
    "Start where you are. Use what you have. Do what you can.",
    "What lies behind us and what lies before us are tiny matters compared to what lies within us.",
    "The secret of getting ahead is getting started.",
    "Your limitation — it's only your imagination.",
    "Push yourself, because no one else is going to do it for you.",
    "Great things never come from comfort zones.",
    "Dream it. Wish it. Do it.",
    "Don't stop when you're tired. Stop when you're done.",
    "Wake up with determination. Go to bed with satisfaction.",
    "Do something today that your future self will thank you for.",
    "It's going to be hard, but hard does not mean impossible.",
    "Don't wait for opportunity. Create it.",
    "Sometimes later becomes never. Do it now.",
    "Dream bigger. Do bigger.",
    "The harder you work for something, the greater you'll feel when you achieve it.",
    "Success doesn't just find you. You have to go out and get it.",
    "Don't be afraid to give up the good to go for the great.",
    "Happiness is not by chance, but by choice.",
    "A smooth sea never made a skilled sailor.",
    "The mind is everything. What you think you become.",
    "Strive not to be a success, but rather to be of value.",
    "Fall seven times, stand up eight.",
    "Everything you've ever wanted is on the other side of fear.",
    "Life is 10% what happens to us and 90% how we react to it.",
    "The only impossible journey is the one you never begin.",
    "Act as if what you do makes a difference. It does.",
    "What you do today can improve all your tomorrows.",
    "Quality is not an act, it is a habit.",
    "It always seems impossible until it's done.",
    "You don't have to be great to start, but you have to start to be great.",
    "The future belongs to those who believe in the beauty of their dreams.",
    "Difficult roads often lead to beautiful destinations.",
    "Your only limit is your mind.",
    "Go the extra mile. It's never crowded.",
    "Stay patient and trust your journey.",
    "Every day is a new chance to change your life.",
]


@dataclass
class InteriorStyle:
    """Unique visual parameters for a book interior, generated from a seed."""

    # Line-based templates (lined, grid)
    line_spacing: float = 24.0
    line_color: tuple = (0.8, 0.8, 0.8)
    line_width: float = 0.5

    # Dotted template
    dot_spacing: float = 18.0
    dot_radius: float = 0.6
    dot_color: tuple = (0.75, 0.75, 0.75)

    # Grid template
    cell_size: float = 18.0

    # Header/footer
    header_style: str = "line"
    header_decoration: str = "none"
    footer_decoration: str = "none"
    page_number_position: str = "centered"
    page_number_font: str = "Helvetica"

    # Margin variation
    margin_inches: float = 0.5

    # Prompt colors (for structured templates)
    prompt_color: tuple = (0.4, 0.4, 0.4)

    # Interstitial pages
    has_quote_pages: bool = False
    quote_page_interval: int = 30
    quotes: list[str] = field(default_factory=list)

    has_section_dividers: bool = False
    section_divider_interval: int = 20

    # Gratitude-specific
    prompt_set_index: int = 0
    lines_per_prompt: int = 4
    prompt_line_spacing: float = 22.0

    # Planner-specific
    planner_hour_start: int = 6
    planner_hour_end: int = 21
    planner_priority_count: int = 5
    planner_sections_order: list[str] = field(
        default_factory=lambda: ["schedule", "priorities", "notes"]
    )


def generate_interior_style(seed: int, interior_type: str) -> InteriorStyle:
    """Generate a unique but reproducible InteriorStyle from a seed.

    Args:
        seed: Typically the variant's ID.
        interior_type: Template name (lined, dotted, grid, gratitude, planner).

    Returns:
        InteriorStyle with unique parameters.
    """
    rng = random.Random(seed)

    line_color = rng.choice(LINE_COLORS)
    prompt_color = rng.choice(PROMPT_COLORS)

    # Pick quotes for interstitial pages
    num_quotes = rng.randint(3, 8)
    quotes = rng.sample(QUOTE_BANK, min(num_quotes, len(QUOTE_BANK)))

    # Planner section order variations
    planner_orders = [
        ["schedule", "priorities", "notes"],
        ["priorities", "schedule", "notes"],
        ["schedule", "notes", "priorities"],
        ["priorities", "notes", "schedule"],
    ]

    style = InteriorStyle(
        # Lines
        line_spacing=rng.uniform(20.0, 28.0),
        line_color=line_color,
        line_width=rng.uniform(0.3, 0.7),

        # Dots
        dot_spacing=rng.uniform(15.0, 22.0),
        dot_radius=rng.uniform(0.4, 0.8),
        dot_color=line_color,  # reuse same palette

        # Grid
        cell_size=rng.uniform(15.0, 22.0),

        # Header/footer
        header_style=rng.choice(HEADER_STYLES),
        header_decoration=rng.choice(HEADER_DECORATIONS),
        footer_decoration=rng.choice(FOOTER_DECORATIONS),
        page_number_position=rng.choice(PAGE_NUMBER_POSITIONS),
        page_number_font=rng.choice(PAGE_NUMBER_FONTS),

        # Margin (slight variation)
        margin_inches=rng.uniform(0.45, 0.55),

        # Prompts
        prompt_color=prompt_color,

        # Interstitial pages
        has_quote_pages=rng.random() > 0.3,  # 70% chance
        quote_page_interval=rng.randint(20, 40),
        quotes=quotes,

        has_section_dividers=rng.random() > 0.4,  # 60% chance
        section_divider_interval=rng.randint(15, 30),

        # Gratitude
        prompt_set_index=rng.randint(0, len(GRATITUDE_PROMPT_SETS) - 1),
        lines_per_prompt=rng.randint(3, 5),
        prompt_line_spacing=rng.uniform(20.0, 26.0),

        # Planner
        planner_hour_start=rng.choice([5, 6, 7, 8]),
        planner_hour_end=rng.choice([19, 20, 21, 22]),
        planner_priority_count=rng.randint(3, 7),
        planner_sections_order=rng.choice(planner_orders),
    )

    return style


def interior_content_hash(seed: int, interior_type: str) -> str:
    """Generate a hash of the actual interior parameters for dedup verification."""
    import hashlib

    style = generate_interior_style(seed, interior_type)
    # Hash the key visual parameters
    raw = (
        f"{interior_type}|{seed}|"
        f"{style.line_spacing:.2f}|{style.line_color}|"
        f"{style.dot_spacing:.2f}|{style.cell_size:.2f}|"
        f"{style.header_style}|{style.prompt_set_index}|"
        f"{style.margin_inches:.3f}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
