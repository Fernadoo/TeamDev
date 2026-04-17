#!/usr/bin/env python3
"""Mark an issue as finished and recalculate task/project statuses.

Usage:
    update-state.py <state_file> <issue_number>

Updates the state file in place:
  - Sets the issue's status to "finished" and updates last_activity
  - If all issues in the parent task are finished, sets task to "finished"
  - If all tasks in the parent project are finished, sets project to "finished"
  - Updates last_activity timestamps at each level

Exit codes:
    0 - success
    1 - issue not found
    2 - error (file missing, invalid JSON, etc.)

Outputs a JSON summary of what changed to stdout.
"""
import json
import sys
from datetime import datetime, timezone


def main():
    if len(sys.argv) != 3:
        print("Usage: update-state.py <state_file> <issue_number>", file=sys.stderr)
        sys.exit(2)

    state_file = sys.argv[1]
    try:
        issue_number = int(sys.argv[2])
    except ValueError:
        print(f"Error: issue_number must be an integer, got '{sys.argv[2]}'", file=sys.stderr)
        sys.exit(2)

    try:
        with open(state_file, "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        print(f"Error: state file not found: {state_file}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in state file: {e}", file=sys.stderr)
        sys.exit(2)

    now = datetime.now(timezone.utc).isoformat()
    found = False
    result = {"issue_number": issue_number, "changes": []}

    for project in state.get("projects", []):
        for task in project.get("tasks", []):
            for issue in task.get("issues", []):
                if issue.get("number") == issue_number:
                    found = True

                    # Mark issue as finished
                    issue["status"] = "finished"
                    issue["last_activity"] = now
                    result["changes"].append(f"Issue #{issue_number} marked as finished")

                    # Recalculate task status
                    all_issues_finished = all(
                        i.get("status") == "finished" for i in task["issues"]
                    )
                    old_task_status = task.get("status", "ongoing")
                    if all_issues_finished:
                        task["status"] = "finished"
                    else:
                        task["status"] = "ongoing"
                    task["last_activity"] = now

                    if old_task_status != task["status"]:
                        result["changes"].append(
                            f"Task '{task.get('name', '')}' status: {old_task_status} -> {task['status']}"
                        )

                    result["task_status"] = task["status"]
                    result["task_name"] = task.get("name", "")

                    # Recalculate project status
                    all_tasks_finished = all(
                        t.get("status") == "finished" for t in project["tasks"]
                    )
                    old_project_status = project.get("status", "ongoing")
                    if all_tasks_finished:
                        project["status"] = "finished"
                    else:
                        project["status"] = "ongoing"
                    project["last_activity"] = now

                    if old_project_status != project["status"]:
                        result["changes"].append(
                            f"Project '{project.get('name', '')}' status: {old_project_status} -> {project['status']}"
                        )

                    result["project_status"] = project["status"]
                    result["project_name"] = project.get("name", "")
                    break
            if found:
                break
        if found:
            break

    if not found:
        print(f"Error: issue #{issue_number} not found in state file", file=sys.stderr)
        sys.exit(1)

    # Write updated state
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
