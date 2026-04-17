#!/usr/bin/env bash
# Fetch full issue details from GitHub (both plain text and JSON).
# Usage: fetch_issue_view.sh <issue_number> <owner/repo>
# Output: Prints a separator "---JSON---" between plain text and JSON output.
# Exit codes: 0 = success, 1 = argument error, 2 = gh CLI failure

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <issue_number> <owner/repo>" >&2
  exit 1
fi

NUMBER="$1"
REPO="$2"

# Fetch plain text view
if ! PLAIN=$(gh issue view "$NUMBER" --repo "$REPO" 2>/tmp/gh_pick_err_$$); then
  echo "Error fetching issue #$NUMBER from $REPO: $(cat /tmp/gh_pick_err_$$)" >&2
  rm -f /tmp/gh_pick_err_$$
  exit 2
fi

# Fetch structured JSON view
if ! JSON_DATA=$(gh issue view "$NUMBER" --repo "$REPO" \
  --json title,body,comments,labels,assignees,state,createdAt,updatedAt,milestone 2>/tmp/gh_pick_err_$$); then
  echo "Error fetching JSON for issue #$NUMBER from $REPO: $(cat /tmp/gh_pick_err_$$)" >&2
  rm -f /tmp/gh_pick_err_$$
  exit 2
fi

rm -f /tmp/gh_pick_err_$$

echo "$PLAIN"
echo "---JSON---"
echo "$JSON_DATA"
