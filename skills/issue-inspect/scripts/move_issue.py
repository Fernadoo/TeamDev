#!/usr/bin/env python3
"""Move an issue from one task to another within the state.

Usage: move_issue.py <state_file> <issue_number> <src_project> <src_task> <dst_project> <dst_task>

Output: Updated state JSON on stdout.
Exit codes: 0 = success, 1 = argument/parse error, 2 = issue/task not found
"""

import json
import sys
from datetime import datetime, timezone


def main():
    if len(sys.argv) != 7:
        print(
            "Usage: move_issue.py <state_file> <issue_number> <src_project> <src_task> <dst_project> <dst_task>",
            file=sys.stderr,
        )
        sys.exit(1)

    state_path = sys.argv[1]
    issue_number = int(sys.argv[2])
    src_project = sys.argv[3]
    src_task = sys.argv[4]
    dst_project = sys.argv[5]
    dst_task = sys.argv[6]

    try:
        with open(state_path, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Find and remove from source
    issue_obj = None
    for project in state.get("projects", []):
        if project.get("name") != src_project:
            continue
        for task in project.get("tasks", []):
            if task.get("name") != src_task:
                continue
            for i, issue in enumerate(task.get("issues", [])):
                if issue.get("number") == issue_number:
                    issue_obj = task["issues"].pop(i)
                    task["last_activity"] = now
                    break
            break
        break

    if issue_obj is None:
        print(
            f"Issue #{issue_number} not found in {src_project}/{src_task}",
            file=sys.stderr,
        )
        sys.exit(2)

    # Add to destination
    found = False
    for project in state.get("projects", []):
        if project.get("name") != dst_project:
            continue
        for task in project.get("tasks", []):
            if task.get("name") != dst_task:
                continue
            task["issues"].append(issue_obj)
            task["last_activity"] = now
            found = True
            break
        break

    if not found:
        print(
            f"Destination task {dst_project}/{dst_task} not found",
            file=sys.stderr,
        )
        sys.exit(2)

    json.dump(state, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
