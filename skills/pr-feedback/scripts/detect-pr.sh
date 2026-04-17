#!/usr/bin/env bash
# Detect the current PR from the current branch.
#
# Usage:
#   detect-pr.sh
#
# Outputs JSON to stdout:
#   {"number": 42, "url": "https://...", "head": "feat/...", "state": "OPEN", "owner": "org", "repo": "name"}
#
# Exit codes:
#   0 - PR found
#   1 - no PR found or error

set -euo pipefail

# Get PR info from current branch
PR_JSON=$(gh pr view --json number,url,headRefName,state 2>/dev/null) || {
    echo "Error: no PR found for current branch" >&2
    exit 1
}

# Extract owner/repo from remote
REMOTE_URL=$(git remote get-url origin 2>/dev/null) || {
    echo "Error: could not get origin remote URL" >&2
    exit 1
}

# Parse owner/repo from various remote URL formats
# Works with both SSH (git@github.com:owner/repo.git) and HTTPS (https://github.com/owner/repo.git)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's#.*[:/]([^/]+/[^/]+)\.git$#\1#; s#.*[:/]([^/]+/[^/]+)$#\1#')
OWNER=$(echo "$OWNER_REPO" | cut -d'/' -f1)
REPO=$(echo "$OWNER_REPO" | cut -d'/' -f2)

# Merge into single JSON output
python3 -c "
import json, sys
pr = json.loads(sys.argv[1])
print(json.dumps({
    'number': pr['number'],
    'url': pr['url'],
    'head': pr['headRefName'],
    'state': pr['state'],
    'owner': sys.argv[2],
    'repo': sys.argv[3]
}, indent=2))
" "$PR_JSON" "$OWNER" "$REPO"
