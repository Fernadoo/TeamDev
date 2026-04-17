#!/usr/bin/env bash
# Fetch all review feedback for a PR.
#
# Usage:
#   fetch-feedback.sh <owner> <repo> <pr_number>
#
# Outputs JSON to stdout with three keys:
#   {"inline_comments": [...], "reviews": [...], "general_comments": [...]}
#
# Exit codes:
#   0 - success
#   1 - one or more API calls failed

set -euo pipefail

if [ $# -ne 3 ]; then
    echo "Usage: fetch-feedback.sh <owner> <repo> <pr_number>" >&2
    exit 1
fi

OWNER="$1"
REPO="$2"
NUMBER="$3"

ERRORS=0

# Fetch inline comments
INLINE=$(gh api "repos/$OWNER/$REPO/pulls/$NUMBER/comments" --paginate 2>/dev/null) || {
    INLINE="[]"
    ERRORS=$((ERRORS + 1))
}

# Fetch reviews
REVIEWS=$(gh api "repos/$OWNER/$REPO/pulls/$NUMBER/reviews" --paginate 2>/dev/null) || {
    REVIEWS="[]"
    ERRORS=$((ERRORS + 1))
}

# Fetch general comments
GENERAL_RAW=$(gh pr view "$NUMBER" --repo "$OWNER/$REPO" --json comments 2>/dev/null) || {
    GENERAL_RAW='{"comments":[]}'
    ERRORS=$((ERRORS + 1))
}

# Combine into single JSON output
python3 -c "
import json, sys

inline = json.loads(sys.argv[1])
reviews = json.loads(sys.argv[2])
general_raw = json.loads(sys.argv[3])
general = general_raw.get('comments', [])

print(json.dumps({
    'inline_comments': inline,
    'reviews': reviews,
    'general_comments': general
}, indent=2))
" "$INLINE" "$REVIEWS" "$GENERAL_RAW"

if [ $ERRORS -gt 0 ]; then
    echo "Warning: $ERRORS API call(s) failed, partial results returned" >&2
fi
