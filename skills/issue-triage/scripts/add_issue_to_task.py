#!/usr/bin/env python3
"""Add a validated issue to an existing task in the state file.

Usage: add_issue_to_task.py <state_file> <project_name> <task_name> <issue_json>

Arguments:
  state_file    - Path to teamdev-state.json
  project_name  - Name of the project containing the task
  task_name     - Name of the task to add the issue to
  issue_json    - JSON string of the issue object: {"number": N, "title": "...", "status": "ongoing", "last_activity": "..."}

Output: Updated state JSON on stdout.
Exit codes: 0 = success, 1 = argument/parse error, 2 = project/task not found
"""

import json
import sys
from datetime import datetime, timezone


def normalize_issue(issue: dict) -> dict:
    """Convert GitHub-format issue to internal format if needed."""
    normalized = {"number": issue["number"], "title": issue.get("title", "Untitled")}
    # Map GitHub 'state' -> internal 'status'
    if "status" in issue:
        normalized["status"] = issue["status"]
    elif "state" in issue:
        normalized["status"] = "ongoing" if issue["state"].upper() == "OPEN" else "finished"
    else:
        normalized["status"] = "ongoing"
    # Map GitHub 'updatedAt' -> internal 'last_activity'
    if "last_activity" in issue:
        normalized["last_activity"] = issue["last_activity"]
    elif "updatedAt" in issue:
        normalized["last_activity"] = issue["updatedAt"]
    else:
        normalized["last_activity"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return normalized


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: add_issue_to_task.py <state_file> <project_name> <task_name> <issue_json>",
            file=sys.stderr,
        )
        sys.exit(1)

    state_path = sys.argv[1]
    project_name = sys.argv[2]
    task_name = sys.argv[3]

    try:
        issue = json.loads(sys.argv[4])
    except json.JSONDecodeError as e:
        print(f"Error parsing issue JSON: {e}", file=sys.stderr)
        sys.exit(1)

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
            task["issues"].append(normalize_issue(issue))
            task["last_activity"] = now
            found = True
            break
        if found:
            # Update project last_activity to max of its tasks
            max_activity = max(
                (t.get("last_activity", "") for t in project.get("tasks", [])),
                default=now,
            )
            project["last_activity"] = max_activity
            break

    if not found:
        print(
            f"Task '{task_name}' not found in project '{project_name}'",
            file=sys.stderr,
        )
        sys.exit(2)

    json.dump(state, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
