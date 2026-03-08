"""Drift detection engine.

Takes snapshots of system state and compares them to detect
configuration drift (added, removed, or modified items).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import collectors, db


def take_snapshot(
    name: str | None = None,
    is_baseline: bool = False,
    db_path: Path | None = None,
) -> dict:
    """Collect current system state and save as a snapshot.

    Returns the saved snapshot dict (with id, name, timestamp, data).
    """
    state = collectors.collect_all()
    snapshot_id = db.save_snapshot(state, name=name, is_baseline=is_baseline, db_path=db_path)
    snapshot = db.get_snapshot(snapshot_id, db_path=db_path)
    assert snapshot is not None
    return snapshot


def compare(snap1_data: dict, snap2_data: dict) -> dict[str, dict]:
    """Deep-diff two snapshot data dicts.

    Returns a dict keyed by collector name, each containing:
    - added: items in snap2 but not snap1
    - removed: items in snap1 but not snap2
    - modified: items present in both but with different values
    """
    all_keys = set(snap1_data.keys()) | set(snap2_data.keys())
    changes: dict[str, dict] = {}

    for section in sorted(all_keys):
        old = snap1_data.get(section, {})
        new = snap2_data.get(section, {})
        section_diff = _diff_dicts(old, new)
        if section_diff["added"] or section_diff["removed"] or section_diff["modified"]:
            changes[section] = section_diff

    return changes


def check_drift(db_path: Path | None = None) -> dict:
    """Compare current system state against the most recent baseline.

    Returns:
        dict with keys: has_drift, baseline_id, baseline_name, changes
    """
    baseline = db.get_latest_baseline(db_path=db_path)
    if baseline is None:
        return {
            "has_drift": False,
            "error": "No baseline found. Run 'driftwatch baseline' first.",
            "baseline_id": None,
            "baseline_name": None,
            "changes": {},
        }

    current_state = collectors.collect_all()
    changes = compare(baseline["data"], current_state)

    return {
        "has_drift": len(changes) > 0,
        "baseline_id": baseline["id"],
        "baseline_name": baseline["name"],
        "changes": changes,
    }


def _diff_dicts(old: Any, new: Any) -> dict:
    """Compare two dicts and return added/removed/modified."""
    result: dict[str, dict] = {"added": {}, "removed": {}, "modified": {}}

    if not isinstance(old, dict) or not isinstance(new, dict):
        # If either isn't a dict, treat the whole thing as a change
        if old != new:
            result["modified"]["_value"] = {"old": old, "new": new}
        return result

    old_keys = set(old.keys())
    new_keys = set(new.keys())

    for key in sorted(new_keys - old_keys):
        result["added"][key] = new[key]

    for key in sorted(old_keys - new_keys):
        result["removed"][key] = old[key]

    for key in sorted(old_keys & new_keys):
        if old[key] != new[key]:
            result["modified"][key] = {"old": old[key], "new": new[key]}

    return result
