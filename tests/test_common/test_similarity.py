"""Tests for similarity guard — title_similarity, content_fingerprint, check_similarity."""

import pytest

from libro.common.similarity import (
    title_similarity,
    content_fingerprint,
    check_similarity,
    check_catalog_similarity,
)
from libro.models.variant import Variant


class TestTitleSimilarity:
    def test_identical_titles(self):
        assert title_similarity("Anxiety Journal", "Anxiety Journal") == 1.0

    def test_case_insensitive(self):
        assert title_similarity("anxiety journal", "ANXIETY JOURNAL") == 1.0

    def test_strips_whitespace(self):
        assert title_similarity("  Anxiety Journal  ", "Anxiety Journal") == 1.0

    def test_completely_different(self):
        sim = title_similarity("Anxiety Journal", "Cooking Recipes 2024")
        assert sim < 0.4

    def test_similar_titles(self):
        sim = title_similarity("Anxiety Journal for Women", "Anxiety Journal for Men")
        assert 0.7 < sim < 1.0

    def test_empty_strings(self):
        assert title_similarity("", "") == 1.0

    def test_one_empty(self):
        assert title_similarity("Anxiety Journal", "") == 0.0


class TestContentFingerprint:
    def test_deterministic(self):
        fp1 = content_fingerprint("My Title", "lined", "6x9", seed=42)
        fp2 = content_fingerprint("My Title", "lined", "6x9", seed=42)
        assert fp1 == fp2

    def test_different_titles_differ(self):
        fp1 = content_fingerprint("Title A", "lined", "6x9")
        fp2 = content_fingerprint("Title B", "lined", "6x9")
        assert fp1 != fp2

    def test_different_seeds_differ(self):
        fp1 = content_fingerprint("My Title", "lined", "6x9", seed=1)
        fp2 = content_fingerprint("My Title", "lined", "6x9", seed=2)
        assert fp1 != fp2

    def test_none_seed_uses_zero(self):
        fp1 = content_fingerprint("My Title", "lined", "6x9", seed=None)
        fp2 = content_fingerprint("My Title", "lined", "6x9", seed=0)
        assert fp1 == fp2

    def test_returns_16_char_hex(self):
        fp = content_fingerprint("Title", "grid", "5x8")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


class TestCheckSimilarity:
    def _make_variant(self, db_session, niche_id, title, status="draft"):
        v = Variant(
            niche_id=niche_id,
            title=title,
            interior_type="lined",
            trim_size="6x9",
            status=status,
        )
        db_session.add(v)
        db_session.flush()
        return v

    def test_no_existing_variants_returns_empty(self, db_session, sample_niche):
        warnings = check_similarity(db_session, "Totally New Title", sample_niche.id)
        assert warnings == []

    def test_similar_title_produces_warning(self, db_session, sample_niche):
        self._make_variant(db_session, sample_niche.id, "Anxiety Journal for Women")
        warnings = check_similarity(
            db_session, "Anxiety Journal for Men", sample_niche.id, threshold=0.7
        )
        assert len(warnings) == 1
        assert "similar" in warnings[0].lower()

    def test_exact_at_max_similar_not_blocked(self, db_session, sample_niche):
        """max_similar=2 means allow up to 2 similar titles — no BLOCKED."""
        self._make_variant(db_session, sample_niche.id, "Anxiety Journal Vol 1")
        self._make_variant(db_session, sample_niche.id, "Anxiety Journal Vol 2")
        warnings = check_similarity(
            db_session, "Anxiety Journal Vol 3", sample_niche.id,
            threshold=0.7, max_similar=2,
        )
        # Should have 2 similarity warnings but NO BLOCKED
        assert not any("BLOCKED" in w for w in warnings)

    def test_exceeds_max_similar_blocked(self, db_session, sample_niche):
        """Exceeding max_similar triggers BLOCKED."""
        self._make_variant(db_session, sample_niche.id, "Anxiety Journal Vol 1")
        self._make_variant(db_session, sample_niche.id, "Anxiety Journal Vol 2")
        self._make_variant(db_session, sample_niche.id, "Anxiety Journal Vol 3")
        warnings = check_similarity(
            db_session, "Anxiety Journal Vol 4", sample_niche.id,
            threshold=0.7, max_similar=2,
        )
        assert any("BLOCKED" in w for w in warnings)

    def test_rejected_variants_excluded(self, db_session, sample_niche):
        """Variants with status 'rejected' should not count."""
        self._make_variant(db_session, sample_niche.id, "Anxiety Journal Vol 1", status="rejected")
        warnings = check_similarity(
            db_session, "Anxiety Journal Vol 2", sample_niche.id, threshold=0.7
        )
        assert warnings == []


class TestCheckCatalogSimilarity:
    def _make_variant(self, db_session, niche_id, title, status="ready"):
        v = Variant(
            niche_id=niche_id,
            title=title,
            interior_type="lined",
            trim_size="6x9",
            status=status,
        )
        db_session.add(v)
        db_session.flush()
        return v

    def test_no_variants_returns_empty(self, db_session, sample_niche):
        warnings = check_catalog_similarity(db_session, "New Title")
        assert warnings == []

    def test_at_max_similar_not_spam_risk(self, db_session, sample_niche):
        """Exactly max_similar matches should NOT trigger SPAM RISK."""
        for i in range(3):
            self._make_variant(db_session, sample_niche.id, f"Calm Mind Journal {i}")
        warnings = check_catalog_similarity(
            db_session, "Calm Mind Journal New", threshold=0.7, max_similar=3,
        )
        assert not any("SPAM RISK" in w for w in warnings)

    def test_exceeds_max_similar_spam_risk(self, db_session, sample_niche):
        for i in range(5):
            self._make_variant(db_session, sample_niche.id, f"Calm Mind Journal {i}")
        warnings = check_catalog_similarity(
            db_session, "Calm Mind Journal New", threshold=0.7, max_similar=3,
        )
        assert any("SPAM RISK" in w for w in warnings)

    def test_exclude_variant_id(self, db_session, sample_niche):
        v = self._make_variant(db_session, sample_niche.id, "Exact Same Title")
        warnings = check_catalog_similarity(
            db_session, "Exact Same Title", exclude_variant_id=v.id,
        )
        assert warnings == []
