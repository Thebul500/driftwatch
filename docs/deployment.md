# Deployment Guide

## Prerequisites

- Docker and Docker Compose (recommended), or Python 3.11+
- PostgreSQL 16+

## Docker Compose (Recommended)

The simplest way to run Driftwatch in production:

```bash
git clone https://github.com/Thebul500/driftwatch.git
cd driftwatch

# Set a secure secret key
export SECRET_KEY=$(openssl rand -hex 32)

# Start the stack
docker compose up -d
```

This starts:
- **app** on port 8000 — the Driftwatch API
- **postgres** on port 5432 — PostgreSQL 16 Alpine with a health check

Verify the deployment:

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0","timestamp":"..."}

curl http://localhost:8000/ready
# {"status":"ready"}
```

## Environment Variables

All settings use the `DRIFTWATCH_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `DRIFTWATCH_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/driftwatch` | Async database connection string |
| `DRIFTWATCH_SECRET_KEY` | `change-me-in-production` | JWT signing key. **Must be changed in production.** |
| `DRIFTWATCH_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token lifetime in minutes |
| `DRIFTWATCH_DEBUG` | `false` | Enable debug mode |

## Database Migrations

Driftwatch uses Alembic for schema migrations:

```bash
# Run pending migrations
alembic upgrade head

# Check current revision
alembic current
```

In Docker, migrations run automatically on startup.

## Running Without Docker

```bash
# Install dependencies
pip install -e .

# Set required environment variables
export DRIFTWATCH_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/driftwatch"
export DRIFTWATCH_SECRET_KEY="$(openssl rand -hex 32)"

# Run migrations
alembic upgrade head

# Start the server
uvicorn driftwatch.app:app --host 0.0.0.0 --port 8000
```

## Production Considerations

### Secret Key

Always set `DRIFTWATCH_SECRET_KEY` to a cryptographically random value. Never use the default in production.

### Database

- Use a managed PostgreSQL instance or configure proper backups for the `pgdata` volume.
- The connection string must use the `asyncpg` driver (`postgresql+asyncpg://`).

### Reverse Proxy

Place Driftwatch behind a reverse proxy (Nginx, Caddy, Traefik) for TLS termination:

```nginx
server {
    listen 443 ssl;
    server_name driftwatch.example.com;

    ssl_certificate /etc/ssl/certs/driftwatch.pem;
    ssl_certificate_key /etc/ssl/private/driftwatch.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Health Checks

Use these endpoints for orchestrator probes:

- **Liveness:** `GET /health` — returns app version and status
- **Readiness:** `GET /ready` — returns `{"status": "ready"}` when the app can serve requests
