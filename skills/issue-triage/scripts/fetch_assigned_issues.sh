#!/usr/bin/env bash
# Fetch GitHub issues assigned to @me for a given repo.
# Usage: fetch_assigned_issues.sh <owner/repo>
# Output: JSON array of issues on stdout
# Exit codes: 0 = success, 1 = argument error, 2 = gh CLI failure

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <owner/repo>" >&2
  exit 1
fi

REPO="$1"

if ! gh issue list --assignee @me --repo "$REPO" \
  --json number,title,body,labels,createdAt --limit 100 2>/tmp/gh_error_$$; then
  echo "Error fetching issues from $REPO: $(cat /tmp/gh_error_$$)" >&2
  rm -f /tmp/gh_error_$$
  exit 2
fi

rm -f /tmp/gh_error_$$
