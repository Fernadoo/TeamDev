#!/usr/bin/env python3
"""Build PR body from task data, commit log, and optional template.

Usage:
    build-pr-body.py [--template <path>] <state_file> <issue_number>

Reads commit log from stdin (pipe `git log --oneline origin/main..HEAD` into it).

If --template is provided, reads the template and fills in sections.
Otherwise uses the default body structure.

Outputs the PR body markdown to stdout.
"""
import argparse
import json
import sys


def read_state(state_file, issue_number):
    """Find the task containing the given issue number."""
    with open(state_file, "r") as f:
        state = json.load(f)

    for project in state.get("projects", []):
        for task in project.get("tasks", []):
            for issue in task.get("issues", []):
                if issue.get("number") == issue_number:
                    return {
                        "project_name": project.get("name", ""),
                        "task_name": task.get("name", ""),
                        "task_tag": task.get("tag", ""),
                        "issues": [
                            {"number": i["number"], "title": i.get("title", "")}
                            for i in task["issues"]
                        ],
                    }
    return None


def build_closes_lines(issues):
    """Build 'Closes #N - title' lines."""
    lines = []
    for issue in issues:
        title = issue.get("title", "")
        if title:
            lines.append(f"Closes #{issue['number']} — {title}")
        else:
            lines.append(f"Closes #{issue['number']}")
    return "\n".join(lines)


def build_default_body(task_data, commit_log):
    """Build the default PR body structure."""
    closes = build_closes_lines(task_data["issues"])

    body = f"""## Summary

<!-- Summary of changes based on commit history -->

## Changes

<!-- Key changes derived from commit log -->

## Resolved Issues

{closes}

## Commit Log

```
{commit_log.strip()}
```
"""
    return body


def fill_template(template_content, task_data, commit_log):
    """Attempt to fill in a PR template with task data.

    Returns the template with closes lines and commit log appended
    at appropriate locations.
    """
    closes = build_closes_lines(task_data["issues"])
    lines = template_content.split("\n")
    output = []
    inserted_closes = False
    inserted_commits = False

    for line in lines:
        output.append(line)
        lower = line.lower().strip()

        # Insert closes after related issues section header
        if not inserted_closes and any(
            kw in lower
            for kw in ["related issue", "closes", "resolves", "fixes", "issue"]
        ):
            if lower.startswith("#"):
                output.append("")
                output.append(closes)
                inserted_closes = True

    # If we didn't find a section for closes, append at the end
    if not inserted_closes:
        output.append("")
        output.append("## Related Issues")
        output.append("")
        output.append(closes)

    if not inserted_commits and commit_log.strip():
        output.append("")
        output.append("## Commit Log")
        output.append("")
        output.append("```")
        output.append(commit_log.strip())
        output.append("```")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Build PR body")
    parser.add_argument("--template", help="Path to PR template file")
    parser.add_argument("state_file", help="Path to teamdev-state.json")
    parser.add_argument("issue_number", type=int, help="Issue number to find task")
    args = parser.parse_args()

    # Read commit log from stdin
    if not sys.stdin.isatty():
        commit_log = sys.stdin.read()
    else:
        commit_log = ""

    task_data = read_state(args.state_file, args.issue_number)
    if task_data is None:
        print(f"Error: issue #{args.issue_number} not found in state file", file=sys.stderr)
        sys.exit(1)

    if args.template:
        try:
            with open(args.template, "r") as f:
                template_content = f.read()
            body = fill_template(template_content, task_data, commit_log)
        except FileNotFoundError:
            print(f"Error: template not found: {args.template}", file=sys.stderr)
            sys.exit(1)
    else:
        body = build_default_body(task_data, commit_log)

    print(body)


if __name__ == "__main__":
    main()
