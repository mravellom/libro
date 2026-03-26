"""Tests for the thematic interior templates."""

import tempfile
from pathlib import Path

from libro.generation.interior import generate_interior


def test_anxiety_journal_template_generates_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("anxiety", Path(tmpdir) / "anxiety.pdf", "6x9", page_count=6, seed=42)
        assert path.exists()
        assert path.stat().st_size > 0


def test_fitness_log_template_generates_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("fitness", Path(tmpdir) / "fitness.pdf", "6x9", page_count=6, seed=42)
        assert path.exists()
        assert path.stat().st_size > 0


def test_budget_tracker_template_generates_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("budget", Path(tmpdir) / "budget.pdf", "6x9", page_count=6, seed=42)
        assert path.exists()
        assert path.stat().st_size > 0


def test_reading_log_template_generates_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("reading", Path(tmpdir) / "reading.pdf", "6x9", page_count=6, seed=42)
        assert path.exists()
        assert path.stat().st_size > 0


def test_meal_planner_template_generates_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_interior("meal", Path(tmpdir) / "meal.pdf", "6x9", page_count=6, seed=42)
        assert path.exists()
        assert path.stat().st_size > 0
