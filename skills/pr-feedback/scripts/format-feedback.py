#!/usr/bin/env python3
"""Organize and format PR feedback by file path and reviewer.

Usage:
    format-feedback.py < feedback.json

Reads the combined feedback JSON (as output by fetch-feedback.sh) from stdin.
Outputs a structured markdown report to stdout and a machine-readable JSON
summary to stderr.

The JSON summary on stderr contains:
  {
    "has_blocking": true/false,
    "reviewers": [{"login": "...", "state": "...", "summary": "..."}],
    "files_with_comments": ["path/to/file.ts", ...],
    "actionable_count": 5,
    "total_comments": 12
  }
"""
import json
import sys
from collections import defaultdict


def main():
    raw = json.load(sys.stdin)

    inline_comments = raw.get("inline_comments", [])
    reviews = raw.get("reviews", [])
    general_comments = raw.get("general_comments", [])

    # --- Organize inline comments by file path ---
    by_file = defaultdict(list)
    for c in inline_comments:
        path = c.get("path", "unknown")
        by_file[path].append({
            "line": c.get("line") or c.get("original_line") or "?",
            "reviewer": c.get("user", {}).get("login", "unknown"),
            "body": c.get("body", ""),
            "id": c.get("id"),
            "in_reply_to_id": c.get("in_reply_to_id"),
            "created_at": c.get("created_at", ""),
        })

    # Sort comments within each file by line number
    for path in by_file:
        by_file[path].sort(key=lambda x: x["line"] if isinstance(x["line"], int) else 0)

    # --- Process reviews ---
    reviewer_verdicts = []
    has_blocking = False
    # Get latest review per reviewer
    latest_reviews = {}
    for r in reviews:
        login = r.get("user", {}).get("login", "unknown")
        state = r.get("state", "COMMENTED")
        submitted = r.get("submitted_at", "")
        if login not in latest_reviews or submitted > latest_reviews[login].get("submitted_at", ""):
            latest_reviews[login] = r

    for login, r in latest_reviews.items():
        state = r.get("state", "COMMENTED")
        if state == "CHANGES_REQUESTED":
            has_blocking = True
        reviewer_verdicts.append({
            "login": login,
            "state": state,
            "summary": r.get("body", ""),
        })

    # --- Build markdown output ---
    lines = []

    # Review verdicts table
    lines.append("## Review Verdicts\n")
    if reviewer_verdicts:
        lines.append("| Reviewer | Verdict | Summary |")
        lines.append("|----------|---------|---------|")
        for rv in reviewer_verdicts:
            state_display = rv["state"].replace("_", " ").title()
            summary = rv["summary"][:80].replace("|", "\\|").replace("\n", " ") if rv["summary"] else ""
            lines.append(f"| @{rv['login']} | {state_display} | {summary} |")
    else:
        lines.append("No reviews submitted yet.")
    lines.append("")

    # Blocking status
    if has_blocking:
        lines.append("**STATUS: CHANGES REQUESTED** — Blocking feedback must be addressed.\n")
    else:
        approved = any(rv["state"] == "APPROVED" for rv in reviewer_verdicts)
        if approved:
            lines.append("**STATUS: APPROVED** — PR is approved.\n")
        else:
            lines.append("**STATUS: PENDING** — No blocking feedback, awaiting reviews.\n")

    # Inline comments by file
    if by_file:
        lines.append("## Inline Comments\n")
        for path in sorted(by_file.keys()):
            comments = by_file[path]
            # Filter out replies for top-level display
            top_level = [c for c in comments if not c.get("in_reply_to_id")]
            if not top_level:
                top_level = comments
            lines.append(f"### {path}\n")
            for c in top_level:
                lines.append(f"- **@{c['reviewer']}** (line {c['line']}): {c['body']}")
            lines.append("")

    # General comments
    if general_comments:
        lines.append("## General Comments\n")
        for c in general_comments:
            author = c.get("author", {}).get("login", "unknown")
            body = c.get("body", "")
            lines.append(f"- **@{author}**: {body}")
        lines.append("")

    # Output markdown to stdout
    print("\n".join(lines))

    # Output machine-readable summary to stderr
    actionable = sum(
        len([c for c in comments if not c.get("in_reply_to_id")])
        for comments in by_file.values()
    )
    summary = {
        "has_blocking": has_blocking,
        "reviewers": reviewer_verdicts,
        "files_with_comments": sorted(by_file.keys()),
        "actionable_count": actionable,
        "total_comments": len(inline_comments) + len(general_comments),
    }
    print(json.dumps(summary), file=sys.stderr)


if __name__ == "__main__":
    main()
