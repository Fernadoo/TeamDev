#!/usr/bin/env bash
# Gather all diff information for review-gate.
#
# Usage:
#   gather_diffs.sh [--format json|text]
#
# Collects staged diff, unstaged diff, changed file list, and stats.
# Outputs a JSON object (default) or plain text sections.
#
# Exit codes:
#   0  Success (diffs collected, at least one non-empty)
#   1  No changes detected (both staged and unstaged diffs are empty)
#   2  Not a git repository

set -euo pipefail

FORMAT="json"
for arg in "$@"; do
    case "$arg" in
        --format=json) FORMAT="json" ;;
        --format=text) FORMAT="text" ;;
        --format) shift; FORMAT="${1:-json}" ;;
    esac
done

# Check we're in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "Error: Not inside a git repository" >&2
    exit 2
fi

STAGED_DIFF=$(git diff --cached 2>/dev/null || true)
UNSTAGED_DIFF=$(git diff 2>/dev/null || true)
CHANGED_FILES=$(git diff --name-only 2>/dev/null || true)
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || true)
DIFF_STAT=$(git diff --stat 2>/dev/null || true)
STAGED_STAT=$(git diff --cached --stat 2>/dev/null || true)

# Check if there are any changes at all
if [ -z "$STAGED_DIFF" ] && [ -z "$UNSTAGED_DIFF" ]; then
    echo "Error: No changes detected (staged or unstaged)" >&2
    exit 1
fi

if [ "$FORMAT" = "text" ]; then
    echo "=== STAGED DIFF ==="
    if [ -n "$STAGED_DIFF" ]; then
        echo "$STAGED_DIFF"
    else
        echo "(none)"
    fi
    echo ""
    echo "=== UNSTAGED DIFF ==="
    if [ -n "$UNSTAGED_DIFF" ]; then
        echo "$UNSTAGED_DIFF"
    else
        echo "(none)"
    fi
    echo ""
    echo "=== CHANGED FILES (unstaged) ==="
    if [ -n "$CHANGED_FILES" ]; then
        echo "$CHANGED_FILES"
    else
        echo "(none)"
    fi
    echo ""
    echo "=== CHANGED FILES (staged) ==="
    if [ -n "$STAGED_FILES" ]; then
        echo "$STAGED_FILES"
    else
        echo "(none)"
    fi
    echo ""
    echo "=== DIFF STATS (unstaged) ==="
    if [ -n "$DIFF_STAT" ]; then
        echo "$DIFF_STAT"
    else
        echo "(none)"
    fi
    echo ""
    echo "=== DIFF STATS (staged) ==="
    if [ -n "$STAGED_STAT" ]; then
        echo "$STAGED_STAT"
    else
        echo "(none)"
    fi
else
    # JSON output: write to temp files and use python to safely escape
    TMPDIR_DIFFS=$(mktemp -d)
    trap "rm -rf $TMPDIR_DIFFS" EXIT

    echo "$STAGED_DIFF" > "$TMPDIR_DIFFS/staged.diff"
    echo "$UNSTAGED_DIFF" > "$TMPDIR_DIFFS/unstaged.diff"
    echo "$CHANGED_FILES" > "$TMPDIR_DIFFS/changed_unstaged.txt"
    echo "$STAGED_FILES" > "$TMPDIR_DIFFS/changed_staged.txt"
    echo "$DIFF_STAT" > "$TMPDIR_DIFFS/stat_unstaged.txt"
    echo "$STAGED_STAT" > "$TMPDIR_DIFFS/stat_staged.txt"

    python3 -c "
import json, os, sys

tmpdir = sys.argv[1]

def read_file(path):
    with open(path, 'r') as f:
        content = f.read().strip()
    return content if content else None

result = {
    'staged_diff': read_file(os.path.join(tmpdir, 'staged.diff')),
    'unstaged_diff': read_file(os.path.join(tmpdir, 'unstaged.diff')),
    'changed_files_unstaged': read_file(os.path.join(tmpdir, 'changed_unstaged.txt')),
    'changed_files_staged': read_file(os.path.join(tmpdir, 'changed_staged.txt')),
    'stat_unstaged': read_file(os.path.join(tmpdir, 'stat_unstaged.txt')),
    'stat_staged': read_file(os.path.join(tmpdir, 'stat_staged.txt')),
    'has_changes': True,
}

# Compute combined diff for reviewer consumption
combined_parts = []
if result['staged_diff']:
    combined_parts.append('=== STAGED CHANGES ===\n' + result['staged_diff'])
if result['unstaged_diff']:
    combined_parts.append('=== UNSTAGED CHANGES ===\n' + result['unstaged_diff'])
result['combined_diff'] = '\n\n'.join(combined_parts)

# Count total changed lines (rough)
total_lines = 0
for diff in [result['staged_diff'], result['unstaged_diff']]:
    if diff:
        total_lines += len(diff.splitlines())
result['total_diff_lines'] = total_lines
result['is_large_diff'] = total_lines > 2000

json.dump(result, sys.stdout, indent=2)
print()
" "$TMPDIR_DIFFS"
fi
