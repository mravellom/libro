"""Database engine, session factory, and declarative base."""

from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from libro.config import get_settings, PROJECT_ROOT


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
