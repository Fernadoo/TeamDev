#!/usr/bin/env python3
"""Create a new task with an initial issue in a project.

Usage: create_task_entry.py <state_file> <project_name> <task_name> <tag> <issue_json>

Arguments:
  state_file    - Path to teamdev-state.json
  project_name  - Name of the project to add the task to
  task_name     - Name for the new task (kebab-case preferred)
  tag           - Task tag (feat, bugfix, refactor, chore, docs, test, perf, or custom)
  issue_json    - JSON string of the issue object: {"number": N, "title": "...", "status": "ongoing", "last_activity": "..."}

Output: Updated state JSON on stdout.
Exit codes: 0 = success, 1 = argument/parse error, 2 = project not found
"""

import json
import sys
from datetime import datetime, timezone


def normalize_issue(issue: dict) -> dict:
    """Convert GitHub-format issue to internal format if needed."""
    normalized = {"number": issue["number"], "title": issue.get("title", "Untitled")}
    if "status" in issue:
        normalized["status"] = issue["status"]
    elif "state" in issue:
        normalized["status"] = "ongoing" if issue["state"].upper() == "OPEN" else "finished"
    else:
        normalized["status"] = "ongoing"
    if "last_activity" in issue:
        normalized["last_activity"] = issue["last_activity"]
    elif "updatedAt" in issue:
        normalized["last_activity"] = issue["updatedAt"]
    else:
        normalized["last_activity"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return normalized


def main():
    if len(sys.argv) != 6:
        print(
            "Usage: create_task_entry.py <state_file> <project_name> <task_name> <tag> <issue_json>",
            file=sys.stderr,
        )
        sys.exit(1)

    state_path = sys.argv[1]
    project_name = sys.argv[2]
    task_name = sys.argv[3]
    tag = sys.argv[4]

    try:
        issue = json.loads(sys.argv[5])
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

    new_task = {
        "name": task_name,
        "tag": tag,
        "status": "ongoing",
        "last_activity": now,
        "issues": [normalize_issue(issue)],
    }

    found = False
    for project in state.get("projects", []):
        if project.get("name") != project_name:
            continue
        project.setdefault("tasks", []).append(new_task)
        # Update project last_activity
        max_activity = max(
            (t.get("last_activity", "") for t in project.get("tasks", [])),
            default=now,
        )
        project["last_activity"] = max_activity
        found = True
        break

    if not found:
        print(f"Project '{project_name}' not found in state", file=sys.stderr)
        sys.exit(2)

    json.dump(state, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
