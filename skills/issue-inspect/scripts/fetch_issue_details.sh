#!/usr/bin/env bash
# Fetch current issue details from GitHub for inspection.
# Usage: fetch_issue_details.sh <issue_number> <owner/repo>
# Output: JSON with comments, state, body, labels, updatedAt on stdout
# Exit codes: 0 = success, 1 = argument error, 2 = gh CLI failure

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <issue_number> <owner/repo>" >&2
  exit 1
fi

NUMBER="$1"
REPO="$2"

if ! gh issue view "$NUMBER" --repo "$REPO" \
  --json comments,state,body,labels,updatedAt 2>/tmp/gh_inspect_err_$$; then
  echo "Error fetching issue #$NUMBER from $REPO: $(cat /tmp/gh_inspect_err_$$)" >&2
  rm -f /tmp/gh_inspect_err_$$
  exit 2
fi

rm -f /tmp/gh_inspect_err_$$
