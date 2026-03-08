"""Tests for drift detection engine and database storage."""

import tempfile
from pathlib import Path

from driftwatch import db, drift


class TestDatabase:
    """Tests for SQLite snapshot storage."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test.db"

    def test_save_and_get_snapshot(self):
        data = {"packages": {"vim": "8.2"}, "docker": {}}
        sid = db.save_snapshot(data, name="test-snap", db_path=self.db_path)
        assert isinstance(sid, int)
        assert sid > 0

        snap = db.get_snapshot(sid, db_path=self.db_path)
        assert snap is not None
        assert snap["name"] == "test-snap"
        assert snap["data"] == data
        assert snap["is_baseline"] is False

    def test_save_baseline(self):
        data = {"packages": {"vim": "8.2"}}
        sid = db.save_snapshot(data, name="base", is_baseline=True, db_path=self.db_path)
        snap = db.get_snapshot(sid, db_path=self.db_path)
        assert snap is not None
        assert snap["is_baseline"] is True

    def test_get_latest_baseline(self):
        db.save_snapshot({"a": 1}, name="b1", is_baseline=True, db_path=self.db_path)
        db.save_snapshot({"b": 2}, name="b2", is_baseline=True, db_path=self.db_path)
        db.save_snapshot({"c": 3}, name="not-baseline", db_path=self.db_path)

        latest = db.get_latest_baseline(db_path=self.db_path)
        assert latest is not None
        assert latest["name"] == "b2"

    def test_get_nonexistent_snapshot(self):
        assert db.get_snapshot(999, db_path=self.db_path) is None

    def test_get_latest_baseline_none(self):
        assert db.get_latest_baseline(db_path=self.db_path) is None

    def test_list_snapshots(self):
        db.save_snapshot({"a": 1}, name="s1", db_path=self.db_path)
        db.save_snapshot({"b": 2}, name="s2", is_baseline=True, db_path=self.db_path)

        result = db.list_snapshots(db_path=self.db_path)
        assert len(result) == 2
        # Listed in reverse order (newest first)
        assert result[0]["name"] == "s2"
        assert result[0]["is_baseline"] is True
        assert result[1]["name"] == "s1"
        # list_snapshots doesn't include data blob
        assert "data" not in result[0]

    def test_auto_generated_name(self):
        sid = db.save_snapshot({"x": 1}, db_path=self.db_path)
        snap = db.get_snapshot(sid, db_path=self.db_path)
        assert snap is not None
        assert snap["name"].startswith("snapshot-")


class TestCompare:
    """Tests for snapshot comparison / diff logic."""

    def test_identical_snapshots(self):
        data = {"packages": {"vim": "8.2", "git": "2.39"}, "docker": {"nginx": {"image": "nginx:latest"}}}
        changes = drift.compare(data, data)
        assert changes == {}

    def test_added_items(self):
        old = {"packages": {"vim": "8.2"}}
        new = {"packages": {"vim": "8.2", "curl": "7.88"}}
        changes = drift.compare(old, new)
        assert "packages" in changes
        assert "curl" in changes["packages"]["added"]
        assert changes["packages"]["added"]["curl"] == "7.88"

    def test_removed_items(self):
        old = {"packages": {"vim": "8.2", "curl": "7.88"}}
        new = {"packages": {"vim": "8.2"}}
        changes = drift.compare(old, new)
        assert "packages" in changes
        assert "curl" in changes["packages"]["removed"]

    def test_modified_items(self):
        old = {"packages": {"vim": "8.2"}}
        new = {"packages": {"vim": "9.0"}}
        changes = drift.compare(old, new)
        assert "packages" in changes
        assert "vim" in changes["packages"]["modified"]
        assert changes["packages"]["modified"]["vim"]["old"] == "8.2"
        assert changes["packages"]["modified"]["vim"]["new"] == "9.0"

    def test_added_section(self):
        old = {"packages": {"vim": "8.2"}}
        new = {"packages": {"vim": "8.2"}, "docker": {"nginx": {"image": "nginx"}}}
        changes = drift.compare(old, new)
        assert "docker" in changes
        assert "nginx" in changes["docker"]["added"]

    def test_removed_section(self):
        old = {"packages": {"vim": "8.2"}, "docker": {"nginx": {"image": "nginx"}}}
        new = {"packages": {"vim": "8.2"}}
        changes = drift.compare(old, new)
        assert "docker" in changes
        assert "nginx" in changes["docker"]["removed"]

    def test_complex_diff(self):
        old = {
            "docker": {"web": {"image": "nginx:1.24"}, "db": {"image": "postgres:15"}},
            "packages": {"vim": "8.2", "git": "2.39"},
            "systemd": {"ssh": {"active": "active"}},
        }
        new = {
            "docker": {"web": {"image": "nginx:1.25"}, "cache": {"image": "redis:7"}},
            "packages": {"vim": "8.2", "git": "2.40", "curl": "7.88"},
            "systemd": {"ssh": {"active": "active"}},
        }
        changes = drift.compare(old, new)

        # Docker: web modified, db removed, cache added
        assert "docker" in changes
        assert "cache" in changes["docker"]["added"]
        assert "db" in changes["docker"]["removed"]
        assert "web" in changes["docker"]["modified"]

        # Packages: git modified, curl added
        assert "packages" in changes
        assert "curl" in changes["packages"]["added"]
        assert "git" in changes["packages"]["modified"]

        # Systemd: no changes
        assert "systemd" not in changes

    def test_empty_to_populated(self):
        old = {"packages": {}}
        new = {"packages": {"vim": "8.2"}}
        changes = drift.compare(old, new)
        assert "packages" in changes
        assert "vim" in changes["packages"]["added"]

    def test_both_empty(self):
        changes = drift.compare({}, {})
        assert changes == {}


class TestTakeSnapshot:
    """Tests for take_snapshot (integration with collectors)."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test.db"

    def test_take_snapshot_saves_to_db(self):
        snap = drift.take_snapshot(name="test", db_path=self.db_path)
        assert snap["id"] > 0
        assert snap["name"] == "test"
        assert "data" in snap
        assert isinstance(snap["data"], dict)
        # Should have all collector sections
        assert "packages" in snap["data"]
        assert "docker" in snap["data"]
        assert "crontabs" in snap["data"]
        assert "systemd" in snap["data"]

    def test_take_baseline(self):
        snap = drift.take_snapshot(name="base", is_baseline=True, db_path=self.db_path)
        assert snap["is_baseline"] is True

        latest = db.get_latest_baseline(db_path=self.db_path)
        assert latest is not None
        assert latest["id"] == snap["id"]


class TestCheckDrift:
    """Tests for check_drift."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test.db"

    def test_no_baseline_returns_error(self):
        result = drift.check_drift(db_path=self.db_path)
        assert result["has_drift"] is False
        assert "error" in result
        assert result["baseline_id"] is None

    def test_check_drift_against_self(self):
        """Taking a baseline then immediately checking should show minimal drift.

        Note: Some drift may appear due to timing differences in collector output
        (e.g., docker status uptime changes). That's expected behavior.
        """
        drift.take_snapshot(name="base", is_baseline=True, db_path=self.db_path)
        result = drift.check_drift(db_path=self.db_path)
        assert result["baseline_id"] is not None
        assert result["baseline_name"] == "base"
        # We don't assert has_drift is False because collectors may return
        # slightly different data between runs (e.g., docker uptime strings)
