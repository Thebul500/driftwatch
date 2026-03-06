"""Snapshot CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Snapshot, User
from ..schemas import SnapshotCreate, SnapshotResponse, SnapshotUpdate

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


async def _get_owned_snapshot(
    snapshot_id: int, user: User, db: AsyncSession
) -> Snapshot:
    """Fetch a snapshot owned by the given user, or raise 404."""
    result = await db.execute(
        select(Snapshot).where(Snapshot.id == snapshot_id, Snapshot.owner_id == user.id)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.post("", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    body: SnapshotCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new snapshot."""
    snapshot = Snapshot(
        name=body.name,
        source=body.source,
        content=body.content,
        baseline=body.baseline,
        owner_id=user.id,
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


@router.get("", response_model=list[SnapshotResponse])
async def list_snapshots(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all snapshots for the current user."""
    result = await db.execute(
        select(Snapshot).where(Snapshot.owner_id == user.id).order_by(Snapshot.id)
    )
    return result.scalars().all()


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(
    snapshot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single snapshot by ID."""
    return await _get_owned_snapshot(snapshot_id, user, db)


@router.put("/{snapshot_id}", response_model=SnapshotResponse)
async def update_snapshot(
    snapshot_id: int,
    body: SnapshotUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing snapshot."""
    snapshot = await _get_owned_snapshot(snapshot_id, user, db)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(snapshot, field, value)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


@router.delete("/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snapshot(
    snapshot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a snapshot."""
    snapshot = await _get_owned_snapshot(snapshot_id, user, db)
    await db.delete(snapshot)
    await db.commit()
