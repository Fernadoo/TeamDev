#!/usr/bin/env python3
"""Build a project entry and add it to teamdev-state.json.

Reads project configuration from stdin as JSON and the current state file,
constructs the project entry, appends it, validates, and writes the result.

Input JSON format (stdin):
{
  "project_name": "my-project",
  "repo": "owner/repo",
  "tasks": [
    {
      "name": "implement-auth",
      "tag": "feat",
      "issues": [
        {"number": 120, "title": "Add login", "state": "OPEN", "updatedAt": "..."}
      ]
    }
  ]
}

Usage: cat project-config.json | build-project.py [path/to/teamdev-state.json]

If no path is given, falls back to ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json.
Raises ValueError if CLAUDE_PLUGIN_ROOT is not set and no path is provided.

Exit codes:
  0 - Success
  1 - Validation error
  2 - Write error
"""
import json
import sys
import os
from datetime import datetime, timezone


def map_status(github_state: str) -> str:
    if github_state.lower() in ("open",):
        return "ongoing"
    return "finished"


def max_timestamp(timestamps: list) -> str:
    if not timestamps:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parsed = []
    for t in timestamps:
        if t:
            try:
                parsed.append((t, datetime.fromisoformat(t.replace("Z", "+00:00"))))
            except ValueError:
                pass
    if not parsed:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return max(parsed, key=lambda x: x[1])[0]


def main():
    if len(sys.argv) > 1:
        state_path = sys.argv[1]
    else:
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", None)
        if plugin_root is None:
            raise ValueError("CLAUDE_PLUGIN_ROOT is not set and no state file path was provided")
        state_path = os.path.join(plugin_root, "teamdev-state.json")

    try:
        config = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Read or initialize state
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in state file: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        state = {"projects": []}

    # Check for duplicate project name
    project_name = config.get("project_name", "")
    existing_names = [p["name"] for p in state.get("projects", [])]
    if project_name in existing_names:
        print(f"DUPLICATE_PROJECT:{project_name}", file=sys.stderr)
        sys.exit(1)

    # Build the project entry
    repo = config.get("repo", "")
    tasks_config = config.get("tasks", [])
    built_tasks = []
    all_task_timestamps = []

    for tc in tasks_config:
        built_issues = []
        issue_timestamps = []

        for gh_issue in tc.get("issues", []):
            issue_status = map_status(gh_issue.get("state", "OPEN"))
            updated_at = gh_issue.get("updatedAt", "")
            built_issues.append({
                "number": gh_issue["number"],
                "title": gh_issue.get("title", "Untitled"),
                "status": issue_status,
                "last_activity": updated_at,
            })
            if updated_at:
                issue_timestamps.append(updated_at)

        task_last_activity = max_timestamp(issue_timestamps)
        all_task_timestamps.append(task_last_activity)

        # Determine task status
        issue_statuses = [i["status"] for i in built_issues]
        if "ongoing" in issue_statuses:
            task_status = "ongoing"
        elif all(s == "finished" for s in issue_statuses) and issue_statuses:
            task_status = "finished"
        else:
            task_status = "ongoing"

        built_tasks.append({
            "name": tc.get("name", "unnamed-task"),
            "tag": tc.get("tag", "chore"),
            "status": task_status,
            "last_activity": task_last_activity,
            "issues": built_issues,
        })

    # Determine project status
    task_statuses = [t["status"] for t in built_tasks]
    if "ongoing" in task_statuses:
        project_status = "ongoing"
    elif all(s == "finished" for s in task_statuses) and task_statuses:
        project_status = "finished"
    else:
        project_status = "ongoing"

    project_entry = {
        "name": project_name,
        "repo": repo,
        "status": project_status,
        "last_activity": max_timestamp(all_task_timestamps),
        "tasks": built_tasks,
    }

    # Validate required fields
    errors = []
    if not project_name:
        errors.append("Missing project_name")
    if not repo:
        errors.append("Missing repo")
    for t in built_tasks:
        if not t.get("name"):
            errors.append("Task missing name")
        for iss in t.get("issues", []):
            if "number" not in iss:
                errors.append(f"Issue missing number in task '{t.get('name')}'")

    if errors:
        for e in errors:
            print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Append and write
    state["projects"].append(project_entry)

    try:
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    except OSError as e:
        print(f"Write error: {e}", file=sys.stderr)
        sys.exit(2)

    # Output the created project summary
    summary = {
        "project_name": project_name,
        "repo": repo,
        "status": project_status,
        "task_count": len(built_tasks),
        "issue_count": sum(len(t["issues"]) for t in built_tasks),
        "ongoing_issues": sum(1 for t in built_tasks for i in t["issues"] if i["status"] == "ongoing"),
        "finished_issues": sum(1 for t in built_tasks for i in t["issues"] if i["status"] == "finished"),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
