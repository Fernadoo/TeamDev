#!/usr/bin/env python3
"""Detect changes between tracked state and GitHub data for a single issue.

Usage: detect_changes.py <tracked_last_activity>
Reads GitHub issue JSON from stdin (comments, state, body, labels, updatedAt).

Output: JSON object on stdout with detected changes:
{
  "new_comments": { "count": N, "authors": [...], "latest_timestamp": "..." },
  "closed_on_github": bool,
  "github_updated_at": "...",
  "commit_closures": [ { "pattern": "...", "referenced_number": N } ],
  "cross_references": [ { "pattern": "...", "referenced_number": N, "repo": "..." } ],
  "has_changes": bool
}

Exit codes: 0 = success, 1 = error
"""

import json
import re
import sys


CLOSURE_PATTERNS = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE
)

CROSS_REF_PATTERNS = [
    # owner/repo#number
    re.compile(r"([\w.-]+/[\w.-]+)#(\d+)"),
    # plain #number
    re.compile(r"(?<!\w)#(\d+)"),
    # task list items
    re.compile(r"- \[[ x]\] #(\d+)"),
]


def find_cross_references(text):
    """Find cross-references in text."""
    refs = []
    for match in CROSS_REF_PATTERNS[0].finditer(text):
        refs.append({"pattern": match.group(0), "referenced_number": int(match.group(2)), "repo": match.group(1)})
    for pattern in CROSS_REF_PATTERNS[1:]:
        for match in pattern.finditer(text):
            groups = match.groups()
            refs.append({"pattern": match.group(0), "referenced_number": int(groups[-1]), "repo": ""})
    return refs


def find_commit_closures(text):
    """Find commit-based closure references in text."""
    closures = []
    for match in CLOSURE_PATTERNS.finditer(text):
        closures.append({"pattern": match.group(0), "referenced_number": int(match.group(1))})
    return closures


def main():
    if len(sys.argv) != 2:
        print("Usage: detect_changes.py <tracked_last_activity>", file=sys.stderr)
        sys.exit(1)

    tracked_last_activity = sys.argv[1]

    try:
        gh_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing stdin JSON: {e}", file=sys.stderr)
        sys.exit(1)

    result = {
        "new_comments": {"count": 0, "authors": [], "latest_timestamp": ""},
        "closed_on_github": False,
        "github_updated_at": gh_data.get("updatedAt", ""),
        "commit_closures": [],
        "cross_references": [],
        "has_changes": False,
    }

    # Detect new comments
    comments = gh_data.get("comments", [])
    new_comment_authors = []
    latest_ts = ""
    new_count = 0
    for comment in comments:
        created = comment.get("createdAt", "")
        if created > tracked_last_activity:
            new_count += 1
            author = comment.get("author", {}).get("login", "unknown")
            if author not in new_comment_authors:
                new_comment_authors.append(author)
            if created > latest_ts:
                latest_ts = created

    result["new_comments"] = {
        "count": new_count,
        "authors": new_comment_authors,
        "latest_timestamp": latest_ts,
    }

    # Detect state changes
    gh_state = gh_data.get("state", "").upper()
    if gh_state == "CLOSED":
        result["closed_on_github"] = True
        result["has_changes"] = True

    # Scan body and comments for cross-references and commit closures
    all_text = gh_data.get("body", "") or ""
    for comment in comments:
        all_text += "\n" + (comment.get("body", "") or "")

    result["cross_references"] = find_cross_references(all_text)
    result["commit_closures"] = find_commit_closures(all_text)

    if new_count > 0 or result["commit_closures"]:
        result["has_changes"] = True

    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
