"""Introduction pages — adds 1-2 pages at the start of each book.

Provides usage instructions, welcome message, and sets expectations
for the reader. This adds perceived value and professionalism.
"""

import textwrap

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import TrimSize


# ---------------------------------------------------------------------------
# Introduction content per interior type
# ---------------------------------------------------------------------------

INTRO_CONTENT: dict[str, dict] = {
    "lined": {
        "title": "Welcome to Your Journal",
        "body": """\
This journal is your personal space — there are no rules here.

Write freely, without judgment. Use it to capture your thoughts, \
process your day, or simply let your pen wander. Whether you write \
one line or fill a page, what matters is that you show up.

How to get the most out of this journal:

  • Set aside a consistent time — morning or evening works best
  • Don't overthink it — just start writing
  • Date your entries so you can look back and see your growth
  • Use it your way — lists, paragraphs, doodles — it's all valid

There is no wrong way to use this journal. The best journal is \
the one you actually use. Let's begin.""",
    },
    "dotted": {
        "title": "Welcome to Your Dot Grid Notebook",
        "body": """\
The dot grid is the most versatile page format — it adapts to you.

Use it for bullet journaling, sketching, mind mapping, handwriting \
practice, or free-form notes. The subtle dots guide your writing \
without constraining it.

Ideas to get started:

  • Bullet Journal — create rapid logs, trackers, and collections
  • Sketch & Draw — the dots provide a subtle grid for proportions
  • Mind Map — start in the center and branch out
  • Free Write — the dots fade away as you fill the page

Whether you're a planner, a doodler, or a thinker — this notebook \
is ready when you are.""",
    },
    "gratitude": {
        "title": "Welcome to Your Gratitude Practice",
        "body": """\
Gratitude is a skill, and like any skill, it grows with practice.

Research shows that people who regularly practice gratitude experience \
improved mood, better sleep, and stronger relationships. This journal \
gives you a simple, structured way to build that habit.

How to use this journal:

  • Choose a time — morning sets intention, evening reflects
  • Answer each prompt honestly — even small things count
  • Be specific — "my morning coffee in the quiet kitchen" is \
better than "coffee"
  • Don't repeat — challenge yourself to find new things each day
  • On hard days, write anyway — those entries matter most

Remember: gratitude isn't about ignoring problems. It's about \
noticing what's already good, even when things are tough.

Start with today. What are you grateful for right now?""",
    },
    "planner": {
        "title": "Welcome to Your Daily Planner",
        "body": """\
A plan doesn't have to be perfect — it just has to exist.

This planner gives you a simple daily structure: schedule your time, \
set your priorities, and capture important notes. That's it. No \
complicated systems, no color-coding required.

How to use this planner:

  • Each morning (or the night before), fill in tomorrow's page
  • Start with your TOP 3 priorities — if you only do three things, \
what matters most?
  • Block your schedule in 1-hour chunks
  • Use the notes section for ideas, calls, and follow-ups
  • At the end of the day, check off what you completed
  • Move unfinished items to tomorrow — no guilt

The goal isn't to fill every hour. It's to spend your time on \
what matters instead of what's loudest. Let's get started.""",
    },
    "grid": {
        "title": "Welcome to Your Grid Notebook",
        "body": """\
The grid format is designed for precision and structure.

Whether you're tracking data, drawing charts, creating tables, or \
working through problems that benefit from organized layout — the \
grid has you covered.

Great uses for grid pages:

  • Data tracking — log numbers, measurements, or habits in neat rows
  • Charts & graphs — create visual representations of your progress
  • Technical notes — diagrams, calculations, and structured thinking
  • Art & design — maintain proportions and symmetry
  • Lists & tables — organize information cleanly

Each square is your building block. Use them however serves you best.""",
    },
    "anxiety": {
        "title": "Welcome to Your Anxiety Journal",
        "body": """\
If you picked up this journal, you're already taking a brave step.

Living with anxiety is exhausting. Racing thoughts, physical tension, \
the constant "what ifs" — it can feel like your mind never stops. \
This journal won't cure anxiety, but it will give you tools to \
understand it, manage it, and reduce its power over you.

Inside you'll find three types of pages:

  • Mood Check-In — track your anxiety level, triggers, and what helps
  • Thought Record — a CBT technique to challenge negative thinking
  • 5-4-3-2-1 Grounding — use your senses to return to the present

How to use this journal:

  • There's no "right" order — use whatever page you need today
  • Be honest with yourself — this is private and judgment-free
  • Notice patterns over time — triggers, helpful strategies
  • On good days, write what made them good
  • On hard days, even writing one line is enough

You are not your anxiety. You are the person learning to manage it.""",
    },
    "fitness": {
        "title": "Welcome to Your Fitness Log",
        "body": """\
What gets measured gets improved.

This logbook is designed to track your workouts simply and effectively. \
No apps to load, no batteries to charge — just you, a pen, and \
your progress on paper.

How to use this log:

  • Fill in one page per workout session
  • Record the exercise, sets, reps, and weight used
  • Track your cardio separately at the bottom
  • Use the notes section for how you felt, energy levels, or tweaks
  • Review your past entries before your next session

Why pen and paper works:

  • Writing it down creates stronger memory and commitment
  • You can flip back and see your progress at a glance
  • No distractions from notifications or social media
  • It's always available — at home, at the gym, anywhere

Consistency beats perfection. Show up, log it, and watch yourself grow.""",
    },
    "budget": {
        "title": "Welcome to Your Budget Tracker",
        "body": """\
You can't improve what you don't track.

This budget tracker gives you a clear, honest picture of where \
your money goes. No judgment, no complicated formulas — just \
simple tracking that builds awareness and control.

How to use this tracker:

  • At the start of each month, set your budget per category
  • Log daily spending on the spending log pages
  • At month's end, compare actual vs. budget
  • Use the "remaining" line to see your real financial picture
  • Celebrate small wins — under budget in ANY category is progress

The categories included cover most common expenses. If something \
doesn't fit, use "Other" and customize as needed.

Tips for success:

  • Track everything, even small purchases — they add up
  • Review weekly, not just monthly — catch overspending early
  • Be realistic with budgets — too tight leads to giving up
  • Round up expenses — the pennies will work out

Financial peace starts with knowing your numbers. Let's begin.""",
    },
    "reading": {
        "title": "Welcome to Your Reading Log",
        "body": """\
Every book changes you a little. This log helps you remember how.

A reading log is more than a list of books — it's a record of your \
intellectual journey. By writing down your thoughts, you'll retain \
more, think deeper, and build a personal library of insights.

How to use this reading log:

  • Fill in the book info page when you start a new book
  • Complete the review page when you finish
  • Be honest in your ratings — not every book is a 5-star
  • Capture quotes that resonate — you'll love re-reading them later
  • Use the "key takeaways" section to distill what matters most

You don't need to write long reviews — even a few sentences capture \
the essence of what the book meant to you at that moment in your life.

Happy reading.""",
    },
    "meal": {
        "title": "Welcome to Your Meal Planner",
        "body": """\
Planning meals isn't about restriction — it's about intention.

When you plan what you eat, you waste less food, spend less money, \
eat healthier, and eliminate the daily stress of "what's for dinner?"

How to use this planner:

  • Spend 15 minutes on the weekend planning your week
  • Fill in meals for each day — keep it realistic
  • Use the grocery list to shop once for the whole week
  • Prep what you can on Sunday — future you will be grateful
  • Don't aim for perfection — planned meals 5 out of 7 days is a win

Tips for success:

  • Repeat meals you love — variety is overrated when it causes stress
  • Cook once, eat twice — make extra for leftovers
  • Keep a running list of your go-to meals on the inside cover
  • Leave 1-2 nights flexible for leftovers or spontaneous plans

Your health, budget, and sanity will thank you. Let's plan.""",
    },
}

# Fallback for unknown types
_DEFAULT_INTRO = {
    "title": "Welcome",
    "body": """\
Thank you for choosing this journal.

This is your space to write, think, and grow. There are no rules — \
use it in whatever way serves you best. The most important thing \
is to start.

Every page is a fresh opportunity. Let's begin.""",
}


def draw_intro_pages(
    c: Canvas,
    trim: TrimSize,
    interior_type: str,
    title: str | None = None,
) -> int:
    """Draw 1-2 introduction pages at the start of the book.

    Args:
        c: ReportLab canvas.
        trim: TrimSize object.
        interior_type: Template name (used to select intro content).
        title: Optional book title to include on the welcome page.

    Returns:
        Number of pages drawn (always 2: title page + intro).
    """
    content = INTRO_CONTENT.get(interior_type, _DEFAULT_INTRO)

    # --- Page 1: Title page (mostly blank, elegant) ---
    _draw_title_page(c, trim, title)
    c.showPage()

    # --- Page 2: How to use this book ---
    _draw_intro_text_page(c, trim, content)
    c.showPage()

    return 2


def _draw_title_page(c: Canvas, trim: TrimSize, title: str | None) -> None:
    """Draw a minimal title page."""
    mid_y = trim.height * 0.55
    mid_x = trim.width / 2

    # Decorative line
    line_color = Color(0.75, 0.75, 0.75)
    c.setStrokeColor(line_color)
    c.setLineWidth(0.5)
    c.line(mid_x - 40, mid_y + 30, mid_x + 40, mid_y + 30)

    if title:
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(Color(0.25, 0.25, 0.25))
        # Wrap title if too long
        max_width = trim.content_width * 0.8
        if c.stringWidth(title, "Helvetica-Bold", 14) > max_width:
            words = title.split()
            lines = []
            current = ""
            for word in words:
                test = f"{current} {word}".strip()
                if c.stringWidth(test, "Helvetica-Bold", 14) < max_width:
                    current = test
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)
            y = mid_y + (len(lines) - 1) * 10
            for line in lines:
                c.drawCentredString(mid_x, y, line)
                y -= 22
        else:
            c.drawCentredString(mid_x, mid_y, title)

    # Decorative line below
    c.line(mid_x - 40, mid_y - 30, mid_x + 40, mid_y - 30)

    # "This book belongs to" at bottom
    c.setFont("Helvetica", 9)
    c.setFillColor(Color(0.5, 0.5, 0.5))
    c.drawCentredString(mid_x, trim.margin + 60, "This book belongs to:")
    c.setStrokeColor(line_color)
    c.line(mid_x - 80, trim.margin + 45, mid_x + 80, trim.margin + 45)


def _draw_intro_text_page(c: Canvas, trim: TrimSize, content: dict) -> None:
    """Draw the intro/instructions page."""
    y = trim.content_top - 10

    # Title
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(Color(0.25, 0.25, 0.25))
    c.drawString(trim.content_left, y, content["title"])
    y -= 8

    # Decorative line under title
    c.setStrokeColor(Color(0.75, 0.75, 0.75))
    c.setLineWidth(0.5)
    c.line(trim.content_left, y, trim.content_left + 60, y)
    y -= 20

    # Body text
    c.setFont("Helvetica", 9)
    c.setFillColor(Color(0.30, 0.30, 0.30))
    line_height = 13

    body = content["body"]
    for paragraph in body.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            y -= line_height * 0.5
            continue

        # Word wrap
        words = paragraph.split()
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if c.stringWidth(test, "Helvetica", 9) < trim.content_width - 10:
                current_line = test
            else:
                # Check for bullet point
                indent = 15 if current_line.startswith("•") else 0
                c.drawString(trim.content_left + indent, y, current_line)
                y -= line_height
                current_line = word

                if y < trim.content_bottom + 20:
                    return

        if current_line:
            indent = 15 if current_line.startswith("•") else 0
            c.drawString(trim.content_left + indent, y, current_line)
            y -= line_height

        if y < trim.content_bottom + 20:
            return
