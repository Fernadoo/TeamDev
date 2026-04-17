#!/usr/bin/env python3
"""Check whether all issues in a task are finished.

Usage:
    check-task-completion.py <state_file> <issue_number>

Reads the state file, finds the task containing the given issue number,
and reports whether all issues in that task are finished (treating the
given issue as if it were already finished).

Exit codes:
    0 - task is complete (all issues finished)
    1 - task is NOT complete (some issues still ongoing)
    2 - error (state file missing, issue not found, etc.)

Outputs JSON to stdout:
    {
      "task_complete": true/false,
      "project_name": "...",
      "task_name": "...",
      "task_tag": "...",
      "issue_numbers": [120, 231],
      "finished_count": 2,
      "total_count": 2
    }
"""
import json
import sys


def main():
    if len(sys.argv) != 3:
        print("Usage: check-task-completion.py <state_file> <issue_number>", file=sys.stderr)
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

    # Find the task containing this issue
    for project in state.get("projects", []):
        for task in project.get("tasks", []):
            for issue in task.get("issues", []):
                if issue.get("number") == issue_number:
                    # Count finished issues, treating current issue as finished
                    issue_numbers = [i["number"] for i in task["issues"]]
                    finished = sum(
                        1 for i in task["issues"]
                        if i.get("status") == "finished" or i.get("number") == issue_number
                    )
                    total = len(task["issues"])
                    task_complete = finished == total

                    result = {
                        "task_complete": task_complete,
                        "project_name": project.get("name", ""),
                        "task_name": task.get("name", ""),
                        "task_tag": task.get("tag", ""),
                        "issue_numbers": issue_numbers,
                        "finished_count": finished,
                        "total_count": total,
                    }
                    print(json.dumps(result, indent=2))
                    sys.exit(0 if task_complete else 1)

    print(f"Error: issue #{issue_number} not found in any task", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
