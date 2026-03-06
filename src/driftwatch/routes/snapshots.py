"""Snapshot CRUD and drift detection endpoints."""

import difflib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Snapshot, User
from ..schemas import (
    DiffRequest,
    DiffResponse,
    DriftCheckResponse,
    PaginatedSnapshots,
    SnapshotCreate,
    SnapshotResponse,
    SnapshotUpdate,
)

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


def _compute_diff(base_content: str, target_content: str, base_label: str, target_label: str):
    """Compute a unified diff between two content strings."""
    base_lines = base_content.splitlines(keepends=True)
    target_lines = target_content.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(base_lines, target_lines, fromfile=base_label, tofile=target_label)
    )
    additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    # Strip trailing newlines from diff lines for clean JSON output
    diff_lines = [line.rstrip("\n") for line in diff_lines]
    return diff_lines, additions, deletions


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


@router.get("", response_model=PaginatedSnapshots)
async def list_snapshots(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source: str | None = Query(default=None),
    baseline: bool | None = Query(default=None),
):
    """List snapshots with pagination and optional filtering."""
    query = select(Snapshot).where(Snapshot.owner_id == user.id)
    count_query = select(func.count()).select_from(Snapshot).where(Snapshot.owner_id == user.id)

    if source is not None:
        query = query.where(Snapshot.source == source)
        count_query = count_query.where(Snapshot.source == source)
    if baseline is not None:
        query = query.where(Snapshot.baseline == baseline)
        count_query = count_query.where(Snapshot.baseline == baseline)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Snapshot.id).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedSnapshots(
        items=[SnapshotResponse.model_validate(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/diff", response_model=DiffResponse)
async def diff_snapshots(
    body: DiffRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare two snapshots and return a unified diff."""
    base = await _get_owned_snapshot(body.base_snapshot_id, user, db)
    target = await _get_owned_snapshot(body.target_snapshot_id, user, db)

    diff_lines, additions, deletions = _compute_diff(
        str(base.content), str(target.content), str(base.name), str(target.name)
    )

    return DiffResponse(
        base_snapshot_id=int(base.id),
        target_snapshot_id=int(target.id),
        base_name=str(base.name),
        target_name=str(target.name),
        base_source=str(base.source),
        target_source=str(target.source),
        drift_detected=len(diff_lines) > 0,
        diff_lines=diff_lines,
        additions=additions,
        deletions=deletions,
    )


@router.get("/{snapshot_id}/drift", response_model=DriftCheckResponse)
async def check_drift(
    snapshot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare a snapshot against the most recent baseline for the same source."""
    snapshot = await _get_owned_snapshot(snapshot_id, user, db)

    # Find the most recent baseline with the same source, excluding the snapshot itself
    result = await db.execute(
        select(Snapshot)
        .where(
            Snapshot.owner_id == user.id,
            Snapshot.source == snapshot.source,
            Snapshot.baseline == True,  # noqa: E712
            Snapshot.id != snapshot.id,
        )
        .order_by(Snapshot.id.desc())
        .limit(1)
    )
    baseline = result.scalar_one_or_none()
    if not baseline:
        raise HTTPException(
            status_code=404, detail=f"No baseline found for source '{snapshot.source}'"
        )

    diff_lines, additions, deletions = _compute_diff(
        str(baseline.content), str(snapshot.content), str(baseline.name), str(snapshot.name)
    )

    return DriftCheckResponse(
        snapshot_id=int(snapshot.id),
        baseline_id=int(baseline.id),
        snapshot_name=str(snapshot.name),
        source=str(snapshot.source),
        drift_detected=len(diff_lines) > 0,
        diff_lines=diff_lines,
        additions=additions,
        deletions=deletions,
    )


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
