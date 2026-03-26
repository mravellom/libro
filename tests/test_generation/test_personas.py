"""Tests for buyer personas module."""

from libro.generation.personas import (
    PERSONAS,
    get_persona_by_name,
    get_personas_for_niche,
)


def test_personas_list_has_14_entries():
    assert len(PERSONAS) == 14


def test_get_personas_for_niche_anxiety_journal():
    personas = get_personas_for_niche("anxiety journal")
    names = [p.name for p in personas]
    assert "anxiety_warrior" in names


def test_get_personas_for_niche_budget_planner():
    personas = get_personas_for_niche("budget planner")
    names = [p.name for p in personas]
    assert "debt_free_dreamer" in names


def test_get_personas_for_niche_hiking_journal():
    personas = get_personas_for_niche("hiking journal")
    names = [p.name for p in personas]
    assert "outdoor_adventurer" in names


def test_get_persona_by_name_existing():
    persona = get_persona_by_name("new_mom")
    assert persona is not None
    assert persona.name == "new_mom"
    assert persona.label == "New Moms"


def test_get_persona_by_name_nonexistent():
    assert get_persona_by_name("nonexistent") is None


def test_fallback_for_obscure_niche():
    personas = get_personas_for_niche("something obscure")
    assert len(personas) >= 2
