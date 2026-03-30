"""Tests for KDP uploader — focus on author name splitting fix."""

import pytest
from unittest.mock import MagicMock


class TestAuthorNameSplit:
    """Tests for the author name splitting logic (bug #7 fix).

    The logic lives in KDPUploader._fill_book_details but we test the
    splitting algorithm directly since the full method requires Playwright.
    """

    @staticmethod
    def _split_author(author: str | None) -> tuple[str, str]:
        """Replicate the splitting logic from uploader.py:444-446."""
        author_parts = author.rsplit(" ", 1) if author else ["", ""]
        first_name = author_parts[0] if len(author_parts) > 1 else ""
        last_name = author_parts[1] if len(author_parts) > 1 else author_parts[0]
        return first_name, last_name

    def test_two_word_name(self):
        first, last = self._split_author("John Smith")
        assert first == "John"
        assert last == "Smith"

    def test_three_word_name(self):
        first, last = self._split_author("Mary Jane Watson")
        assert first == "Mary Jane"
        assert last == "Watson"

    def test_single_word_name(self):
        """Single-word name should go to last_name only (bug #7)."""
        first, last = self._split_author("Madonna")
        assert first == ""
        assert last == "Madonna"

    def test_none_author(self):
        first, last = self._split_author(None)
        assert first == ""
        assert last == ""

    def test_empty_string_author(self):
        first, last = self._split_author("")
        assert first == ""
        assert last == ""

    def test_name_with_extra_spaces(self):
        first, last = self._split_author("Jean  Claude  Van Damme")
        assert first == "Jean  Claude  Van"
        assert last == "Damme"


class TestUploadResultDataclass:
    def test_defaults(self):
        from libro.kdp.uploader import UploadResult
        r = UploadResult(variant_id=1)
        assert r.success is False
        assert r.published is False
        assert r.skipped is False
        assert r.error is None
        assert r.retries == 0


class TestBatchResult:
    def test_failed_variant_ids(self):
        from libro.kdp.uploader import BatchResult, UploadResult
        batch = BatchResult(
            total=3,
            details=[
                UploadResult(variant_id=1, success=True, published=True),
                UploadResult(variant_id=2, error="timeout"),
                UploadResult(variant_id=3, skipped=True, error="user skipped"),
            ],
        )
        # Only variant 2 should be in failed (3 is skipped)
        assert batch.failed_variant_ids == [2]

    def test_empty_batch(self):
        from libro.kdp.uploader import BatchResult
        batch = BatchResult()
        assert batch.failed_variant_ids == []
