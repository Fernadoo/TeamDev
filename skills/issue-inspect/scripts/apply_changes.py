#!/usr/bin/env python3
"""Apply detected changes to the state file and propagate timestamps.

Usage: apply_changes.py <state_file>
Reads a JSON array of change records from stdin. Each record:
{
  "project_name": "...",
  "task_name": "...",
  "issue_number": N,
  "new_status": "ongoing" | "finished",
  "new_last_activity": "ISO8601 timestamp"
}

Output: Updated state JSON on stdout.
Also outputs a staleness report on stderr as JSON:
{
  "all_finished_tasks": [{"project": "...", "task": "...", "issue_count": N}],
  "stale_tasks": [{"project": "...", "task": "...", "last_activity": "..."}]
}

Exit codes: 0 = success, 1 = error
"""

import json
import sys
from datetime import datetime, timezone, timedelta


STALE_DAYS = 14


def main():
    if len(sys.argv) != 2:
        print("Usage: apply_changes.py <state_file>", file=sys.stderr)
        sys.exit(1)

    state_path = sys.argv[1]

    try:
        changes = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing stdin JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(state_path, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        sys.exit(1)

    # Build a lookup for changes: (project_name, task_name, issue_number) -> change
    change_map = {}
    for c in changes:
        key = (c["project_name"], c["task_name"], c["issue_number"])
        change_map[key] = c

    # Track which tasks/projects were modified
    modified_tasks = set()  # (project_name, task_name)

    # Apply issue-level changes
    for project in state.get("projects", []):
        pname = project.get("name", "")
        for task in project.get("tasks", []):
            tname = task.get("name", "")
            for issue in task.get("issues", []):
                key = (pname, tname, issue.get("number"))
                if key in change_map:
                    c = change_map[key]
                    if c.get("new_status"):
                        issue["status"] = c["new_status"]
                    if c.get("new_last_activity"):
                        issue["last_activity"] = c["new_last_activity"]
                    modified_tasks.add((pname, tname))

    # Propagate timestamps: task -> project
    modified_projects = set()
    for project in state.get("projects", []):
        pname = project.get("name", "")
        for task in project.get("tasks", []):
            tname = task.get("name", "")
            if (pname, tname) in modified_tasks:
                # Set task last_activity to max of its issues
                max_ts = max(
                    (i.get("last_activity", "") for i in task.get("issues", [])),
                    default="",
                )
                if max_ts:
                    task["last_activity"] = max_ts
                modified_projects.add(pname)

        if pname in modified_projects:
            max_ts = max(
                (t.get("last_activity", "") for t in project.get("tasks", [])),
                default="",
            )
            if max_ts:
                project["last_activity"] = max_ts

    # Detect staleness
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=STALE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    staleness = {"all_finished_tasks": [], "stale_tasks": []}

    for project in state.get("projects", []):
        if project.get("status") != "ongoing":
            continue
        pname = project.get("name", "")
        for task in project.get("tasks", []):
            if task.get("status") != "ongoing":
                continue
            tname = task.get("name", "")
            issues = task.get("issues", [])

            # All issues finished?
            if issues and all(i.get("status") == "finished" for i in issues):
                staleness["all_finished_tasks"].append(
                    {"project": pname, "task": tname, "issue_count": len(issues)}
                )

            # Stale (no recent activity and not modified this run)?
            task_la = task.get("last_activity", "")
            if task_la < cutoff and (pname, tname) not in modified_tasks:
                staleness["stale_tasks"].append(
                    {"project": pname, "task": tname, "last_activity": task_la}
                )

    # Output state to stdout, staleness report to stderr
    json.dump(state, sys.stdout, indent=2)
    print()
    json.dump(staleness, sys.stderr, indent=2)
    print(file=sys.stderr)


if __name__ == "__main__":
    main()
