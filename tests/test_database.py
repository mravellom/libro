"""Tests for database module — schema migration quoting fix."""

import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy import create_engine, text, inspect, Column, Integer, String

from libro.database import Base, ensure_schema


class TestEnsureSchemaQuoting:
    """Tests for the SQL identifier quoting fix (bug #9)."""

    def test_adds_missing_column_with_quoted_identifiers(self):
        """New columns should use quoted table/column names in ALTER TABLE."""
        engine = create_engine("sqlite:///:memory:")

        # Create a table with only 'id' column directly in DB
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE "niches" (id INTEGER PRIMARY KEY)'))

        # Now Base.metadata has the full Niche model (with many columns)
        # ensure_schema should add the missing ones with proper quoting
        import libro.models  # noqa: F401

        with patch("libro.database.get_engine", return_value=engine), \
             patch("libro.database.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(database_url="sqlite:///:memory:")
            ensure_schema()

        # Verify columns were added
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("niches")}
        assert "keyword" in cols
        assert "status" in cols

    def test_no_error_on_already_complete_schema(self):
        """ensure_schema should be idempotent — no error if schema is complete."""
        engine = create_engine("sqlite:///:memory:")
        import libro.models  # noqa: F401

        # Create full schema first
        Base.metadata.create_all(engine)

        with patch("libro.database.get_engine", return_value=engine), \
             patch("libro.database.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(database_url="sqlite:///:memory:")
            # Should not raise
            ensure_schema()


class TestGetSession:
    def test_session_commits_on_success(self):
        from libro.database import get_session

        engine = create_engine("sqlite:///:memory:")
        import libro.models  # noqa: F401
        Base.metadata.create_all(engine)

        with patch("libro.database.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value = MagicMock(return_value=mock_session)

            with get_session() as session:
                pass

            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_session_rolls_back_on_error(self):
        from libro.database import get_session

        with patch("libro.database.get_session_factory") as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value = MagicMock(return_value=mock_session)

            with pytest.raises(ValueError):
                with get_session() as session:
                    raise ValueError("test error")

            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()
            mock_session.close.assert_called_once()
