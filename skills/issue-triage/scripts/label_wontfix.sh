#!/usr/bin/env bash
# Label an issue as wontfix. Creates the label if it doesn't exist.
# Usage: label_wontfix.sh <issue_number> <owner/repo>
# Exit codes: 0 = success, 1 = argument error, 2 = gh CLI failure

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <issue_number> <owner/repo>" >&2
  exit 1
fi

NUMBER="$1"
REPO="$2"

if ! gh issue edit "$NUMBER" --repo "$REPO" --add-label wontfix 2>/tmp/gh_label_err_$$; then
  # Label might not exist; try creating it first
  if gh label create wontfix --repo "$REPO" \
    --description "Issue will not be addressed" --color ffffff 2>/dev/null; then
    # Retry the edit after creating the label
    if ! gh issue edit "$NUMBER" --repo "$REPO" --add-label wontfix 2>/tmp/gh_label_err_$$; then
      echo "Error labeling issue #$NUMBER in $REPO after creating label: $(cat /tmp/gh_label_err_$$)" >&2
      rm -f /tmp/gh_label_err_$$
      exit 2
    fi
  else
    echo "Error labeling issue #$NUMBER in $REPO: $(cat /tmp/gh_label_err_$$)" >&2
    rm -f /tmp/gh_label_err_$$
    exit 2
  fi
fi

rm -f /tmp/gh_label_err_$$
echo "Labeled issue #$NUMBER in $REPO as wontfix"
