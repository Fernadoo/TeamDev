#!/usr/bin/env python3
"""Validate and write state JSON to the state file.

Reads JSON from stdin, validates the structure, and writes to the
specified output file.

Usage: cat state.json | write-state.py [path/to/teamdev-state.json]

If no path is given, falls back to ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json.
Raises ValueError if CLAUDE_PLUGIN_ROOT is not set and no path is provided.

Exit codes:
  0 - Success
  1 - Validation error (details on stderr)
  2 - Write error (details on stderr)
"""
import json
import sys
import os


REQUIRED_PROJECT_FIELDS = {"name", "repo", "status", "last_activity", "tasks"}
REQUIRED_TASK_FIELDS = {"name", "tag", "status", "last_activity", "issues"}
REQUIRED_ISSUE_FIELDS = {"number", "title", "status", "last_activity"}


def validate(state: dict) -> list:
    """Validate state structure. Returns list of error strings."""
    errors = []

    if "projects" not in state:
        errors.append("Missing top-level 'projects' key")
        return errors

    for pi, project in enumerate(state["projects"]):
        missing = REQUIRED_PROJECT_FIELDS - set(project.keys())
        if missing:
            errors.append(f"Project [{pi}] missing fields: {missing}")
            continue

        for ti, task in enumerate(project.get("tasks", [])):
            missing = REQUIRED_TASK_FIELDS - set(task.keys())
            if missing:
                errors.append(f"Project '{project['name']}' task [{ti}] missing fields: {missing}")
                continue

            for ii, issue in enumerate(task.get("issues", [])):
                missing = REQUIRED_ISSUE_FIELDS - set(issue.keys())
                if missing:
                    errors.append(
                        f"Project '{project['name']}' task '{task['name']}' issue [{ii}] missing fields: {missing}"
                    )

    return errors


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", None)
        if plugin_root is None:
            raise ValueError("CLAUDE_PLUGIN_ROOT is not set and no state file path was provided")
        path = os.path.join(plugin_root, "teamdev-state.json")

    try:
        state = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate(state)
    if errors:
        for err in errors:
            print(f"Validation error: {err}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    except OSError as e:
        print(f"Write error: {e}", file=sys.stderr)
        sys.exit(2)

    print(f"State written to {path}")


if __name__ == "__main__":
    main()
