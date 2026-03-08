"""Tests for the Click CLI."""

import json
import tempfile
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from driftwatch import db, drift
from driftwatch.cli import cli


class TestCLI:
    """Tests for CLI commands."""

    def setup_method(self):
        self.runner = CliRunner()
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test.db"
        # Patch DB_PATH so all CLI commands use our temp db
        self.db_patcher = mock.patch("driftwatch.db.DB_PATH", self.db_path)
        self.db_patcher.start()

    def teardown_method(self):
        self.db_patcher.stop()

    def test_version(self):
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "driftwatch" in result.output

    def test_snapshot(self):
        result = self.runner.invoke(cli, ["snapshot", "--name", "test"])
        assert result.exit_code == 0
        assert "Snapshot saved" in result.output
        assert "test" in result.output

    def test_snapshot_json(self):
        result = self.runner.invoke(cli, ["snapshot", "--name", "test", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "test"
        assert "data" in data

    def test_baseline(self):
        result = self.runner.invoke(cli, ["baseline", "--name", "my-base"])
        assert result.exit_code == 0
        assert "Baseline saved" in result.output
        assert "my-base" in result.output

        # Verify it's actually a baseline
        latest = db.get_latest_baseline(db_path=self.db_path)
        assert latest is not None
        assert latest["name"] == "my-base"

    def test_list_empty(self):
        result = self.runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "No snapshots found" in result.output

    def test_list_with_snapshots(self):
        self.runner.invoke(cli, ["snapshot", "--name", "s1"])
        self.runner.invoke(cli, ["baseline", "--name", "b1"])
        result = self.runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "s1" in result.output
        assert "b1" in result.output
        assert "*" in result.output  # baseline marker

    def test_list_json(self):
        self.runner.invoke(cli, ["snapshot", "--name", "s1"])
        result = self.runner.invoke(cli, ["list", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "s1"

    def test_check_no_baseline(self):
        result = self.runner.invoke(cli, ["check"])
        assert result.exit_code == 1
        assert "No baseline" in result.output

    def test_check_with_baseline(self):
        self.runner.invoke(cli, ["baseline"])
        result = self.runner.invoke(cli, ["check"])
        # Exit 0 (no drift) or 2 (drift detected) are both valid
        assert result.exit_code in (0, 2)

    def test_diff_snapshots(self):
        self.runner.invoke(cli, ["snapshot", "--name", "s1"])
        self.runner.invoke(cli, ["snapshot", "--name", "s2"])

        snapshots = db.list_snapshots(db_path=self.db_path)
        id1 = snapshots[-1]["id"]  # oldest
        id2 = snapshots[0]["id"]  # newest

        result = self.runner.invoke(cli, ["diff", str(id1), str(id2)])
        assert result.exit_code == 0
        assert "Comparing" in result.output

    def test_diff_nonexistent(self):
        result = self.runner.invoke(cli, ["diff", "999", "1000"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_diff_json(self):
        self.runner.invoke(cli, ["snapshot", "--name", "s1"])
        self.runner.invoke(cli, ["snapshot", "--name", "s2"])

        snapshots = db.list_snapshots(db_path=self.db_path)
        id1 = snapshots[-1]["id"]
        id2 = snapshots[0]["id"]

        result = self.runner.invoke(cli, ["diff", str(id1), str(id2), "-j"])
        assert result.exit_code == 0
        json.loads(result.output)  # should be valid JSON
