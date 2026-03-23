"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libro.database import Base
import libro.models  # noqa: F401 — register all models


@pytest.fixture
def db_session():
    """In-memory SQLite session for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_niche(db_session):
    from libro.models import Niche
    niche = Niche(keyword="anxiety journal", category="Self-Help")
    db_session.add(niche)
    db_session.commit()
    db_session.refresh(niche)
    return niche


@pytest.fixture
def sample_products(db_session, sample_niche):
    from libro.models import Product
    products = [
        Product(asin="B0TEST0001", niche_id=sample_niche.id, title="Anxiety Journal for Women", bsr=45000, price=7.99, reviews_count=23),
        Product(asin="B0TEST0002", niche_id=sample_niche.id, title="Daily Anxiety Workbook", bsr=82000, price=9.99, reviews_count=156),
        Product(asin="B0TEST0003", niche_id=sample_niche.id, title="Calm Mind Journal", bsr=120000, price=6.99, reviews_count=8),
    ]
    db_session.add_all(products)
    db_session.commit()
    return products
