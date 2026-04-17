#!/usr/bin/env python3
"""Update last_activity timestamp on a selected issue and propagate upward.

Usage: update_pick_timestamps.py <state_file> <project_name> <task_name> <issue_number>

Output: Updated state JSON on stdout.
Exit codes: 0 = success, 1 = argument/parse error, 2 = issue not found
"""

import json
import sys
from datetime import datetime, timezone


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: update_pick_timestamps.py <state_file> <project_name> <task_name> <issue_number>",
            file=sys.stderr,
        )
        sys.exit(1)

    state_path = sys.argv[1]
    project_name = sys.argv[2]
    task_name = sys.argv[3]
    issue_number = int(sys.argv[4])

    try:
        with open(state_path, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    found = False
    for project in state.get("projects", []):
        if project.get("name") != project_name:
            continue
        for task in project.get("tasks", []):
            if task.get("name") != task_name:
                continue
            for issue in task.get("issues", []):
                if issue.get("number") == issue_number:
                    issue["last_activity"] = now
                    found = True
                    break
            if found:
                # Propagate to task
                max_ts = max(
                    (i.get("last_activity", "") for i in task.get("issues", [])),
                    default=now,
                )
                task["last_activity"] = max_ts
                break
        if found:
            # Propagate to project
            max_ts = max(
                (t.get("last_activity", "") for t in project.get("tasks", [])),
                default=now,
            )
            project["last_activity"] = max_ts
            break

    if not found:
        print(
            f"Issue #{issue_number} not found in {project_name}/{task_name}",
            file=sys.stderr,
        )
        sys.exit(2)

    json.dump(state, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
