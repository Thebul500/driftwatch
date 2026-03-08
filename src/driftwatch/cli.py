"""Click CLI for driftwatch.

Commands:
    snapshot  -- Take a snapshot of current system state
    baseline  -- Take a snapshot and mark it as the baseline
    check     -- Compare current state to the baseline, report drift
    diff      -- Compare two specific snapshots by ID
    list      -- List all snapshots
"""

from __future__ import annotations

import json

import click

from . import __version__, db, drift


@click.group()
@click.version_option(__version__, prog_name="driftwatch")
def cli() -> None:
    """Infrastructure drift detector.

    Snapshots Docker containers, crontabs, packages, and systemd services.
    Compares snapshots to detect unexpected configuration drift.
    """


@cli.command()
@click.option("--name", "-n", default=None, help="Name for the snapshot.")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def snapshot(name: str | None, json_output: bool) -> None:
    """Take a snapshot of current system state."""
    snap = drift.take_snapshot(name=name)
    if json_output:
        click.echo(json.dumps(snap, indent=2))
    else:
        click.echo(f"Snapshot saved: id={snap['id']} name={snap['name']}")
        _print_state_summary(snap["data"])


@cli.command()
@click.option("--name", "-n", default=None, help="Name for the baseline.")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def baseline(name: str | None, json_output: bool) -> None:
    """Take a snapshot and mark it as the baseline for drift checks."""
    if name is None:
        name = "baseline"
    snap = drift.take_snapshot(name=name, is_baseline=True)
    if json_output:
        click.echo(json.dumps(snap, indent=2))
    else:
        click.echo(f"Baseline saved: id={snap['id']} name={snap['name']}")
        _print_state_summary(snap["data"])


@cli.command("check")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def check_cmd(json_output: bool) -> None:
    """Compare current state to the baseline. Report any drift."""
    result = drift.check_drift()

    if json_output:
        click.echo(json.dumps(result, indent=2))
        return

    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        raise SystemExit(1)

    click.echo(
        f"Baseline: id={result['baseline_id']} name={result['baseline_name']}"
    )

    if not result["has_drift"]:
        click.secho("No drift detected.", fg="green", bold=True)
        return

    click.secho("DRIFT DETECTED", fg="red", bold=True)
    _print_changes(result["changes"])
    raise SystemExit(2)


@cli.command()
@click.argument("id1", type=int)
@click.argument("id2", type=int)
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def diff(id1: int, id2: int, json_output: bool) -> None:
    """Compare two snapshots by ID."""
    snap1 = db.get_snapshot(id1)
    snap2 = db.get_snapshot(id2)

    if snap1 is None:
        click.echo(f"Snapshot {id1} not found.", err=True)
        raise SystemExit(1)
    if snap2 is None:
        click.echo(f"Snapshot {id2} not found.", err=True)
        raise SystemExit(1)

    changes = drift.compare(snap1["data"], snap2["data"])

    if json_output:
        click.echo(json.dumps(changes, indent=2))
        return

    click.echo(f"Comparing snapshot {id1} ({snap1['name']}) -> {id2} ({snap2['name']})")

    if not changes:
        click.secho("No differences.", fg="green")
        return

    _print_changes(changes)


@cli.command("list")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def list_cmd(json_output: bool) -> None:
    """List all snapshots."""
    snapshots = db.list_snapshots()

    if json_output:
        click.echo(json.dumps(snapshots, indent=2))
        return

    if not snapshots:
        click.echo("No snapshots found.")
        return

    click.echo(f"{'ID':>4}  {'Baseline':>8}  {'Timestamp':<25}  Name")
    click.echo("-" * 70)
    for s in snapshots:
        marker = "*" if s["is_baseline"] else " "
        click.echo(
            f"{s['id']:>4}  {marker:>8}  {s['timestamp'][:25]:<25}  {s['name']}"
        )


def _print_state_summary(data: dict) -> None:
    """Print a brief summary of collected state."""
    for section, items in sorted(data.items()):
        if isinstance(items, dict):
            if "_error" in items:
                click.echo(f"  {section}: error ({items['_error']})")
            else:
                click.echo(f"  {section}: {len(items)} items")
        else:
            click.echo(f"  {section}: {items}")


def _print_changes(changes: dict) -> None:
    """Print structured drift changes."""
    for section, diff_data in sorted(changes.items()):
        click.secho(f"\n[{section}]", fg="yellow", bold=True)

        added = diff_data.get("added", {})
        removed = diff_data.get("removed", {})
        modified = diff_data.get("modified", {})

        for key in sorted(added):
            click.secho(f"  + {key}", fg="green")
            _print_value(added[key], indent=6)

        for key in sorted(removed):
            click.secho(f"  - {key}", fg="red")
            _print_value(removed[key], indent=6)

        for key in sorted(modified):
            click.secho(f"  ~ {key}", fg="cyan")
            mod = modified[key]
            if isinstance(mod, dict) and "old" in mod and "new" in mod:
                click.echo(f"      old: {_fmt(mod['old'])}")
                click.echo(f"      new: {_fmt(mod['new'])}")
            else:
                _print_value(mod, indent=6)


def _print_value(val: object, indent: int = 4) -> None:
    """Print a value with indentation."""
    prefix = " " * indent
    if isinstance(val, dict):
        for k, v in sorted(val.items()) if isinstance(val, dict) else []:
            click.echo(f"{prefix}{k}: {_fmt(v)}")
    elif isinstance(val, list):
        for item in val:
            click.echo(f"{prefix}- {_fmt(item)}")
    else:
        click.echo(f"{prefix}{_fmt(val)}")


def _fmt(val: object) -> str:
    """Format a value for display, truncating long strings."""
    s = str(val)
    if len(s) > 120:
        return s[:117] + "..."
    return s
