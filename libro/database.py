"""Database engine, session factory, and declarative base."""

import logging
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from libro.config import get_settings, PROJECT_ROOT

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        db_path = PROJECT_ROOT / url.replace("sqlite:///", "")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
    return create_engine(url, echo=False)


def get_session_factory():
    return sessionmaker(bind=get_engine())


def ensure_schema():
    """Auto-migrate missing columns by comparing models to existing DB schema.

    SQLite's create_all() only creates new tables, not new columns.
    This inspects each model table and ADDs any columns defined in the model
    but missing from the DB.
    """
    engine = get_engine()

    # Import all models so Base.metadata is fully populated
    import libro.models  # noqa: F401

    Base.metadata.create_all(engine)

    insp = inspect(engine)
    existing_tables = insp.get_table_names()

    TYPE_MAP = {
        "VARCHAR": "VARCHAR",
        "TEXT": "TEXT",
        "INTEGER": "INTEGER",
        "FLOAT": "FLOAT",
        "BOOLEAN": "BOOLEAN",
        "DATETIME": "DATETIME",
    }

    added = 0
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_cols = {c["name"] for c in insp.get_columns(table.name)}

        for col in table.columns:
            if col.name not in existing_cols:
                col_type = str(col.type)
                for key in TYPE_MAP:
                    if key in col_type.upper():
                        col_type = col_type
                        break

                sql = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"
                with engine.begin() as conn:
                    conn.execute(text(sql))
                log.info(f"Auto-migrated: {sql}")
                added += 1

    if added:
        log.info(f"Schema migration complete: {added} column(s) added")


@contextmanager
def get_session():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
