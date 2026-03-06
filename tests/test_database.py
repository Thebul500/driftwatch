"""Tests for database module."""

from unittest.mock import AsyncMock, patch

import pytest

from driftwatch.database import Base, async_session, engine, get_db


def test_engine_exists():
    """Engine is created at module level."""
    assert engine is not None


def test_async_session_factory_exists():
    """Async session factory is created at module level."""
    assert async_session is not None


def test_base_is_declarative():
    """Base has SQLAlchemy metadata."""
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "registry")


@pytest.mark.asyncio
async def test_get_db_yields_session():
    """get_db yields a database session."""
    mock_session = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("driftwatch.database.async_session", return_value=mock_session_ctx):
        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session
