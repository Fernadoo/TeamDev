#!/usr/bin/env bash
# Validate a GitHub repository exists and is accessible.
#
# Usage: validate-repo.sh <owner/repo>
#
# Outputs JSON with repo name, owner, and description to stdout.
# On failure, prints error to stderr and exits with non-zero code.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: validate-repo.sh <owner/repo>" >&2
    exit 1
fi

REPO="$1"

if ! command -v gh &>/dev/null; then
    echo "Error: gh CLI is not installed. Install it from https://cli.github.com/" >&2
    exit 1
fi

# Validate format
if [[ ! "$REPO" =~ ^[^/]+/[^/]+$ ]]; then
    echo "Error: Repository must be in owner/repo format, got: $REPO" >&2
    exit 1
fi

gh repo view "$REPO" --json name,owner,description 2>&1
