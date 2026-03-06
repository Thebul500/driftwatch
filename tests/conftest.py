"""Test fixtures."""

import os

# Set required env vars before importing driftwatch (Settings validates on import)
os.environ.setdefault("DRIFTWATCH_SECRET_KEY", "test-secret-key-not-for-production")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from driftwatch.app import create_app  # noqa: E402
from driftwatch.database import Base, get_db  # noqa: E402


@pytest.fixture
def client():
    """Create a test client with an in-memory SQLite database."""
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_client(tmp_path):
    """Create a test client backed by a real SQLite database."""
    db_path = tmp_path / "test.db"
    sync_url = f"sqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    sync_engine = create_engine(sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
