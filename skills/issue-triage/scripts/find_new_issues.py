#!/usr/bin/env python3
"""Compare fetched issues against tracked issues in state to find new ones.

Usage: find_new_issues.py <state_file>
Reads fetched issues as JSON from stdin. Each object must have:
  - "number": int
  - "title": str
  - "project_name": str
  - "repo": str
  plus any other fields from gh output.

The state file is read to extract all currently tracked issue numbers per repo.

Output: JSON array of new (untracked) issues on stdout.
Exit codes: 0 = success (may output empty array), 1 = argument/parse error
"""

import json
import sys


def load_tracked_issues(state_path):
    """Return a set of (repo, issue_number) tuples from the state file."""
    with open(state_path, "r") as f:
        state = json.load(f)

    tracked = set()
    for project in state.get("projects", []):
        repo = project.get("repo", "")
        for task in project.get("tasks", []):
            for issue in task.get("issues", []):
                tracked.add((repo, issue.get("number")))
    return tracked


def main():
    if len(sys.argv) != 2:
        print("Usage: find_new_issues.py <state_file>", file=sys.stderr)
        sys.exit(1)

    state_path = sys.argv[1]

    try:
        fetched = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing stdin JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        tracked = load_tracked_issues(state_path)
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        sys.exit(1)

    new_issues = []
    for issue in fetched:
        repo = issue.get("repo", "")
        number = issue.get("number")
        if (repo, number) not in tracked:
            new_issues.append(issue)

    json.dump(new_issues, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
