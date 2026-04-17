#!/usr/bin/env python3
"""Format fetched GitHub issues as a numbered list for user presentation.

Reads a JSON array of issues from stdin (as returned by gh issue list --json).
Outputs a numbered, formatted list to stdout.

Usage: cat issues.json | format-issues.py

Exit codes:
  0 - Success (issues found)
  1 - No issues found or error
"""
import json
import sys


def main():
    try:
        issues = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    if not issues:
        print("NO_ISSUES")
        sys.exit(1)

    print(f"Found {len(issues)} issues:\n")
    for i, issue in enumerate(issues, 1):
        number = issue.get("number", "?")
        state = issue.get("state", "UNKNOWN").upper()
        title = issue.get("title", "Untitled")
        print(f"  {i:>3}. #{number} [{state:<6s}] {title}")

    # Also output a machine-readable mapping (index -> number) to stderr
    mapping = {str(i): issue["number"] for i, issue in enumerate(issues, 1)}
    print(json.dumps(mapping), file=sys.stderr)


if __name__ == "__main__":
    main()
