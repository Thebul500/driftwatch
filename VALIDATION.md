# Real-World Validation Report

**Project**: driftwatch v0.1.0
**Date**: 2026-03-06
**Environment**: Docker Compose (app + postgres:16-alpine) on Linux 6.17.0-14-generic
**Stack**: FastAPI + asyncpg + PostgreSQL 16 + JWT auth

## Stack Deployment

Docker Compose stack started successfully with two containers:

| Container | Image | Status | Ports |
|---|---|---|---|
| driftwatch-app-1 | driftwatch-app | Up (healthy) | 0.0.0.0:8000->8000/tcp |
| driftwatch-postgres-1 | postgres:16-alpine | Up (healthy) | 0.0.0.0:5432->5432/tcp |

**Resource usage (idle after tests)**:
- App: 0.20% CPU, 64.63 MiB RAM
- PostgreSQL: 0.05% CPU, 28.85 MiB RAM

**Note**: The app lifespan was updated to auto-create database tables on startup via `Base.metadata.create_all()`, since no Alembic migration files existed yet.

## API Validation Results

All 15 tests passed. Every endpoint returned the expected HTTP status code and response body.

### 1. Health Check

```
Timestamp: 2026-03-06T17:09:47Z
GET /health
HTTP 200

{"status":"healthy","version":"0.1.0","timestamp":"2026-03-06T17:09:47.969998Z"}
```

### 2. Readiness Check

```
Timestamp: 2026-03-06T17:09:55Z
GET /ready
HTTP 200

{"status":"ready"}
```

### 3. OpenAPI Schema

```
Timestamp: 2026-03-06T17:09:56Z
GET /openapi.json
HTTP 200

{
  "title": "driftwatch",
  "version": "0.1.0",
  "paths": [
    "/health",
    "/ready",
    "/auth/register",
    "/auth/login",
    "/snapshots",
    "/snapshots/{snapshot_id}"
  ]
}
```

### 4. Register User

```
Timestamp: 2026-03-06T17:10:01Z
POST /auth/register
HTTP 201

{"id":1,"username":"testuser","email":"test@example.com"}
```

### 5. Duplicate Registration (error path)

```
Timestamp: 2026-03-06T17:10:06Z
POST /auth/register (same credentials)
HTTP 400

{"detail":"Username already taken"}
```

### 6. Login

```
Timestamp: 2026-03-06T17:10:11Z
POST /auth/login
HTTP 200

{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzcyODE4ODExfQ.1BpDLR4385in-_HPEog4WcQ1ljrQoJ1p489d_iWqE6k","token_type":"bearer"}
```

### 7. Bad Login (error path)

```
Timestamp: 2026-03-06T17:10:15Z
POST /auth/login (wrong password)
HTTP 401

{"detail":"Invalid credentials"}
```

### 8. Create Snapshot

```
Timestamp: 2026-03-06T17:10:21Z
POST /snapshots (with Bearer token)
HTTP 201

{"id":1,"name":"docker-compose-config","source":"docker","content":"version: 3.9\nservices:\n  app:\n    image: driftwatch","baseline":true,"owner_id":1,"created_at":"2026-03-06T17:10:21.541032","updated_at":"2026-03-06T17:10:21.541032"}
```

A second snapshot was also created (id=2, source="crontab", baseline=false).

### 9. List Snapshots

```
Timestamp: 2026-03-06T17:10:26Z
GET /snapshots (with Bearer token)
HTTP 200

[
    {
        "id": 1,
        "name": "docker-compose-config",
        "source": "docker",
        "content": "version: 3.9\nservices:\n  app:\n    image: driftwatch",
        "baseline": true,
        "owner_id": 1,
        "created_at": "2026-03-06T17:10:21.541032",
        "updated_at": "2026-03-06T17:10:21.541032"
    },
    {
        "id": 2,
        "name": "crontab-snapshot",
        "source": "crontab",
        "content": "* * * * * /usr/bin/healthcheck",
        "baseline": false,
        "owner_id": 1,
        "created_at": "2026-03-06T17:10:21.805566",
        "updated_at": "2026-03-06T17:10:21.805566"
    }
]
```

### 10. Get Single Snapshot

```
Timestamp: 2026-03-06T17:10:29Z
GET /snapshots/1 (with Bearer token)
HTTP 200

{"id":1,"name":"docker-compose-config","source":"docker","content":"version: 3.9\nservices:\n  app:\n    image: driftwatch","baseline":true,"owner_id":1,"created_at":"2026-03-06T17:10:21.541032","updated_at":"2026-03-06T17:10:21.541032"}
```

### 11. Update Snapshot

```
Timestamp: 2026-03-06T17:10:32Z
PUT /snapshots/1 (with Bearer token)
HTTP 200

{"id":1,"name":"docker-compose-config-v2","source":"docker","content":"version: 3.9\nservices:\n  app:\n    image: driftwatch:latest\n  postgres:\n    image: postgres:16","baseline":true,"owner_id":1,"created_at":"2026-03-06T17:10:21.541032","updated_at":"2026-03-06T17:10:32.459685"}
```

`updated_at` changed from `17:10:21` to `17:10:32`, confirming the server-side timestamp update works.

### 12. Get Nonexistent Snapshot (error path)

```
Timestamp: 2026-03-06T17:10:33Z
GET /snapshots/999 (with Bearer token)
HTTP 404

{"detail":"Snapshot not found"}
```

### 13. Delete Snapshot

```
Timestamp: 2026-03-06T17:10:37Z
DELETE /snapshots/2 (with Bearer token)
HTTP 204

(empty body)
```

### 14. List After Delete

```
Timestamp: 2026-03-06T17:10:39Z
GET /snapshots (with Bearer token)
HTTP 200

[
    {
        "id": 1,
        "name": "docker-compose-config-v2",
        "source": "docker",
        "content": "version: 3.9\nservices:\n  app:\n    image: driftwatch:latest\n  postgres:\n    image: postgres:16",
        "baseline": true,
        "owner_id": 1,
        "created_at": "2026-03-06T17:10:21.541032",
        "updated_at": "2026-03-06T17:10:32.459685"
    }
]
```

Snapshot #2 is gone, confirming delete worked.

### 15. Unauthenticated Access (error path)

```
Timestamp: 2026-03-06T17:10:39Z
GET /snapshots (no token)
HTTP 401

{"detail":"Not authenticated"}
```

## Summary

| # | Test | Endpoint | Expected | Actual | Result |
|---|---|---|---|---|---|
| 1 | Health check | GET /health | 200 | 200 | PASS |
| 2 | Readiness | GET /ready | 200 | 200 | PASS |
| 3 | OpenAPI schema | GET /openapi.json | 200 | 200 | PASS |
| 4 | Register user | POST /auth/register | 201 | 201 | PASS |
| 5 | Duplicate register | POST /auth/register | 400 | 400 | PASS |
| 6 | Login | POST /auth/login | 200 | 200 | PASS |
| 7 | Bad login | POST /auth/login | 401 | 401 | PASS |
| 8 | Create snapshot | POST /snapshots | 201 | 201 | PASS |
| 9 | List snapshots | GET /snapshots | 200 | 200 | PASS |
| 10 | Get snapshot | GET /snapshots/1 | 200 | 200 | PASS |
| 11 | Update snapshot | PUT /snapshots/1 | 200 | 200 | PASS |
| 12 | Nonexistent snapshot | GET /snapshots/999 | 404 | 404 | PASS |
| 13 | Delete snapshot | DELETE /snapshots/2 | 204 | 204 | PASS |
| 14 | List after delete | GET /snapshots | 200 | 200 | PASS |
| 15 | Unauthenticated access | GET /snapshots | 401 | 401 | PASS |

**15/15 tests passed.**

## Limitations and Notes

- **No Alembic migrations**: The `alembic/versions/` directory is empty. Tables are created on startup via `create_all()`. A proper migration should be generated before production use.
- **docker-compose.yml version key**: The `version: "3.9"` attribute is obsolete per Docker Compose v2 and triggers a warning.
- **Secret key**: The `DRIFTWATCH_SECRET_KEY` env var must be set; the fallback generates a random key on each restart, which invalidates all existing JWT tokens.
- **No rate limiting**: Auth endpoints (register/login) have no rate limiting. Production deployments should add throttling.
- **CORS wide open**: `allow_origins=["*"]` is fine for development but should be restricted in production.
