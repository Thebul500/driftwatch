# driftwatch

Infrastructure drift detector. Snapshots Docker containers, crontabs, installed packages, and systemd services. Compares snapshots to detect unexpected configuration changes.

[![CI](https://github.com/Thebul500/driftwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/Thebul500/driftwatch/actions)

## What It Does

- **Collects** system state: Docker containers (with full inspect), crontab entries, installed packages (dpkg/rpm), running systemd services
- **Snapshots** the combined state into SQLite with timestamps
- **Baselines** mark a known-good state to compare against
- **Detects drift** by deep-diffing current state against the baseline, reporting exactly what was added, removed, or modified

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Take a baseline of the current system state
driftwatch baseline --name "prod-2026-03-08"

# Later, check if anything has drifted
driftwatch check

# Take a regular snapshot
driftwatch snapshot --name "after-update"

# Compare any two snapshots
driftwatch diff 1 2

# List all snapshots
driftwatch list
```

## Commands

| Command | Description |
|---------|-------------|
| `driftwatch baseline [--name NAME]` | Snapshot current state and mark as baseline |
| `driftwatch check` | Compare current state to baseline, report drift |
| `driftwatch snapshot [--name NAME]` | Take a snapshot without marking as baseline |
| `driftwatch diff <id1> <id2>` | Compare two specific snapshots |
| `driftwatch list` | List all stored snapshots |

All commands support `--json-output` / `-j` for machine-readable output.

## Collectors

| Collector | Source | Data |
|-----------|--------|------|
| Docker | `docker ps` + `docker inspect` | Container configs, images, ports, volumes, env |
| Crontabs | `crontab -l`, `/etc/cron.d/`, `/var/spool/cron/` | Cron entries |
| Packages | `dpkg-query` or `rpm -qa` | Package name + version |
| Systemd | `systemctl list-units` | Running service states |

## Storage

Snapshots are stored in `~/.driftwatch/driftwatch.db` (SQLite).

## Development

```bash
pip install -e .[dev]
pytest -v
```
