"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime


class UserCreate(BaseModel):
    """User registration request."""

    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """User response (no password)."""

    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """Login request."""

    username: str
    password: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105


class SnapshotCreate(BaseModel):
    """Create snapshot request."""

    name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    baseline: bool = False


class SnapshotUpdate(BaseModel):
    """Update snapshot request."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    source: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)
    baseline: bool | None = None


class SnapshotResponse(BaseModel):
    """Snapshot response."""

    id: int
    name: str
    source: str
    content: str
    baseline: bool
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiffRequest(BaseModel):
    """Request to diff two snapshots."""

    base_snapshot_id: int
    target_snapshot_id: int


class DiffResponse(BaseModel):
    """Diff result between two snapshots."""

    base_snapshot_id: int
    target_snapshot_id: int
    base_name: str
    target_name: str
    base_source: str
    target_source: str
    drift_detected: bool
    diff_lines: list[str]
    additions: int
    deletions: int


class DriftCheckResponse(BaseModel):
    """Result of checking a snapshot against its baseline."""

    snapshot_id: int
    baseline_id: int
    snapshot_name: str
    source: str
    drift_detected: bool
    diff_lines: list[str]
    additions: int
    deletions: int


class PaginatedSnapshots(BaseModel):
    """Paginated snapshot list response."""

    items: list[SnapshotResponse]
    total: int
    limit: int
    offset: int
