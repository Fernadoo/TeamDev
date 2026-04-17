#!/usr/bin/env python3
"""Remove a task from the state file by project name and task name.

Usage:
    remove_task.py <state_file> <project_name> <task_name>

Removes the specified task from the project's tasks array. Outputs the
updated state JSON to stdout.

Exit codes:
  0  Success (task removed)
  1  File not found or unreadable
  2  Invalid JSON or missing projects array
  3  Project or task not found
"""

import json
import sys


def main():
    if len(sys.argv) != 4:
        print("Usage: remove_task.py <state_file> <project_name> <task_name>", file=sys.stderr)
        sys.exit(1)

    state_file = sys.argv[1]
    project_name = sys.argv[2]
    task_name = sys.argv[3]

    try:
        with open(state_file, "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        print(f"Error: State file not found: {state_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    if "projects" not in state or not isinstance(state["projects"], list):
        print("Error: Missing 'projects' array", file=sys.stderr)
        sys.exit(2)

    found_project = False
    found_task = False
    for project in state["projects"]:
        if project.get("name") == project_name:
            found_project = True
            original_len = len(project.get("tasks", []))
            project["tasks"] = [
                t for t in project.get("tasks", []) if t.get("name") != task_name
            ]
            if len(project["tasks"]) < original_len:
                found_task = True
            break

    if not found_project:
        print(f"Error: Project '{project_name}' not found", file=sys.stderr)
        sys.exit(3)
    if not found_task:
        print(f"Error: Task '{task_name}' not found in project '{project_name}'", file=sys.stderr)
        sys.exit(3)

    json.dump(state, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
