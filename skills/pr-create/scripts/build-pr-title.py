#!/usr/bin/env python3
"""Build PR title from task metadata.

Usage:
    build-pr-title.py <tag> <task_name> <issue_numbers...>

Example:
    build-pr-title.py feat add-auth 120 231
    # Output: feat: add auth (#120, #231)

Outputs the PR title to stdout.
"""
import sys


def main():
    if len(sys.argv) < 4:
        print("Usage: build-pr-title.py <tag> <task_name> <issue_numbers...>", file=sys.stderr)
        sys.exit(1)

    tag = sys.argv[1]
    task_name = sys.argv[2].replace("-", " ")
    issue_numbers = sys.argv[3:]

    issue_list = ", ".join(f"#{n}" for n in issue_numbers)
    title = f"{tag}: {task_name} (#{issue_list})" if len(issue_numbers) == 1 else f"{tag}: {task_name} ({issue_list})"

    # For single issue, simplify: "feat: add auth (#120)"
    if len(issue_numbers) == 1:
        title = f"{tag}: {task_name} (#{issue_numbers[0]})"

    # Truncate to 72 chars if needed
    if len(title) > 72:
        max_name_len = 72 - len(f"{tag}:  ({issue_list})") - 3
        if max_name_len > 10:
            task_name = task_name[:max_name_len] + "..."
            title = f"{tag}: {task_name} ({issue_list})"
        # If still too long, just truncate
        if len(title) > 72:
            title = title[:69] + "..."

    print(title)


if __name__ == "__main__":
    main()
