"""Isolated SQLite fixtures for backend integration tests."""

import os
from collections.abc import Generator

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["SECRET_KEY"] = "test-secret-that-is-not-used-outside-tests"

import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.core.database import Base, engine
from app.crud.categories import ensure_default_categories
from app.db.session import SessionLocal
from app.main import app


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    """Create a fresh schema for every test."""

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_default_categories(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """FastAPI client using the shared in-memory connection pool."""

    with TestClient(app) as test_client:
        yield test_client
