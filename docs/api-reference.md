# API Reference

Base URL: `http://localhost:8000`

All snapshot endpoints require a JWT Bearer token obtained from `/auth/login`.

## Authentication

### POST /auth/register

Create a new user account.

**Request:**

```json
{
  "username": "ops",
  "email": "ops@example.com",
  "password": "secure-pass-123"
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `username` | string | 3-100 characters |
| `email` | string | Valid email address |
| `password` | string | 8-128 characters |

**Response (201):**

```json
{
  "id": 1,
  "username": "ops",
  "email": "ops@example.com"
}
```

**Errors:**
- `400` — Username already taken or email already registered

### POST /auth/login

Authenticate and receive a JWT token.

**Request:**

```json
{
  "username": "ops",
  "password": "secure-pass-123"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Errors:**
- `401` — Invalid credentials

## Snapshots

All snapshot endpoints require the header: `Authorization: Bearer <token>`

### POST /snapshots

Create a new snapshot.

**Request:**

```json
{
  "name": "web-server docker-compose",
  "source": "docker-compose",
  "content": "version: '3.9'\nservices: ...",
  "baseline": true
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | string | 1-200 characters |
| `source` | string | 1-100 characters (e.g., `docker-compose`, `crontab`, `iptables`, `pip-packages`) |
| `content` | string | Non-empty, the raw configuration content |
| `baseline` | boolean | Default `false`. Set `true` to mark as the reference snapshot. |

**Response (201):**

```json
{
  "id": 1,
  "name": "web-server docker-compose",
  "source": "docker-compose",
  "content": "version: '3.9'\nservices: ...",
  "baseline": true,
  "owner_id": 1,
  "created_at": "2026-03-06T12:00:00",
  "updated_at": "2026-03-06T12:00:00"
}
```

### GET /snapshots

List all snapshots owned by the authenticated user, ordered by ID.

**Response (200):**

```json
[
  {
    "id": 1,
    "name": "web-server docker-compose",
    "source": "docker-compose",
    "content": "...",
    "baseline": true,
    "owner_id": 1,
    "created_at": "2026-03-06T12:00:00",
    "updated_at": "2026-03-06T12:00:00"
  }
]
```

### GET /snapshots/{snapshot_id}

Get a single snapshot by ID. Returns only snapshots owned by the authenticated user.

**Response (200):** Same schema as a single snapshot object above.

**Errors:**
- `404` — Snapshot not found or not owned by the current user

### PUT /snapshots/{snapshot_id}

Update an existing snapshot. All fields are optional; only provided fields are updated.

**Request:**

```json
{
  "name": "updated name",
  "content": "new content...",
  "baseline": false
}
```

**Response (200):** The updated snapshot object.

**Errors:**
- `404` — Snapshot not found or not owned by the current user

### DELETE /snapshots/{snapshot_id}

Delete a snapshot.

**Response:** `204 No Content`

**Errors:**
- `404` — Snapshot not found or not owned by the current user

## Health

### GET /health

Application health check. No authentication required.

**Response (200):**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-03-06T12:00:00"
}
```

### GET /ready

Readiness probe for orchestrators. No authentication required.

**Response (200):**

```json
{
  "status": "ready"
}
```
