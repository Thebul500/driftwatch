# Driftwatch — Project Plan

## Overview

Driftwatch is an infrastructure drift detector that periodically snapshots system configurations — Docker containers, crontabs, firewall rules, and package versions — compares them against known-good baselines, and alerts operators via Signal when unexpected changes occur. It exposes a REST API for managing hosts, baselines, snapshots, and drift events.

---

## Architecture

### System Components

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Collector    │────>│  Driftwatch API  │────>│  PostgreSQL   │
│  (scheduled)  │     │  (FastAPI)       │     │              │
└──────────────┘     └────────┬─────────┘     └──────────────┘
                              │
                     ┌────────▼─────────┐
                     │  Signal REST API  │
                     │  (alerts)         │
                     └──────────────────┘
```

**Driftwatch API** — Central FastAPI service. Manages hosts, baselines, snapshots, and drift records. Runs the diff engine and triggers alerts. Deployed as a Docker container alongside PostgreSQL.

**Collector** — Lightweight agent or scheduled task that gathers system state (Docker inspect output, crontab -l, iptables-save, dpkg/rpm lists) from target hosts and POSTs snapshots to the API. Initially runs as an async background task within the API process for local-host monitoring; can be extracted to a standalone agent later.

**Diff Engine** — Compares incoming snapshots against the stored baseline for each host+resource pair. Produces structured drift records describing what changed (added, removed, modified fields).

**Alert Dispatcher** — When drift is detected, sends notifications via Signal REST API (HTTP POST to the signal-cli container). Extensible to other channels (email, webhooks) later.

**PostgreSQL** — Stores all persistent state: hosts, baselines, snapshots, drift events, and users.

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Health check |
| `GET` | `/ready` | No | Readiness probe |
| `POST` | `/api/v1/auth/register` | No | Create user account |
| `POST` | `/api/v1/auth/login` | No | Get JWT access token |
| `GET` | `/api/v1/hosts` | JWT | List monitored hosts |
| `POST` | `/api/v1/hosts` | JWT | Register a new host |
| `GET` | `/api/v1/hosts/{id}` | JWT | Get host details |
| `DELETE` | `/api/v1/hosts/{id}` | JWT | Remove a host |
| `GET` | `/api/v1/hosts/{id}/baselines` | JWT | List baselines for a host |
| `POST` | `/api/v1/hosts/{id}/baselines` | JWT | Set/update baseline for a resource type |
| `GET` | `/api/v1/snapshots` | JWT | List snapshots (filterable by host, type) |
| `POST` | `/api/v1/snapshots` | JWT | Submit a new snapshot |
| `GET` | `/api/v1/snapshots/{id}` | JWT | Get snapshot details |
| `GET` | `/api/v1/drifts` | JWT | List detected drift events |
| `GET` | `/api/v1/drifts/{id}` | JWT | Get drift event details |
| `POST` | `/api/v1/drifts/{id}/acknowledge` | JWT | Acknowledge (dismiss) a drift |
| `POST` | `/api/v1/drifts/{id}/accept` | JWT | Accept drift as new baseline |

### Data Model

```
User
  id            Integer PK
  username      String UNIQUE
  hashed_password String
  created_at    DateTime

Host
  id            Integer PK
  name          String UNIQUE       -- e.g. "web-prod-01"
  hostname      String              -- IP or FQDN
  description   Text (nullable)
  is_active     Boolean
  created_at    DateTime
  updated_at    DateTime

Baseline
  id            Integer PK
  host_id       Integer FK -> Host
  resource_type String              -- "docker", "crontab", "firewall", "packages"
  content       JSON                -- canonical snapshot data
  set_at        DateTime
  set_by        Integer FK -> User

Snapshot
  id            Integer PK
  host_id       Integer FK -> Host
  resource_type String
  content       JSON                -- raw collected data
  collected_at  DateTime

Drift
  id            Integer PK
  host_id       Integer FK -> Host
  resource_type String
  snapshot_id   Integer FK -> Snapshot
  baseline_id   Integer FK -> Baseline
  diff          JSON                -- structured diff (added/removed/changed)
  severity      String              -- "info", "warning", "critical"
  status        String              -- "open", "acknowledged", "accepted"
  detected_at   DateTime
  resolved_at   DateTime (nullable)
```

### Auth Flow

1. User registers via `POST /api/v1/auth/register` with username + password.
2. Password is hashed with bcrypt (via `passlib`).
3. User logs in via `POST /api/v1/auth/login`, receives a JWT access token.
4. Token is signed with HS256 using `DRIFTWATCH_SECRET_KEY`, expires after `ACCESS_TOKEN_EXPIRE_MINUTES`.
5. Protected endpoints require `Authorization: Bearer <token>` header.
6. FastAPI dependency extracts and validates the token on each request.

### Deployment Architecture

**Docker Compose** (primary deployment):
- `app` — Driftwatch API container (Python 3.11, uvicorn)
- `postgres` — PostgreSQL 16 Alpine
- Shared Docker network, persistent volume for database
- Environment-based configuration (12-factor)

**Production hardening** (later milestones):
- Run behind a reverse proxy (nginx/Traefik) with TLS
- Non-root container user
- Health checks for orchestrator integration
- Alembic migrations run on startup or as an init container

---

## Technology

| Technology | Role | Rationale |
|-----------|------|-----------|
| **Python 3.11+** | Language | Strong async ecosystem, good library support for system introspection, fast development cycle. |
| **FastAPI** | Web framework | Native async/await, automatic OpenAPI docs, Pydantic validation, dependency injection. Best-in-class for building typed REST APIs in Python. |
| **SQLAlchemy 2.0 (async)** | ORM / query builder | Async session support via `asyncpg`, migration support via Alembic, mature and battle-tested. Decouples business logic from raw SQL. |
| **PostgreSQL 16** | Database | JSONB columns for flexible snapshot/diff storage, strong indexing, reliable for production workloads. Runs easily in Docker. |
| **Alembic** | Migrations | Official SQLAlchemy migration tool. Auto-generates migration scripts from model changes. |
| **Pydantic v2** | Validation / schemas | Request/response validation with type safety. Integrates natively with FastAPI. `pydantic-settings` handles environment config. |
| **python-jose** | JWT tokens | Lightweight JWT implementation. HS256 signing for access tokens. |
| **passlib + bcrypt** | Password hashing | Industry-standard password hashing. Bcrypt is slow by design, resistant to brute-force. |
| **httpx** | HTTP client | Async HTTP client for calling Signal REST API and (later) remote collectors. Drop-in replacement for requests with async support. |
| **Docker / Compose** | Deployment | Reproducible builds, easy local development, production-ready with orchestrators. |
| **pytest + pytest-asyncio** | Testing | Async test support, fixtures, good FastAPI integration via `httpx.AsyncClient`. |
| **Ruff** | Linting / formatting | Extremely fast Python linter, replaces flake8 + isort + black. Single tool for code quality. |

---

## Milestones

### Milestone 1 — Core API & Auth
**Goal:** Working API with user authentication and host management.

Deliverables:
- User model with registration and login endpoints
- JWT authentication middleware
- Host CRUD endpoints (create, list, get, delete)
- Alembic migration for initial schema
- Request/response Pydantic schemas for all endpoints
- Unit and integration tests (target: 80% coverage)
- Linting clean (ruff, mypy)

### Milestone 2 — Baselines & Snapshots
**Goal:** Accept and store infrastructure snapshots, manage baselines.

Deliverables:
- Baseline and Snapshot models + migrations
- Endpoints to set baselines and submit snapshots
- Resource type validation (docker, crontab, firewall, packages)
- JSON storage for flexible snapshot content
- Snapshot listing with filters (host, resource type, date range)
- Tests for all new endpoints

### Milestone 3 — Diff Engine & Drift Detection
**Goal:** Automatically detect drift when snapshots diverge from baselines.

Deliverables:
- Diff engine: compare snapshot content against baseline content
- Structured diff output (added, removed, changed keys/values)
- Drift model + migration
- Automatic drift record creation on snapshot submission
- Severity classification (info/warning/critical based on resource type and change scope)
- Drift listing and detail endpoints
- Acknowledge and accept-as-new-baseline actions

### Milestone 4 — Signal Alerting
**Goal:** Notify operators when drift is detected.

Deliverables:
- Alert dispatcher service (async, non-blocking)
- Signal REST API integration via httpx
- Alert configuration (recipients, severity threshold)
- Alert deduplication (don't spam for the same drift)
- Configurable alert templates
- Integration test with mocked Signal API

### Milestone 5 — Scheduled Collection
**Goal:** Automatically collect snapshots on a schedule.

Deliverables:
- Background scheduler (asyncio task or APScheduler)
- Local collectors: Docker (`docker inspect`), crontab, iptables/nftables, dpkg/rpm
- Configurable collection interval per host
- Collection status tracking
- Error handling and retry logic

### Milestone 6 — Production Hardening
**Goal:** Make the system production-ready and secure.

Deliverables:
- Security policy (SECURITY.md)
- Container vulnerability scanning and remediation
- SBOM generation (sbom.json)
- Performance benchmarks (BENCHMARKS.md)
- Rate limiting on auth endpoints
- CORS configuration tightened for production
- Contributing guide (CONTRIBUTING.md)
- Enterprise readiness review (ENTERPRISE_REVIEW.md)
- CI pipeline with coverage enforcement
- End-to-end validation (VALIDATION.md)
