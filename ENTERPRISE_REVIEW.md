# Enterprise Readiness Review

Review date: 2026-03-06
Reviewer: automated self-evaluation

---

## Competitors

The infrastructure drift detection space is segmented into four categories. No single tool covers driftwatch's intended niche — lightweight, non-IaC drift detection for system-level configuration.

### 1. driftctl (Snyk)

- **GitHub**: ~2.6K stars
- **Key features**: Terraform state vs. live cloud resource comparison, multi-cloud (AWS/Azure/GCP), CI/CD integration, `.driftignore` suppression, JSON/HTML output
- **Target audience**: DevOps teams managing cloud infrastructure via Terraform
- **Limitation**: In maintenance mode since 2023. Requires Terraform state files — useless for non-IaC infrastructure. No Docker, crontab, or package monitoring.

### 2. osquery (Meta/community)

- **GitHub**: ~23.1K stars
- **Key features**: SQL interface to OS state (processes, packages, crontabs, Docker stats, network), cross-platform, scheduled queries, daemon mode
- **Target audience**: Security teams, large-scale fleet monitoring
- **Limitation**: Not a drift detector — no baseline/diff/alerting. Requires building your own comparison and notification pipeline on top. Steep learning curve, resource-heavy.

### 3. Wazuh

- **GitHub**: ~14.7K stars
- **Key features**: File integrity monitoring (FIM), rootkit detection, vulnerability scanning, CIS benchmarks, ELK/OpenSearch dashboards, active response
- **Target audience**: SOC teams, enterprise security operations
- **Limitation**: Full XDR/SIEM platform — massive deployment (manager + agents + Elasticsearch). FIM is file-checksum-based, not semantic. No Docker config drift, no crontab-as-structured-data, no package version timeline.

### 4. DriftHound

- **GitHub**: New project, low stars
- **Key features**: Receives Terraform/OpenTofu/Terragrunt drift reports via API, historical tracking, GitHub Actions integration, Docker/K8s deployment
- **Target audience**: DevOps teams with Terraform-managed infrastructure
- **Limitation**: Terraform-only. Requires running `terraform plan` externally. No support for non-IaC infrastructure. AGPL-3.0 license.

### 5. Steampipe (Turbot)

- **GitHub**: ~7.7K stars
- **Key features**: SQL queries against 140+ cloud/SaaS APIs, zero-ETL, single binary, PostgreSQL FDW, 2000+ queryable tables, MCP server for AI agents
- **Target audience**: Platform teams, cloud security engineers
- **Limitation**: Cloud API query tool, not a drift detector. No baseline storage, no diff engine, no alerting. Must build drift detection on top.

### 6. CloudQuery

- **GitHub**: ~6.3K stars
- **Key features**: High-performance data pipelines from 70+ cloud/SaaS sources, asset inventory, CSPM, FinOps, vulnerability management
- **Target audience**: Platform engineering teams, regulated environments
- **Limitation**: Cloud-focused ETL pipeline. No local infrastructure monitoring (Docker configs, crontabs, firewall rules). No built-in drift alerting.

### 7. Ansible (check mode)

- **GitHub**: ~64K stars
- **Key features**: Agentless config management, `--check` dry-run mode, diff output, massive module library
- **Target audience**: Operations teams, infrastructure engineers
- **Limitation**: Drift detection is a side effect, not a feature. Check mode unreliable with shell/command modules. Exits SUCCESS even when drift detected. Requires maintaining playbooks that define desired state. No drift history or timeline.

### 8. Spacelift / env0 (commercial)

- **Key features**: Scheduled Terraform drift detection, auto-remediation, policy-driven responses, visual dashboards, FinOps integration
- **Target audience**: Enterprise DevOps teams
- **Limitation**: Commercial SaaS, Terraform/IaC-only, not open source.

### Summary Table

| Tool | Docker drift | Crontab drift | Firewall rules | Package versions | Baseline+diff | Alerting | Setup complexity |
|------|:-----------:|:-------------:|:--------------:|:----------------:|:-------------:|:--------:|:----------------:|
| driftctl | - | - | - | - | Terraform only | - | Medium |
| osquery | Partial | Query only | Partial | Query only | - | - | High |
| Wazuh | - | File checksum | - | - | Checksum only | Via SIEM | Very high |
| DriftHound | - | - | - | - | Terraform only | Slack | Medium |
| Steampipe | - | - | - | - | - | - | Low |
| CloudQuery | - | - | - | - | - | - | Medium |
| Ansible | - | - | - | - | Desired-state | - | Medium |
| **Driftwatch** | **Planned** | **Planned** | **Planned** | **Planned** | **Yes** | **Planned** | **Low** |

---

## Functionality Gaps

### What we claim vs. what we have

The project description promises: "Snapshots Docker configs, crontabs, firewall rules, and package versions. Alerts via Signal when anything changes unexpectedly. Stores baselines in SQLite, diffs on schedule."

**Honest assessment of current state:**

| Claimed Feature | Status | Notes |
|----------------|--------|-------|
| Snapshot storage | **Implemented** | CRUD API for snapshots with baseline flag |
| Docker config collection | **Missing** | No collector code — snapshots are manually submitted text blobs |
| Crontab collection | **Missing** | No collector code |
| Firewall rule collection | **Missing** | No collector code |
| Package version collection | **Missing** | No collector code |
| Diff engine | **Missing** | No endpoint to compare two snapshots |
| Baseline comparison | **Missing** | Can mark baseline=true but no comparison logic |
| Signal alerting | **Missing** | No Signal REST API integration |
| Scheduled collection | **Missing** | No scheduler, no cron, no periodic tasks |
| Host management | **Missing** | No Host model — can't track multiple servers |
| Drift event recording | **Missing** | No DriftEvent model or history |

### Core functions missing vs. best competitors

1. **No diff engine** — The fundamental operation of a drift detector (compare state A to state B) doesn't exist. osquery, Wazuh, and driftctl all have comparison capabilities built in. We have none.

2. **No collectors** — Every competitor either has built-in data collection (osquery, Wazuh agents) or integrates with an external collection mechanism (driftctl reads tfstate, DriftHound receives plan output). Driftwatch requires the user to manually POST snapshot content via API, which makes it a generic document store, not a drift detector.

3. **No alerting** — Signal integration is mentioned in the project description but not implemented. Wazuh has SIEM-based alerting, DriftHound has Slack, Spacelift/env0 have email/Slack/webhooks. We have nothing.

4. **No scheduling** — No way to run periodic checks. Competitors either have built-in schedulers (osquery daemon, Wazuh agent) or integrate with external schedulers (DriftHound via GitHub Actions cron).

5. **No host concept** — Can't associate snapshots with specific hosts/servers. For multi-server monitoring this is essential. osquery and Wazuh have per-host enrollment.

6. **No pagination** — `GET /snapshots` returns all snapshots with no limit. With hundreds of snapshots this will be a performance problem and usability issue.

### Common workflows we don't support

- "Show me what changed since my last approved baseline" — no diff endpoint
- "Alert me when a new cron job appears" — no collector, no diff, no alerting
- "Compare Docker configs across two servers" — no host model, no diff
- "Show drift history for the past week" — no drift event model
- "Automatically check every hour" — no scheduler

---

## Quality Gaps

### What's good

- **Clean architecture**: FastAPI + SQLAlchemy async + Pydantic schemas, well-structured
- **Proper auth**: JWT with bcrypt password hashing, token expiry, ownership isolation
- **Good test coverage**: 33+ integration tests covering auth, CRUD, ownership isolation, edge cases
- **Production deployment**: Docker Compose with PostgreSQL, Alembic migrations, multi-stage Dockerfile, non-root container user
- **Security posture**: SECURITY.md, bandit in CI, secrets loaded from environment, CORS configured
- **Performance**: Benchmarked at 2300+ req/s for health endpoints
- **Documentation**: Deployment guide, competitive analysis

### What needs work

1. **CORS is wide open**: `allow_origins=["*"]` with `allow_credentials=True` is a security risk. Should be configurable.

2. **No request rate limiting**: No protection against brute-force login attempts or API abuse.

3. **No pagination on list endpoints**: Will break with large datasets.

4. **Health endpoint doesn't check database**: `/health` returns "healthy" even if the database is down. A real health check should verify database connectivity.

5. **No structured error format**: Errors return bare `{"detail": "..."}` strings. A standard error envelope (`{"error": {"code": "...", "message": "..."}}`) would be more professional.

6. **bcrypt imported directly**: `pyproject.toml` lists `passlib[bcrypt]` as a dependency but the code imports `bcrypt` directly. Either use passlib or remove it from deps.

7. **Secret key auto-generation**: If `DRIFTWATCH_SECRET_KEY` is not set, a random key is generated on every restart, invalidating all existing JWT tokens. The deployment docs say it's required but the code has a fallback.

8. **No OpenAPI description enrichment**: API docs at `/docs` work but endpoints lack detailed descriptions, examples, and response documentation.

---

## Improvement Plan

### Critical (must have for real users)

1. **Add diff endpoint** — `POST /snapshots/diff` accepting two snapshot IDs and returning a unified diff. This is THE core feature. *Implementing now.*

2. **Add baseline comparison** — `GET /snapshots/{id}/drift` that finds the latest baseline for the same source/name and returns the diff. Makes drift detection a first-class API operation. *Implementing now.*

3. **Add pagination and filtering** — `limit`, `offset`, `source`, `baseline` query params on `GET /snapshots`. Essential for usability at scale. *Implementing now.*

4. **Add collectors** — Modules that run `docker inspect`, parse `/var/spool/cron`, dump `iptables-save`, list packages via `dpkg-query`/`rpm -qa`. Without these, driftwatch is a CRUD API, not a drift detector. *Not implementing in this gate — requires significant design work.*

5. **Add Signal alerting** — HTTP POST to Signal REST API when drift is detected. *Not implementing in this gate.*

6. **Add scheduler** — Periodic snapshot collection and baseline comparison. *Not implementing in this gate.*

### Important (should have)

7. **Add Host model** — Associate snapshots with hosts for multi-server tracking.
8. **Add DriftEvent model** — Record drift detections with timestamp, severity, diff content.
9. **Database health check** — `/health` should verify DB connectivity.
10. **Rate limiting** — Protect auth endpoints from brute force.
11. **Configurable CORS** — Move allowed origins to environment config.

### Nice to have

12. **Webhook alerting** — Generic webhook for Slack/Discord/etc.
13. **OpenAPI examples** — Rich API documentation.
14. **Export formats** — JSON, CSV, HTML report generation.

---

## Improvements Implemented

### 1. Diff endpoint (`POST /snapshots/diff`)

Compares any two snapshots and returns a unified diff. Supports comparing across sources and hosts. Returns structured JSON with diff lines, change summary, and whether drift was detected.

### 2. Baseline drift check (`GET /snapshots/{id}/drift`)

Compares a snapshot against the most recent baseline for the same source. Returns the diff plus metadata about which baseline was used. Returns 404 if no baseline exists. This makes "has this drifted from baseline?" a single API call.

### 3. Pagination and filtering on list endpoint

`GET /snapshots` now supports:
- `limit` (default 50, max 200) — page size
- `offset` (default 0) — pagination offset
- `source` — filter by source type (e.g., "docker", "crontab")
- `baseline` — filter by baseline status (true/false)

Response includes total count and pagination metadata.

---

## Final Verdict

**NOT READY** for real users.

### Reasoning

The project has a solid technical foundation — clean FastAPI architecture, proper authentication, good test coverage, production Docker deployment, and a well-researched competitive analysis that identifies a genuine market gap. The diff and pagination improvements implemented in this review bring the API closer to being useful.

However, the core value proposition — "snapshots Docker configs, crontabs, firewall rules, and package versions; alerts via Signal when anything changes" — is **not yet implemented**. Without collectors, scheduling, and alerting, driftwatch is a generic snapshot CRUD API with a diff engine bolted on. Users must manually POST snapshot content and manually trigger comparisons.

To be ready for real users, driftwatch needs:
1. At least one working collector (Docker would be the easiest starting point)
2. A scheduler or clear integration path for external scheduling (cron examples)
3. Signal or webhook alerting on detected drift
4. A DriftEvent model to record drift history

The gap between "what the README promises" and "what the code delivers" is too large. A user installing driftwatch today would find a well-built CRUD API and be confused about how to actually detect drift.

**Path to READY**: Implement Docker collector + cron-based scheduling + Signal alerting. That turns driftwatch from "CRUD API with diff" into "actual drift detector." Estimated scope: 3-4 focused development sessions.
