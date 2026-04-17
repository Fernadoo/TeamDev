#!/usr/bin/env python3
"""Recalculate task and project statuses from child entities.

Reads state JSON from stdin, recalculates all derived statuses
(task status from issues, project status from tasks), applies
staleness detection, and writes the updated state to stdout.

A report of changes is printed to stderr.

Usage: cat state.json | recalculate-statuses.py [--stale-days N]

Exit codes:
  0 - Success
  1 - Error
"""
import json
import sys
from datetime import datetime, timezone, timedelta


def parse_args():
    stale_days = 7
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--stale-days" and i < len(sys.argv) - 1:
            stale_days = int(sys.argv[i + 1])
    return stale_days


def parse_timestamp(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp to a UTC datetime."""
    if ts is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    # Handle both 'Z' suffix and '+00:00'
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def max_timestamp(*timestamps: str) -> str:
    """Return the most recent timestamp string from a list."""
    parsed = [(t, parse_timestamp(t)) for t in timestamps if t]
    if not parsed:
        return None
    return max(parsed, key=lambda x: x[1])[0]


def is_stale(last_activity: str, stale_days: int) -> bool:
    """Check if a finished item is stale (last activity older than stale_days)."""
    if not last_activity:
        return False
    ts = parse_timestamp(last_activity)
    now = datetime.now(timezone.utc)
    return (now - ts) > timedelta(days=stale_days)


def main():
    stale_days = parse_args()
    state = json.load(sys.stdin)

    newly_stale = []
    status_changes = []

    for project in state.get("projects", []):
        for task in project.get("tasks", []):
            issues = task.get("issues", [])
            if not issues:
                continue

            # Compute task last_activity from children
            issue_timestamps = [i.get("last_activity") for i in issues if i.get("last_activity")]
            if issue_timestamps:
                task["last_activity"] = max_timestamp(*issue_timestamps)

            # Recalculate task status
            old_status = task.get("status")
            statuses = [i.get("status") for i in issues]

            if "ongoing" in statuses:
                task["status"] = "ongoing"
            elif all(s == "finished" for s in statuses):
                task["status"] = "finished"

            # Apply staleness
            if task["status"] == "finished" and is_stale(task.get("last_activity"), stale_days):
                task["status"] = "stale"
                if old_status != "stale":
                    newly_stale.append(f"task:{task['name']}")

            if old_status != task["status"]:
                status_changes.append(f"task:{task['name']} {old_status}->{task['status']}")

        # Recalculate project status from tasks
        tasks = project.get("tasks", [])
        if not tasks:
            continue

        # Compute project last_activity from children
        task_timestamps = [t.get("last_activity") for t in tasks if t.get("last_activity")]
        if task_timestamps:
            project["last_activity"] = max_timestamp(*task_timestamps)

        old_status = project.get("status")
        task_statuses = [t.get("status") for t in tasks]

        if "ongoing" in task_statuses:
            project["status"] = "ongoing"
        elif all(s in ("finished", "stale") for s in task_statuses) and tasks:
            project["status"] = "finished"

        # Apply staleness
        if project["status"] == "finished" and is_stale(project.get("last_activity"), stale_days):
            project["status"] = "stale"
            if old_status != "stale":
                newly_stale.append(f"project:{project['name']}")

        if old_status != project["status"]:
            status_changes.append(f"project:{project['name']} {old_status}->{project['status']}")

    # Output
    print(json.dumps(state, indent=2))

    report = {
        "status_changes": status_changes,
        "newly_stale": newly_stale,
    }
    print(json.dumps(report), file=sys.stderr)


if __name__ == "__main__":
    main()
