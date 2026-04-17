#!/usr/bin/env python3
"""Recalculate task statuses, last_activity, and staleness from child issues.

Usage:
    recalculate_tasks.py <state_file> [--current-date YYYY-MM-DDTHH:MM:SSZ]

Reads the state file, recalculates all task statuses from their child issues,
updates last_activity, detects staleness (finished > 7 days), and propagates
changes upward to project statuses. Outputs a JSON object to stdout with:
  - "state": the updated state
  - "changes": list of changes made (task status transitions, staleness, etc.)
  - "stale_tasks": list of stale task descriptors for user prompting
  - "warnings": list of warnings (missing issues, null timestamps, etc.)

Does NOT remove stale tasks -- that requires user confirmation and is handled
by the orchestrator.

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
        # Handle Z suffix and +00:00
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: recalculate_tasks.py <state_file> [--current-date ISO]", file=sys.stderr)
        sys.exit(1)

    state_file = sys.argv[1]
    now = datetime.now(timezone.utc)

    # Parse optional --current-date
    for i, arg in enumerate(sys.argv):
        if arg == "--current-date" and i + 1 < len(sys.argv):
            parsed = parse_iso(sys.argv[i + 1])
            if parsed:
                now = parsed
            break

    # Read state file
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
    stale_tasks = []
    staleness_threshold = now - timedelta(days=STALENESS_DAYS)

    # Step 2-5: Process all tasks
    for project in state["projects"]:
        project_name = project.get("name", "<unnamed>")
        tasks = project.get("tasks", [])

        for task in tasks:
            task_name = task.get("name", "<unnamed>")
            issues = task.get("issues", [])
            old_status = task.get("status")

            # Step 3: Recalculate task status from child issues
            if not issues:
                warnings.append(f"Task '{task_name}' in project '{project_name}' has no child issues; status unchanged.")
                continue

            has_ongoing = any(iss.get("status") == "ongoing" for iss in issues)
            all_finished = all(iss.get("status") == "finished" for iss in issues)

            if has_ongoing:
                task["status"] = "ongoing"
            elif all_finished:
                task["status"] = "finished"

            # Step 4: Update task last_activity
            max_activity = None
            for iss in issues:
                ts = parse_iso(iss.get("last_activity"))
                if ts and (max_activity is None or ts > max_activity):
                    max_activity = ts
            if max_activity:
                task["last_activity"] = max_activity.isoformat().replace("+00:00", "Z")

            # Step 5: Check staleness
            if task["status"] == "finished":
                task_activity = parse_iso(task.get("last_activity"))
                if task_activity is None:
                    warnings.append(f"Task '{task_name}' in project '{project_name}' has null last_activity; skipping staleness check.")
                elif task_activity < staleness_threshold:
                    task["status"] = "stale"
                    stale_tasks.append({
                        "project_name": project_name,
                        "task_name": task_name,
                        "last_activity": task.get("last_activity"),
                    })

            # Record status change
            if task["status"] != old_status:
                changes.append(f"Task '{task_name}' in project '{project_name}': {old_status} -> {task['status']}")

    # Step 7: Propagate to parent projects
    for project in state["projects"]:
        project_name = project.get("name", "<unnamed>")
        tasks = project.get("tasks", [])
        old_status = project.get("status")

        if not tasks:
            # No tasks remaining -> finished
            if old_status != "finished":
                project["status"] = "finished"
        else:
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

        # Project staleness check
        if project.get("status") == "finished":
            proj_activity = parse_iso(project.get("last_activity"))
            if proj_activity and proj_activity < staleness_threshold:
                project["status"] = "stale"

        if project.get("status") != old_status:
            changes.append(f"Project '{project_name}': {old_status} -> {project.get('status')}")

    result = {
        "state": state,
        "changes": changes,
        "stale_tasks": stale_tasks,
        "warnings": warnings,
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
