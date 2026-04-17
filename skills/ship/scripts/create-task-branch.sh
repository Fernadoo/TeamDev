#!/usr/bin/env bash
# Create a task branch from origin/main and cherry-pick commits onto it.
#
# Usage:
#   create-task-branch.sh <branch_name> <commit_sha>...
#
# Steps:
#   1. git fetch origin main
#   2. git checkout -b <branch_name> origin/main
#   3. git cherry-pick <commit_sha>...
#
# Exit codes:
#   0 - success
#   1 - fetch failed
#   2 - branch creation failed
#   3 - cherry-pick failed (conflict or other error)

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: create-task-branch.sh <branch_name> <commit_sha>..." >&2
    exit 1
fi

BRANCH_NAME="$1"
shift
COMMITS=("$@")

# Detect default branch name
DEFAULT_BRANCH=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')
if [ -z "$DEFAULT_BRANCH" ]; then
    DEFAULT_BRANCH="main"
fi

# Step 1: Fetch latest default branch
if ! git fetch origin "$DEFAULT_BRANCH" 2>&1; then
    echo "Error: failed to fetch origin/$DEFAULT_BRANCH" >&2
    exit 1
fi

# Step 2: Create branch from origin/<default>
if ! git checkout -b "$BRANCH_NAME" "origin/$DEFAULT_BRANCH" 2>&1; then
    echo "Error: failed to create branch '$BRANCH_NAME' from origin/$DEFAULT_BRANCH" >&2
    exit 2
fi

# Step 3: Cherry-pick commits
if ! git cherry-pick "${COMMITS[@]}" 2>&1; then
    echo "Error: cherry-pick failed. Conflicts may need manual resolution." >&2
    echo "Resolve conflicts, then run: git cherry-pick --continue" >&2
    exit 3
fi

echo "Branch '$BRANCH_NAME' created with ${#COMMITS[@]} commit(s) cherry-picked."
