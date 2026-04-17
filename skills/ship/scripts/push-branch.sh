#!/usr/bin/env bash
# Push the current branch to origin with upstream tracking.
#
# Usage:
#   push-branch.sh [branch_name]
#
# If branch_name is omitted, pushes the current branch.
#
# Exit codes:
#   0 - success
#   1 - push failed

set -euo pipefail

if [ $# -ge 1 ]; then
    BRANCH="$1"
else
    BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

if ! git push -u origin "$BRANCH" 2>&1; then
    echo "Error: failed to push branch '$BRANCH' to origin" >&2
    exit 1
fi

echo "Branch '$BRANCH' pushed to origin with upstream tracking set."
