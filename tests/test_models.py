"""Tests for database models."""

from driftwatch.models import BaseModel


def test_basemodel_is_abstract():
    """BaseModel is abstract and cannot be instantiated directly."""
    assert BaseModel.__abstract__ is True


def test_basemodel_has_common_fields():
    """BaseModel defines id, created_at, updated_at columns."""
    assert hasattr(BaseModel, "id")
    assert hasattr(BaseModel, "created_at")
    assert hasattr(BaseModel, "updated_at")
