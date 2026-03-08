# driftwatch

Configuration snapshot store with diff detection. REST API for storing text snapshots, computing diffs, and detecting drift against baselines. Includes JWT authentication, pagination, and filtering.

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
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Authenticate and get JWT token |
| POST | `/snapshots` | Create a snapshot |
| GET | `/snapshots` | List snapshots (paginated, filterable by source/baseline) |
| GET | `/snapshots/{id}` | Get a single snapshot |
| PUT | `/snapshots/{id}` | Update a snapshot |
| DELETE | `/snapshots/{id}` | Delete a snapshot |
| POST | `/snapshots/diff` | Compute unified diff between two snapshots |
| GET | `/snapshots/{id}/drift` | Check drift against the latest baseline for the same source |

## Configuration

Environment variables (prefix `DRIFTWATCH_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `SECRET_KEY` | *(required)* | JWT signing key |
| `DEBUG` | `false` | Enable debug mode |
