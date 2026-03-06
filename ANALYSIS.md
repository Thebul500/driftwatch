# Competitive Analysis — Infrastructure Drift Detection

Research date: 2026-03-06

## Existing Tools

### 1. driftctl (Snyk)

- **GitHub**: [snyk/driftctl](https://github.com/snyk/driftctl) — ~2.6K stars
- **What it does**: Detects drift between Terraform state and actual cloud resources (AWS, Azure, GCP). Compares `.tfstate` files against live infrastructure and reports discrepancies.
- **Key features**: Multi-cloud support, CI/CD integration, `.driftignore` file for suppression, JSON/HTML output.
- **Limitations**: **In maintenance mode since June 2023** after Snyk acquisition. Requires an existing Terraform state file — useless without IaC. Only covers cloud resources managed by Terraform. 127 open issues including false positives with certain AWS resources. Cannot use different AWS regions for state bucket vs. scanned infra. No support for multiple aliased providers in a single state.
- **User complaints**: Abandonment concerns (maintenance mode), cloud-only scope, Terraform lock-in, no support for bare-metal or self-hosted infrastructure.

### 2. osquery (Meta/community)

- **GitHub**: [osquery/osquery](https://github.com/osquery/osquery) — ~23.1K stars
- **What it does**: Exposes OS-level state as SQL tables. You can query running processes, installed packages, crontabs, Docker containers, network interfaces, and more using SQL syntax.
- **Key features**: Cross-platform (Linux, macOS, Windows), crontab table, Docker container stats, package lists, file integrity monitoring via events, daemon mode with scheduled queries.
- **Limitations**: **Not a drift detector** — it's an instrumentation framework. You must build your own baseline/diff/alerting logic on top. Docker monitoring has issues with high audit event volumes. Cannot access files inside containers. No built-in concept of "baseline vs. current state." Steep learning curve. Resource-heavy in environments with many containers. No native alerting — requires external tools (Fleet, Kolide, SIEM).
- **User complaints**: Complexity of setup and management, no turnkey drift detection, requires significant orchestration to be useful for config monitoring.

### 3. Wazuh (fork of OSSEC)

- **GitHub**: [wazuh/wazuh](https://github.com/wazuh/wazuh) — ~14.5K stars
- **What it does**: Open-source XDR/SIEM platform with file integrity monitoring (FIM), rootkit detection, vulnerability scanning, and compliance auditing. Agent-based architecture with central manager.
- **Key features**: Real-time FIM with checksum comparison, agent auto-registration, ELK/OpenSearch dashboard integration, active response, CIS benchmark scanning.
- **Limitations**: **Massive platform** — FIM is one module in a full security stack. Requires deploying manager + agents + Elasticsearch/OpenSearch + dashboard. FIM misses changes during agent downtime (Issue #22199). Specific file detection bugs on Windows. Database can fill up and halt monitoring. Not designed for Docker config drift or crontab monitoring — focused on file-level changes.
- **User complaints**: Complex deployment for small teams, heavy resource requirements, overkill if you only need config drift detection, FIM gaps during agent restarts.

### 4. DriftHound (drifthoundhq)

- **GitHub**: [drifthoundhq/drifthound](https://github.com/drifthoundhq/drifthound) — new project, low stars
- **What it does**: Rails web app that receives Terraform/OpenTofu/Terragrunt drift reports via API. Provides drift visibility across projects with historical tracking and notifications.
- **Key features**: GitHub Actions integration, CLI for CI/CD pipelines, Docker/Kubernetes deployment, monorepo-friendly, parallel execution, rich reporting.
- **Limitations**: **Terraform/OpenTofu-only** — same IaC dependency as driftctl. Requires running `terraform plan` externally and posting results. No support for non-IaC infrastructure (Docker configs, crontabs, firewall rules, packages). AGPL-3.0 license may be restrictive for some users.
- **User complaints**: Early-stage project with limited community. Only useful if you already manage everything through Terraform.

### 5. Ansible (check mode for drift detection)

- **GitHub**: [ansible/ansible](https://github.com/ansible/ansible) — ~64K stars
- **What it does**: Configuration management tool with a `--check` (dry-run) mode that can identify differences between desired and actual state without making changes.
- **Key features**: Agentless (SSH-based), massive module library, diff output in check mode, idempotent playbooks, huge community.
- **Limitations**: **Drift detection is a side effect, not a feature.** Check mode breaks with `command`/`shell` modules, registered variables, and complex conditionals. Even when drift is detected, playbook exits with SUCCESS status — making automated compliance workflows difficult. You must define the desired state in playbooks first; it can't snapshot current state and detect changes from a baseline. No built-in alerting or drift history.
- **User complaints**: Check mode unreliable for drift detection (community forum threads), SUCCESS exit code on drift is confusing, not designed for continuous monitoring, requires maintaining playbooks that mirror your infrastructure.

### 6. Rudder (Normation)

- **GitHub**: [Normation/rudder](https://github.com/Normation/rudder) — ~550 stars
- **What it does**: Configuration and security automation platform with continuous compliance monitoring. Agent runs every 5 minutes to check/enforce desired state. Web UI with compliance visualization.
- **Key features**: Visual policy editor, YAML config support, Linux + Windows agents, compliance dashboards, audit mode (detect without enforce), built on CFEngine.
- **Limitations**: Small community compared to Ansible/Puppet. No ecosystem like Puppet Forge for sharing modules. Agent-based (requires installation on every node). Focused on traditional config management, not container or Docker-specific. Limited Docker/container awareness.
- **User complaints**: Small community, limited third-party resources, learning curve for policy language, not designed for container-native environments.

### 7. Tripwire Open Source

- **GitHub**: Unmaintained — last update 2018
- **What it does**: Classic file integrity monitoring. Creates checksums of files and directories, alerts when they change.
- **Key features**: File-level integrity checking, policy-based monitoring.
- **Limitations**: **Effectively dead.** Only monitors files, not Docker configs, crontabs, or package versions at a semantic level. No active development. Superseded by OSSEC/Wazuh.

---

## Gap Analysis

After surveying the landscape, there is a clear segmentation:

| Category | Tools | What they cover | What they miss |
|----------|-------|----------------|----------------|
| **IaC drift** | driftctl, DriftHound | Terraform/cloud resources | Non-IaC infra, local servers, Docker configs |
| **Security/FIM** | Wazuh, OSSEC, Tripwire | File checksums, rootkits | Semantic config understanding, Docker state, crontabs as structured data |
| **Config management** | Ansible, Puppet, Rudder | Desired-state enforcement | Baseline snapshots, drift history, lightweight monitoring |
| **OS instrumentation** | osquery | Everything queryable | No baseline/diff/alerting built in |

### Specific gaps no tool fills well:

1. **Docker configuration drift as a first-class concern.** No tool snapshots `docker inspect` output, tracks container config changes (env vars, mounts, ports, image digests), and diffs them against a known-good baseline. osquery can query Docker stats but doesn't baseline or diff. Wazuh monitors files inside containers but not container configuration itself.

2. **Crontab monitoring as structured data.** osquery has a crontab table but no diffing. Wazuh monitors crontab files for checksum changes but doesn't parse entries semantically. No tool alerts you that "a new cron job was added at 3 AM running curl to an external URL."

3. **Firewall rule drift detection.** iptables/nftables rules change and no lightweight tool tracks this. Wazuh doesn't monitor firewall rules. Config management tools can enforce rules but don't provide drift history or alerting.

4. **Package version drift tracking.** Knowing that `openssl` went from 3.0.2 to 3.0.14 overnight matters. osquery can list packages but doesn't track changes over time. No tool provides a simple timeline of "what changed and when" for installed packages.

5. **Simple deployment for small teams / homelabs.** Every existing tool is either cloud-focused (driftctl, DriftHound), enterprise-grade (Wazuh, Rudder), or requires building your own solution (osquery, Ansible). There's nothing that a sysadmin can `pip install`, point at a server, and start getting drift alerts within minutes.

6. **Signal / webhook alerting without a full SIEM.** Existing tools either have no alerting (osquery), require ELK/OpenSearch (Wazuh), or only integrate with enterprise channels (PagerDuty, Slack). None support Signal out of the box, and simple webhook-based alerting is an afterthought.

7. **SQLite-based local storage.** Every tool either requires PostgreSQL/Elasticsearch (Wazuh, DriftHound) or has no persistent storage (Ansible check mode). A lightweight SQLite approach for baseline storage and drift history doesn't exist.

---

## Gap

**No existing tool provides lightweight, turnkey infrastructure drift detection for non-IaC environments.**

The market is split between Terraform-focused tools (useless without IaC) and heavyweight security platforms (overkill for config monitoring). If you run a small fleet of servers, a homelab, or any infrastructure not fully managed by Terraform, there is no simple way to:

- Snapshot Docker container configs, crontabs, firewall rules, and package lists
- Store baselines and compare against them on a schedule
- Get alerted when something changes unexpectedly
- Review a history of what changed, when, and on which host

You'd have to cobble together osquery + custom scripts + a database + an alerting pipeline. That's exactly the gap driftwatch fills.

---

## Differentiator

Driftwatch is **the missing middle ground** between "write your own scripts" and "deploy an enterprise SIEM."

| Feature | driftctl | osquery | Wazuh | DriftHound | **Driftwatch** |
|---------|----------|---------|-------|------------|----------------|
| Docker config drift | No | Partial | No | No | **Yes** |
| Crontab monitoring | No | Query only | File checksum | No | **Structured diff** |
| Firewall rule tracking | No | Partial | No | No | **Yes** |
| Package version history | No | Query only | No | No | **Yes** |
| Baseline + diff engine | N/A (uses tfstate) | No | Checksum only | Terraform plan | **Semantic diff** |
| Alert via Signal/webhook | No | No | Via SIEM | Slack/email | **Signal native** |
| Storage | Terraform state | None | Elasticsearch | PostgreSQL | **SQLite** |
| Setup complexity | Medium | High | Very high | Medium | **Low** |
| Works without IaC | No | Yes | Yes | No | **Yes** |
| Target audience | Cloud teams | Security teams | SOC teams | DevOps teams | **Sysadmins, homelabs, small teams** |

### Core differentiators:

1. **Opinionated collectors for real infrastructure** — Docker, crontab, iptables/nftables, dpkg/rpm. Not file checksums, not Terraform state. Actual system configuration captured as structured data.

2. **Baseline-and-diff model** — Snapshot current state, approve it as baseline, get alerted on deviations. No need to define desired state in a DSL first. Works with brownfield infrastructure as-is.

3. **Minimal footprint** — SQLite storage, single Python process, FastAPI REST API. No Elasticsearch, no agents on every node (initially collects from localhost, extensible to remote hosts via SSH).

4. **Signal-native alerting** — First-class integration with Signal REST API for notifications. Also supports webhooks for other channels. No SIEM required.

5. **Audit trail** — Every snapshot is stored. Every drift event is recorded with timestamp, host, category, and diff. Queryable via REST API. Simple compliance evidence without enterprise tooling.

### Honest assessment:

Driftwatch does **not** compete with Wazuh for security monitoring or driftctl for Terraform state management. It fills a specific niche: **lightweight drift detection for system-level configuration on servers that aren't fully managed by IaC.** If your entire infrastructure is in Terraform, use driftctl or DriftHound. If you need a full SIEM, use Wazuh. If you have servers where people occasionally `apt install` something, add a cron job, or modify Docker configs — and you want to know about it — that's driftwatch.
