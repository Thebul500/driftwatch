# Driftwatch Use Cases

## Overview

Driftwatch is an infrastructure drift detector that snapshots system configurations and alerts when unexpected changes occur. It provides a REST API for storing, comparing, and managing configuration snapshots across your infrastructure.

## Use Case 1: Docker Compose Drift Detection

**Scenario:** You manage multiple servers running Docker Compose stacks. After a teammate edits a `docker-compose.yml` in production without going through the normal change process, services start behaving unexpectedly.

**How Driftwatch helps:**

1. Register and authenticate with the API.
2. Create a baseline snapshot of each host's `docker-compose.yml`.
3. Periodically capture new snapshots from the same source.
4. Compare the latest snapshot content against the baseline to detect unauthorized changes.

```bash
# Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "ops", "email": "ops@example.com", "password": "secure-pass-123"}'

# Login to get a JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ops", "password": "secure-pass-123"}' | jq -r .access_token)

# Store a baseline snapshot
curl -X POST http://localhost:8000/snapshots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web-server docker-compose",
    "source": "docker-compose",
    "content": "'"$(cat docker-compose.yml | jq -Rs .)"'",
    "baseline": true
  }'
```

## Use Case 2: Crontab Auditing

**Scenario:** A scheduled job disappears from a server's crontab after a system update. No one notices until a nightly backup stops running.

**How Driftwatch helps:**

1. Snapshot each server's crontab as a baseline.
2. Run a cron job that periodically captures the current crontab and POSTs it to Driftwatch.
3. Compare against the baseline to detect removed, added, or modified entries.

```bash
# Capture crontab as a snapshot
CRONTAB_CONTENT=$(crontab -l 2>/dev/null || echo "no crontab")
curl -X POST http://localhost:8000/snapshots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$(hostname) crontab $(date +%F)\",
    \"source\": \"crontab\",
    \"content\": $(echo "$CRONTAB_CONTENT" | jq -Rs .),
    \"baseline\": false
  }"
```

## Use Case 3: Firewall Rule Monitoring

**Scenario:** You run OPNsense or iptables firewalls. A rule gets accidentally deleted during maintenance, opening a port that should be blocked.

**How Driftwatch helps:**

1. Export firewall rules (e.g., `iptables-save` or OPNsense API export) and store as a baseline snapshot.
2. Schedule periodic captures. When the current state differs from the baseline, you know drift has occurred.
3. Use the snapshot history to identify exactly what changed and when.

## Use Case 4: Package Version Pinning

**Scenario:** An unattended system upgrade bumps a critical library to an incompatible version, breaking your application.

**How Driftwatch helps:**

1. Capture `pip freeze`, `dpkg --get-selections`, or `rpm -qa` output as a baseline snapshot.
2. After deployments or on a schedule, capture a new snapshot.
3. Diff the two to find packages that were added, removed, or changed versions.

```bash
# Store installed packages as a snapshot
pip freeze | curl -X POST http://localhost:8000/snapshots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "name": "app-server packages $(date +%F)",
  "source": "pip-packages",
  "content": "$(pip freeze | jq -Rs .)",
  "baseline": false
}
EOF
```

## Use Case 5: Multi-Environment Baseline Comparison

**Scenario:** Your staging and production environments should be identical, but over time they diverge in subtle ways that cause "works on staging, fails in production" issues.

**How Driftwatch helps:**

1. Create baseline snapshots from production for each config type (Docker, packages, crontabs, firewall rules).
2. Capture the same configs from staging.
3. Compare snapshot content across environments to find divergence before it causes incidents.
