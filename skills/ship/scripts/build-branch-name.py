#!/usr/bin/env python3
"""Build a task branch name from tag, task_name, and issue numbers.

Usage:
    build-branch-name.py <tag> <task_name> <issue_numbers...>

Example:
    build-branch-name.py feat add-auth 120 231
    # Output: feat/add-auth-120-231

Outputs the branch name to stdout.
"""
import sys


def main():
    if len(sys.argv) < 4:
        print("Usage: build-branch-name.py <tag> <task_name> <issue_numbers...>", file=sys.stderr)
        sys.exit(1)

    tag = sys.argv[1]
    task_name = sys.argv[2]
    issue_numbers = sys.argv[3:]

    branch_name = f"{tag}/{task_name}-{'-'.join(issue_numbers)}"
    print(branch_name)


if __name__ == "__main__":
    main()
