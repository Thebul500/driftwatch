# driftwatch

Infrastructure drift detector. Snapshots Docker configs, crontabs, firewall rules, and package versions. Alerts via Signal when anything changes unexpectedly. Stores baselines in SQLite, diffs on schedule.

[![CI](https://github.com/Thebul500/driftwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/Thebul500/driftwatch/actions)

## Quick Start

```bash
docker compose up -d
curl http://localhost:8000/health
```

## Installation (Development)

```bash
pip install -e .[dev]
uvicorn driftwatch.app:app --reload
```

## Usage

```bash
# Start with Docker Compose (recommended)
docker compose up -d

# Or run directly
uvicorn driftwatch.app:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness probe |

## Configuration

Environment variables (prefix `DRIFTWATCH_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `SECRET_KEY` | *(required)* | JWT signing key |
| `DEBUG` | `false` | Enable debug mode |
