#!/usr/bin/env bash
# Create a pull request via the GitHub CLI.
#
# Usage:
#   create-pr.sh <title> <body_file> [base_branch]
#
# Arguments:
#   title       - PR title string
#   body_file   - Path to a file containing the PR body markdown
#   base_branch - Target branch (default: main)
#
# Outputs the PR URL to stdout on success.
#
# Exit codes:
#   0 - success, PR created
#   1 - gh cli error

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: create-pr.sh <title> <body_file> [base_branch]" >&2
    exit 1
fi

TITLE="$1"
BODY_FILE="$2"
BASE="${3:-main}"

if [ ! -f "$BODY_FILE" ]; then
    echo "Error: body file not found: $BODY_FILE" >&2
    exit 1
fi

BODY="$(cat "$BODY_FILE")"

PR_URL=$(gh pr create --title "$TITLE" --body "$BODY" --base "$BASE" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "Error: gh pr create failed:" >&2
    echo "$PR_URL" >&2
    exit 1
fi

echo "$PR_URL"
