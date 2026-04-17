#!/usr/bin/env python3
"""Remove a project from the state file by name.

Usage:
    remove_project.py <state_file> <project_name>

Removes the specified project from the projects array. Outputs the
updated state JSON to stdout.

Exit codes:
  0  Success (project removed)
  1  File not found or unreadable
  2  Invalid JSON or missing projects array
  3  Project not found
"""

import json
import sys


def main():
    if len(sys.argv) != 3:
        print("Usage: remove_project.py <state_file> <project_name>", file=sys.stderr)
        sys.exit(1)

    state_file = sys.argv[1]
    project_name = sys.argv[2]

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

    original_len = len(state["projects"])
    state["projects"] = [
        p for p in state["projects"] if p.get("name") != project_name
    ]

    if len(state["projects"]) == original_len:
        print(f"Error: Project '{project_name}' not found", file=sys.stderr)
        sys.exit(3)

    json.dump(state, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
