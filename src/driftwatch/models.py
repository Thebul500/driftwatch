"""SQLAlchemy database models."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class BaseModel(Base):
    """Abstract base with common fields."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(BaseModel):
    """Application user for authentication."""

    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    snapshots = relationship("Snapshot", back_populates="owner", cascade="all, delete-orphan")


class Snapshot(BaseModel):
    """Infrastructure configuration snapshot."""

    __tablename__ = "snapshots"

    name = Column(String(200), nullable=False)
    source = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    baseline = Column(Boolean, default=False, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="snapshots")
