#!/usr/bin/env bash
# Fetch all issues assigned to @me from a GitHub repo.
#
# Usage: fetch-issues.sh <owner/repo>
#
# Outputs JSON array to stdout. On failure, prints error to stderr and exits 1.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: fetch-issues.sh <owner/repo>" >&2
    exit 1
fi

REPO="$1"

if ! command -v gh &>/dev/null; then
    echo "Error: gh CLI is not installed. Install it from https://cli.github.com/" >&2
    exit 1
fi

gh issue list \
    --repo "$REPO" \
    --assignee @me \
    --state all \
    --json number,title,state,labels,updatedAt \
    --limit 500
