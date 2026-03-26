"""Thematic interior templates — niche-specific layouts with real content.

Instead of generic lines/dots, these templates provide structured pages
with fields, prompts, and layouts specific to the niche's purpose.
"""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color

from libro.generation.templates.base import InteriorTemplate, TrimSize


# ---------------------------------------------------------------------------
# Anxiety / CBT Journal
# ---------------------------------------------------------------------------

class AnxietyJournalTemplate(InteriorTemplate):
    """CBT-informed anxiety journal with grounding exercises."""

    name = "anxiety"
    description = "Anxiety journal with CBT exercises, mood tracking, and grounding techniques"

    _GROUNDING_EXERCISE = [
        "5 things I can SEE:",
        "4 things I can TOUCH:",
        "3 things I can HEAR:",
        "2 things I can SMELL:",
        "1 thing I can TASTE:",
    ]

    _THOUGHT_RECORD = [
        ("Situation", "What happened? Where were you?"),
        ("Automatic Thought", "What went through your mind?"),
        ("Emotion", "What did you feel? (0-10)"),
        ("Evidence For", "What supports this thought?"),
        ("Evidence Against", "What contradicts this thought?"),
        ("Balanced Thought", "A more realistic perspective:"),
    ]

    _MOOD_OPTIONS = [
        "Calm", "Anxious", "Sad", "Happy", "Irritable",
        "Hopeful", "Overwhelmed", "Grateful", "Numb", "Energetic",
    ]

    def __init__(self):
        super().__init__()

    @property
    def line_color(self) -> Color:
        return Color(*(self.style.line_color if self.style else (0.80, 0.82, 0.80)))

    @property
    def label_color(self) -> Color:
        return Color(*(self.style.prompt_color if self.style else (0.35, 0.40, 0.35)))

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        # Alternate between 3 page types
        page_type = page_num % 3
        if page_type == 1:
            self._draw_mood_check_in(c, page_num, trim)
        elif page_type == 2:
            self._draw_thought_record(c, page_num, trim)
        else:
            self._draw_grounding_page(c, page_num, trim)

    def _draw_mood_check_in(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        # Header
        c.setFont("Helvetica", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "Date: _______________")
        c.drawRightString(trim.content_right, y, "Time: ________")
        y -= 25

        c.setFont("Helvetica-Bold", 11)
        c.drawString(trim.content_left, y, "MOOD CHECK-IN")
        y -= 20

        # Mood circles
        c.setFont("Helvetica", 8)
        c.setStrokeColor(self.line_color)
        x_start = trim.content_left
        col_width = trim.content_width / 5
        for i, mood in enumerate(self._MOOD_OPTIONS):
            col = i % 5
            row = i // 5
            x = x_start + col * col_width
            my = y - row * 22
            c.circle(x + 6, my + 2, 5, fill=0)
            c.setFillColor(self.label_color)
            c.drawString(x + 15, my, mood)
        y -= 55

        # Anxiety level
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "Anxiety Level (1-10):")
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)
        x = trim.content_left + 120
        for i in range(1, 11):
            c.circle(x, y + 2, 7, fill=0)
            c.setFont("Helvetica", 7)
            c.setFillColor(self.label_color)
            c.drawCentredString(x, y - 1, str(i))
            x += 20
        y -= 30

        # What triggered my anxiety
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "What triggered my anxiety today:")
        y -= 15
        c.setStrokeColor(self.line_color)
        for _ in range(4):
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 20

        # Physical symptoms
        y -= 5
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "Physical symptoms I noticed:")
        y -= 15
        for _ in range(3):
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 20

        # What helped
        y -= 5
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "What helped me feel better:")
        y -= 15
        for _ in range(3):
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 20

        self._draw_page_number(c, page_num, trim)

    def _draw_thought_record(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "THOUGHT RECORD")
        y -= 8

        c.setFont("Helvetica", 7)
        c.drawString(trim.content_left, y, "Challenge negative thoughts by examining the evidence")
        y -= 20

        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)

        for label, prompt in self._THOUGHT_RECORD:
            if y < trim.content_bottom + 30:
                break
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left, y, label)
            c.setFont("Helvetica", 7)
            c.drawString(trim.content_left + 5, y - 12, prompt)
            y -= 22
            for _ in range(3):
                c.line(trim.content_left, y, trim.content_right, y)
                y -= 18
            y -= 8

        self._draw_page_number(c, page_num, trim)

    def _draw_grounding_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "5-4-3-2-1 GROUNDING EXERCISE")
        y -= 8
        c.setFont("Helvetica", 7)
        c.drawString(trim.content_left, y, "Use your senses to anchor yourself in the present moment")
        y -= 25

        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)

        for prompt in self._GROUNDING_EXERCISE:
            if y < trim.content_bottom + 40:
                break
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left, y, prompt)
            y -= 18
            num_lines = int(prompt[0])  # 5, 4, 3, 2, or 1
            for _ in range(num_lines):
                c.line(trim.content_left + 15, y, trim.content_right, y)
                y -= 18
            y -= 10

        # Reflection
        y -= 5
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "How do I feel now?")
        y -= 15
        for _ in range(3):
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 20

        self._draw_page_number(c, page_num, trim)


# ---------------------------------------------------------------------------
# Fitness Log
# ---------------------------------------------------------------------------

class FitnessLogTemplate(InteriorTemplate):
    """Fitness log with sets/reps/weight tracking tables."""

    name = "fitness"
    description = "Workout log with exercise tracking, sets/reps/weight tables, and notes"

    def __init__(self):
        super().__init__()

    @property
    def line_color(self) -> Color:
        return Color(*(self.style.line_color if self.style else (0.78, 0.78, 0.82)))

    @property
    def label_color(self) -> Color:
        return Color(*(self.style.prompt_color if self.style else (0.3, 0.3, 0.35)))

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        # Header
        c.setFont("Helvetica", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "Date: _______________")
        c.drawRightString(trim.content_right, y, "Day:  M  T  W  T  F  S  S")
        y -= 20

        # Workout type + duration
        c.drawString(trim.content_left, y, "Workout Type: ______________________")
        c.drawRightString(trim.content_right, y, "Duration: ________")
        y -= 25

        # Exercise table header
        c.setFont("Helvetica-Bold", 8)
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.8)

        cols = [
            (trim.content_left, "EXERCISE"),
            (trim.content_left + trim.content_width * 0.35, "SET 1"),
            (trim.content_left + trim.content_width * 0.48, "SET 2"),
            (trim.content_left + trim.content_width * 0.61, "SET 3"),
            (trim.content_left + trim.content_width * 0.74, "SET 4"),
            (trim.content_left + trim.content_width * 0.87, "REST"),
        ]

        # Draw header row
        c.setFillColor(self.label_color)
        for x, label in cols:
            c.drawString(x + 2, y + 2, label)
        y -= 3
        c.line(trim.content_left, y, trim.content_right, y)
        y -= 2

        # Sub-header (reps x weight)
        c.setFont("Helvetica", 6)
        for x, label in cols[1:-1]:
            c.drawString(x + 2, y, "reps × wt")
        y -= 10

        # 8 exercise rows
        c.setLineWidth(0.4)
        row_height = 28
        for _ in range(8):
            if y - row_height < trim.content_bottom + 80:
                break
            # Row lines
            c.line(trim.content_left, y, trim.content_right, y)
            # Vertical separators
            for x, _ in cols[1:]:
                c.line(x - 3, y, x - 3, y - row_height)
            y -= row_height

        # Bottom border of table
        c.line(trim.content_left, y, trim.content_right, y)
        y -= 20

        # Cardio section
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "CARDIO")
        y -= 15
        c.setFont("Helvetica", 8)
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)
        c.drawString(trim.content_left, y, "Type: ________________  Duration: _______  Distance: _______  Calories: _______")
        y -= 25

        # Notes and how I feel
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "NOTES & HOW I FEEL")
        y -= 15
        while y > trim.content_bottom + 20:
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 18

        self._draw_page_number(c, page_num, trim)


# ---------------------------------------------------------------------------
# Budget Tracker
# ---------------------------------------------------------------------------

class BudgetTrackerTemplate(InteriorTemplate):
    """Budget tracker with expense categories and totals."""

    name = "budget"
    description = "Budget tracker with expense categories, income tracking, and monthly summary"

    _EXPENSE_CATEGORIES = [
        "Housing / Rent",
        "Utilities",
        "Groceries",
        "Transportation",
        "Insurance",
        "Subscriptions",
        "Dining Out",
        "Entertainment",
        "Health / Medical",
        "Personal Care",
        "Clothing",
        "Savings / Investments",
        "Debt Payments",
        "Other",
    ]

    def __init__(self):
        super().__init__()

    @property
    def line_color(self) -> Color:
        return Color(*(self.style.line_color if self.style else (0.78, 0.78, 0.78)))

    @property
    def label_color(self) -> Color:
        return Color(*(self.style.prompt_color if self.style else (0.25, 0.25, 0.30)))

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        page_type = page_num % 2
        if page_type == 1:
            self._draw_expense_tracker(c, page_num, trim)
        else:
            self._draw_daily_spending(c, page_num, trim)

    def _draw_expense_tracker(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "MONTHLY BUDGET")
        c.setFont("Helvetica", 9)
        c.drawRightString(trim.content_right, y, "Month: _______________")
        y -= 25

        # Income section
        c.setFont("Helvetica-Bold", 9)
        c.drawString(trim.content_left, y, "INCOME")
        y -= 15
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)
        mid = trim.content_left + trim.content_width * 0.65
        for label in ["Salary / Wages", "Side Income", "Other Income", "TOTAL INCOME"]:
            c.setFont("Helvetica-Bold" if "TOTAL" in label else "Helvetica", 8)
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left + 5, y, label)
            c.line(mid, y - 2, trim.content_right, y - 2)
            y -= 16
        y -= 10

        # Expense categories table
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "EXPENSES")

        # Column headers
        budget_x = mid
        actual_x = mid + trim.content_width * 0.18
        c.setFont("Helvetica-Bold", 7)
        c.drawString(budget_x, y, "BUDGET")
        c.drawString(actual_x, y, "ACTUAL")
        y -= 15

        c.setLineWidth(0.4)
        for cat in self._EXPENSE_CATEGORIES:
            if y < trim.content_bottom + 40:
                break
            c.setFont("Helvetica", 8)
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left + 5, y, cat)
            c.line(budget_x, y - 2, budget_x + trim.content_width * 0.15, y - 2)
            c.line(actual_x, y - 2, trim.content_right, y - 2)
            y -= 16

        # Totals
        y -= 5
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left + 5, y, "TOTAL EXPENSES")
        c.line(budget_x, y - 2, budget_x + trim.content_width * 0.15, y - 2)
        c.line(actual_x, y - 2, trim.content_right, y - 2)
        y -= 20
        c.drawString(trim.content_left + 5, y, "REMAINING (Income - Expenses)")
        c.line(actual_x, y - 2, trim.content_right, y - 2)

        self._draw_page_number(c, page_num, trim)

    def _draw_daily_spending(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "DAILY SPENDING LOG")
        c.setFont("Helvetica", 9)
        c.drawRightString(trim.content_right, y, "Week of: _______________")
        y -= 20

        # Table header
        c.setFont("Helvetica-Bold", 8)
        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.6)

        date_x = trim.content_left
        desc_x = trim.content_left + trim.content_width * 0.15
        cat_x = trim.content_left + trim.content_width * 0.55
        amt_x = trim.content_left + trim.content_width * 0.78

        c.setFillColor(self.label_color)
        c.drawString(date_x + 2, y, "DATE")
        c.drawString(desc_x + 2, y, "DESCRIPTION")
        c.drawString(cat_x + 2, y, "CATEGORY")
        c.drawString(amt_x + 2, y, "AMOUNT")
        y -= 5
        c.line(trim.content_left, y, trim.content_right, y)
        y -= 2

        # Rows
        c.setLineWidth(0.3)
        row_height = 18
        while y - row_height > trim.content_bottom + 30:
            y -= row_height
            c.line(trim.content_left, y, trim.content_right, y)
            # Vertical separators
            for vx in [desc_x, cat_x, amt_x]:
                c.line(vx, y, vx, y + row_height)

        # Daily total
        y -= 5
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "DAILY TOTAL: $________")

        self._draw_page_number(c, page_num, trim)


# ---------------------------------------------------------------------------
# Reading Log
# ---------------------------------------------------------------------------

class ReadingLogTemplate(InteriorTemplate):
    """Reading log with book tracking fields."""

    name = "reading"
    description = "Reading log with title, author, rating, favorite quotes, and review fields"

    _RATING_LABEL = "★ ★ ★ ★ ★"

    def __init__(self):
        super().__init__()

    @property
    def line_color(self) -> Color:
        return Color(*(self.style.line_color if self.style else (0.78, 0.78, 0.82)))

    @property
    def label_color(self) -> Color:
        return Color(*(self.style.prompt_color if self.style else (0.30, 0.30, 0.38)))

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        # Book number
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        book_num = (page_num + 1) // 2  # 2 pages per book
        page_type = page_num % 2

        if page_type == 1:
            self._draw_book_info(c, page_num, trim, book_num)
        else:
            self._draw_book_review(c, page_num, trim, book_num)

    def _draw_book_info(self, c: Canvas, page_num: int, trim: TrimSize, book_num: int) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, f"BOOK #{book_num}")
        y -= 25

        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)

        fields = [
            ("Title:", 1),
            ("Author:", 1),
            ("Genre:", 1),
            ("Pages:", 1),
            ("Date Started:", 1),
            ("Date Finished:", 1),
            ("Format:  ☐ Physical   ☐ Kindle   ☐ Audiobook", 0),
        ]

        for label, has_line in fields:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left, y, label)
            if has_line:
                label_width = c.stringWidth(label, "Helvetica-Bold", 9)
                c.line(trim.content_left + label_width + 10, y - 2, trim.content_right, y - 2)
            y -= 22

        # Rating
        y -= 5
        c.setFont("Helvetica-Bold", 9)
        c.drawString(trim.content_left, y, "Rating:")
        c.setFont("Helvetica", 14)
        c.drawString(trim.content_left + 50, y - 2, "☆  ☆  ☆  ☆  ☆")
        y -= 25

        # Would recommend?
        c.setFont("Helvetica-Bold", 9)
        c.drawString(trim.content_left, y, "Would I recommend this?   ☐ Yes   ☐ No   ☐ Maybe")
        y -= 25

        # Why I picked this book
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "Why I picked this book:")
        y -= 15
        for _ in range(3):
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 18

        # Favorite quote
        y -= 10
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "Favorite Quote:")
        y -= 15
        for _ in range(4):
            c.line(trim.content_left, y, trim.content_right, y)
            y -= 18

        self._draw_page_number(c, page_num, trim)

    def _draw_book_review(self, c: Canvas, page_num: int, trim: TrimSize, book_num: int) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, f"BOOK #{book_num} — REVIEW")
        y -= 25

        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)

        sections = [
            ("Summary in my own words:", 5),
            ("What I loved:", 4),
            ("What I didn't like:", 3),
            ("Key takeaways or lessons:", 4),
            ("How this book changed my thinking:", 3),
        ]

        for label, num_lines in sections:
            if y < trim.content_bottom + 40:
                break
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left, y, label)
            y -= 15
            for _ in range(num_lines):
                c.line(trim.content_left, y, trim.content_right, y)
                y -= 18
            y -= 8

        self._draw_page_number(c, page_num, trim)


# ---------------------------------------------------------------------------
# Meal Planner
# ---------------------------------------------------------------------------

class MealPlannerTemplate(InteriorTemplate):
    """Weekly meal planner with grocery list."""

    name = "meal"
    description = "Weekly meal planner with breakfast/lunch/dinner, snacks, and grocery list"

    _DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    _MEALS = ["Breakfast", "Lunch", "Dinner", "Snacks"]

    def __init__(self):
        super().__init__()

    @property
    def line_color(self) -> Color:
        return Color(*(self.style.line_color if self.style else (0.80, 0.80, 0.78)))

    @property
    def label_color(self) -> Color:
        return Color(*(self.style.prompt_color if self.style else (0.32, 0.38, 0.32)))

    def draw_page(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        page_type = page_num % 2
        if page_type == 1:
            self._draw_meal_plan(c, page_num, trim)
        else:
            self._draw_grocery_list(c, page_num, trim)

    def _draw_meal_plan(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "WEEKLY MEAL PLAN")
        c.setFont("Helvetica", 9)
        c.drawRightString(trim.content_right, y, "Week of: _______________")
        y -= 20

        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.5)

        # Calculate column widths
        day_col = trim.content_width * 0.18
        meal_col = (trim.content_width - day_col) / len(self._MEALS)

        # Header row
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(self.label_color)
        for i, meal in enumerate(self._MEALS):
            x = trim.content_left + day_col + i * meal_col
            c.drawString(x + 3, y, meal)
        y -= 5
        c.setLineWidth(0.6)
        c.line(trim.content_left, y, trim.content_right, y)

        # Day rows
        row_height = (y - trim.content_bottom - 20) / len(self._DAYS)
        row_height = min(row_height, 55)

        c.setLineWidth(0.3)
        for day in self._DAYS:
            if y - row_height < trim.content_bottom + 20:
                break
            y -= row_height
            c.line(trim.content_left, y, trim.content_right, y)

            # Day label (vertical center of row)
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(self.label_color)
            c.drawString(trim.content_left + 3, y + row_height / 2, day[:3])

            # Vertical separators
            for i in range(len(self._MEALS)):
                x = trim.content_left + day_col + i * meal_col
                c.line(x, y, x, y + row_height)

        self._draw_page_number(c, page_num, trim)

    def _draw_grocery_list(self, c: Canvas, page_num: int, trim: TrimSize) -> None:
        y = trim.content_top

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.label_color)
        c.drawString(trim.content_left, y, "GROCERY LIST")
        y -= 20

        c.setStrokeColor(self.line_color)
        c.setLineWidth(0.4)

        categories = [
            "Produce", "Protein", "Dairy & Eggs",
            "Grains & Bread", "Pantry Staples", "Frozen", "Other",
        ]

        # Two columns
        col_width = trim.content_width * 0.47
        col_gap = trim.content_width * 0.06
        left_col = trim.content_left
        right_col = trim.content_left + col_width + col_gap

        cols = [left_col, right_col]
        col_y = [y, y]

        for i, cat in enumerate(categories):
            col = i % 2
            x = cols[col]
            cy = col_y[col]

            if cy < trim.content_bottom + 40:
                break

            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(self.label_color)
            c.drawString(x, cy, cat.upper())
            cy -= 14

            # Checkbox lines
            for _ in range(5):
                c.rect(x, cy - 2, 8, 8, fill=0)
                c.line(x + 14, cy - 2, x + col_width, cy - 2)
                cy -= 15

            cy -= 8
            col_y[col] = cy

        self._draw_page_number(c, page_num, trim)
