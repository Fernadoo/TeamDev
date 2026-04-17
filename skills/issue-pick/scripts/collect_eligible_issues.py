#!/usr/bin/env python3
"""Collect eligible issues from state (ongoing project -> ongoing task -> ongoing issue).

Usage: collect_eligible_issues.py <state_file>

Output: JSON array of issue objects with hierarchical context:
  - number, title, status, last_activity (from issue)
  - repo, project_name, task_name, task_tag (from parents)

Exit codes: 0 = success, 1 = argument/parse error
"""

import json
import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: collect_eligible_issues.py <state_file>", file=sys.stderr)
        sys.exit(1)

    state_path = sys.argv[1]

    try:
        with open(state_path, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        sys.exit(1)

    eligible = []
    for project in state.get("projects", []):
        if project.get("status") != "ongoing":
            continue
        repo = project.get("repo", "")
        project_name = project.get("name", "")
        for task in project.get("tasks", []):
            if task.get("status") != "ongoing":
                continue
            task_name = task.get("name", "")
            task_tag = task.get("tag", "")
            for issue in task.get("issues", []):
                if issue.get("status") != "ongoing":
                    continue
                eligible.append(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title", ""),
                        "status": issue.get("status"),
                        "last_activity": issue.get("last_activity", ""),
                        "repo": repo,
                        "project_name": project_name,
                        "task_name": task_name,
                        "task_tag": task_tag,
                    }
                )

    json.dump(eligible, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
