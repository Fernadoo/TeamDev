#!/usr/bin/env bash
# Check PR approval status.
#
# Usage:
#   check-pr-status.sh <pr_number> [owner/repo]
#
# Outputs JSON to stdout:
#   {"review_decision": "APPROVED|CHANGES_REQUESTED|REVIEW_REQUIRED", "approved": true/false}
#
# Exit codes:
#   0 - PR is approved
#   1 - PR is not approved (changes requested or review required)
#   2 - error

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: check-pr-status.sh <pr_number> [owner/repo]" >&2
    exit 2
fi

NUMBER="$1"
REPO_FLAG=""
if [ $# -ge 2 ]; then
    REPO_FLAG="--repo $2"
fi

RESULT=$(gh pr view "$NUMBER" $REPO_FLAG --json reviewDecision 2>/dev/null) || {
    echo "Error: could not fetch PR #$NUMBER status" >&2
    exit 2
}

DECISION=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reviewDecision','REVIEW_REQUIRED'))")

if [ "$DECISION" = "APPROVED" ]; then
    echo "{\"review_decision\": \"$DECISION\", \"approved\": true}"
    exit 0
else
    echo "{\"review_decision\": \"$DECISION\", \"approved\": false}"
    exit 1
fi
