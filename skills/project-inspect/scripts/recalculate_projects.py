#!/usr/bin/env python3
"""Recalculate project statuses, last_activity, and staleness from child tasks.

Usage:
    recalculate_projects.py <state_file> [--current-date YYYY-MM-DDTHH:MM:SSZ]

Reads the state file, recalculates all project statuses from their child tasks,
updates last_activity, and detects staleness (finished > 7 days). Outputs a
JSON object to stdout with:
  - "state": the updated state
  - "changes": list of status transitions
  - "stale_projects": list of stale project descriptors for user prompting
  - "warnings": list of warnings

Does NOT remove stale projects -- that requires user confirmation.

Exit codes:
  0  Success
  1  File not found or unreadable
  2  Invalid JSON or missing projects array
"""

import json
import sys
from datetime import datetime, timedelta, timezone


STALENESS_DAYS = 7


def parse_iso(ts):
    """Parse an ISO 8601 timestamp string to a datetime object."""
    if not ts:
        return None
    try:
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: recalculate_projects.py <state_file> [--current-date ISO]", file=sys.stderr)
        sys.exit(1)

    state_file = sys.argv[1]
    now = datetime.now(timezone.utc)

    for i, arg in enumerate(sys.argv):
        if arg == "--current-date" and i + 1 < len(sys.argv):
            parsed = parse_iso(sys.argv[i + 1])
            if parsed:
                now = parsed
            break

    try:
        with open(state_file, "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        print(f"Error: State file not found: {state_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in state file: {e}", file=sys.stderr)
        sys.exit(2)

    if "projects" not in state or not isinstance(state["projects"], list):
        print("Error: State file missing 'projects' array", file=sys.stderr)
        sys.exit(2)

    changes = []
    warnings = []
    stale_projects = []
    staleness_threshold = now - timedelta(days=STALENESS_DAYS)

    for project in state["projects"]:
        project_name = project.get("name", "<unnamed>")
        tasks = project.get("tasks", [])
        old_status = project.get("status")

        # Recalculate project status from child tasks
        if not tasks:
            warnings.append(f"Project '{project_name}' has no child tasks; status unchanged.")
            continue

        has_ongoing = any(t.get("status") == "ongoing" for t in tasks)
        all_done = all(t.get("status") in ("finished", "stale") for t in tasks)

        if has_ongoing:
            project["status"] = "ongoing"
        elif all_done:
            project["status"] = "finished"

        # Update project last_activity
        max_activity = None
        for t in tasks:
            ts = parse_iso(t.get("last_activity"))
            if ts and (max_activity is None or ts > max_activity):
                max_activity = ts
        if max_activity:
            project["last_activity"] = max_activity.isoformat().replace("+00:00", "Z")

        # Check staleness
        if project["status"] == "finished":
            proj_activity = parse_iso(project.get("last_activity"))
            if proj_activity is None:
                warnings.append(f"Project '{project_name}' has null last_activity; skipping staleness check.")
            elif proj_activity < staleness_threshold:
                project["status"] = "stale"
                stale_projects.append({
                    "project_name": project_name,
                    "repo": project.get("repo", "<unknown>"),
                    "last_activity": project.get("last_activity"),
                })

        if project.get("status") != old_status:
            changes.append({
                "project_name": project_name,
                "old_status": old_status,
                "new_status": project.get("status"),
            })

    # Compute summary stats
    status_counts = {"ongoing": 0, "finished": 0, "stale": 0}
    for project in state["projects"]:
        s = project.get("status", "ongoing")
        if s in status_counts:
            status_counts[s] += 1

    result = {
        "state": state,
        "changes": changes,
        "stale_projects": stale_projects,
        "warnings": warnings,
        "status_counts": status_counts,
        "total_inspected": len(state["projects"]),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
