"""System state collectors.

Each collector gathers a specific aspect of system configuration
and returns a dict representing the current state.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _run(cmd: list[str], timeout: int = 30) -> str:
    """Run a command and return stdout. Returns empty string on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def collect_docker() -> dict:
    """Collect running Docker container configurations.

    Uses ``docker ps --format json`` to list containers, then
    ``docker inspect`` on each to capture full config.
    Returns a dict keyed by container name.
    """
    containers: dict[str, dict] = {}

    # Get running container IDs and names
    raw = _run(["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"])
    if not raw:
        return containers

    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        cid, name, image, status = parts[0], parts[1], parts[2], parts[3]

        # Inspect for full config
        inspect_raw = _run(["docker", "inspect", "--format", "json", cid])
        inspect_data = {}
        if inspect_raw:
            try:
                parsed = json.loads(inspect_raw)
                if isinstance(parsed, list) and parsed:
                    full = parsed[0]
                    # Extract the useful bits, skip volatile fields
                    config = full.get("Config", {})
                    host_config = full.get("HostConfig", {})
                    inspect_data = {
                        "image": config.get("Image", image),
                        "env": sorted(config.get("Env", [])),
                        "cmd": config.get("Cmd"),
                        "entrypoint": config.get("Entrypoint"),
                        "ports": host_config.get("PortBindings", {}),
                        "binds": host_config.get("Binds", []),
                        "network_mode": host_config.get("NetworkMode", ""),
                        "restart_policy": host_config.get("RestartPolicy", {}),
                    }
            except (json.JSONDecodeError, KeyError, IndexError):
                inspect_data = {}

        containers[name] = {
            "id": cid,
            "image": image,
            "status": status,
            **inspect_data,
        }

    return containers


def collect_crontabs() -> dict:
    """Collect crontab entries from the system.

    Reads from:
    - ``crontab -l`` (current user)
    - ``/var/spool/cron/crontabs/`` (all users, if readable)
    - ``/etc/cron.d/`` (system cron files)
    """
    crontabs: dict[str, list[str]] = {}

    # Current user crontab
    raw = _run(["crontab", "-l"])
    if raw:
        lines = [
            line for line in raw.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if lines:
            crontabs["current_user"] = sorted(lines)

    # System cron directories
    for cron_dir in [
        Path("/var/spool/cron/crontabs"),
        Path("/var/spool/cron"),
        Path("/etc/cron.d"),
    ]:
        if not cron_dir.is_dir():
            continue
        try:
            for cron_file in sorted(cron_dir.iterdir()):
                if cron_file.is_file() and not cron_file.name.startswith("."):
                    try:
                        content = cron_file.read_text()
                        lines = [
                            line
                            for line in content.splitlines()
                            if line.strip() and not line.strip().startswith("#")
                        ]
                        if lines:
                            key = f"{cron_dir.name}/{cron_file.name}"
                            crontabs[key] = sorted(lines)
                    except PermissionError:
                        continue
        except PermissionError:
            continue

    return crontabs


def collect_packages() -> dict:
    """Collect installed package versions.

    Tries ``dpkg-query`` first (Debian/Ubuntu), falls back to
    ``rpm -qa`` (RHEL/Fedora).
    Returns a dict of package_name -> version.
    """
    packages: dict[str, str] = {}

    # Try dpkg first (Debian/Ubuntu)
    raw = _run(
        ["dpkg-query", "-W", "-f", "${Package}\t${Version}\n"],
        timeout=60,
    )
    if raw:
        for line in raw.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                packages[parts[0]] = parts[1]
        return packages

    # Fallback: rpm (RHEL/Fedora)
    raw = _run(["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}-%{RELEASE}\n"], timeout=60)
    if raw:
        for line in raw.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                packages[parts[0]] = parts[1]

    return packages


def collect_systemd() -> dict:
    """Collect running systemd service units.

    Returns a dict of service_name -> state info.
    """
    services: dict[str, dict] = {}

    raw = _run([
        "systemctl",
        "list-units",
        "--type=service",
        "--state=running",
        "--no-pager",
        "--no-legend",
        "--plain",
    ])
    if not raw:
        return services

    for line in raw.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4:
            unit = parts[0]
            # Strip .service suffix for cleaner names
            name = unit.removesuffix(".service")
            services[name] = {
                "load": parts[1],
                "active": parts[2],
                "sub": parts[3],
                "description": parts[4] if len(parts) > 4 else "",
            }

    return services


ALL_COLLECTORS = {
    "docker": collect_docker,
    "crontabs": collect_crontabs,
    "packages": collect_packages,
    "systemd": collect_systemd,
}


def collect_all() -> dict:
    """Run all collectors and return combined state dict."""
    state: dict[str, dict] = {}
    for name, collector in ALL_COLLECTORS.items():
        try:
            state[name] = collector()
        except Exception as exc:
            state[name] = {"_error": str(exc)}
    return state
