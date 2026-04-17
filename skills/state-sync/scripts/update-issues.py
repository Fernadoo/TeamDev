#!/usr/bin/env python3
"""Update issue statuses in the state by comparing with GitHub data.

Usage: update-issues.py <state.json> <github-issues.json> <project-name>

Reads the state file and a JSON file containing GitHub issue data for one project.
Prints the updated state JSON to stdout plus a report summary to stderr.

Exit codes:
  0 - Success
  1 - Error
"""
import json
import sys


def map_status(github_state: str) -> str:
    """Map GitHub issue state to local status."""
    if github_state.lower() in ("open",):
        return "ongoing"
    elif github_state.lower() in ("closed",):
        return "finished"
    return "ongoing"


def main():
    if len(sys.argv) < 4:
        print("Usage: update-issues.py <state.json> <github-issues.json> <project-name>", file=sys.stderr)
        sys.exit(1)

    state_path = sys.argv[1]
    gh_path = sys.argv[2]
    project_name = sys.argv[3]

    with open(state_path, "r") as f:
        state = json.load(f)

    with open(gh_path, "r") as f:
        gh_issues = json.load(f)

    # Build lookup by issue number
    gh_lookup = {issue["number"]: issue for issue in gh_issues}

    updated_count = 0
    status_changed = 0
    not_found = []

    for project in state["projects"]:
        if project["name"] != project_name:
            continue

        for task in project.get("tasks", []):
            for issue in task.get("issues", []):
                num = issue["number"]
                if num in gh_lookup:
                    gh_issue = gh_lookup[num]
                    new_status = map_status(gh_issue["state"])
                    if issue.get("status") != new_status:
                        status_changed += 1
                    issue["status"] = new_status
                    issue["title"] = gh_issue["title"]
                    issue["last_activity"] = gh_issue["updatedAt"]
                    updated_count += 1
                else:
                    not_found.append(num)

    # Print updated state to stdout
    print(json.dumps(state, indent=2))

    # Print report to stderr
    report = {
        "project": project_name,
        "issues_updated": updated_count,
        "status_changes": status_changed,
        "not_found_on_github": not_found,
    }
    print(json.dumps(report), file=sys.stderr)


if __name__ == "__main__":
    main()
