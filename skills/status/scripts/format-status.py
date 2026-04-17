#!/usr/bin/env python3
"""Format the teamdev state as a hierarchical status display.

Reads teamdev-state.json and outputs a formatted tree view grouped by status,
with clickable GitHub links, relative timestamps, and a summary footer.

Usage: format-status.py [options] [path/to/teamdev-state.json]

Options:
  --compact           Show only project and task summaries (no issues)
  --project NAME      Filter to a single project (case-insensitive partial match)
  --filter STATUS     Show only items with this status (ongoing|finished|stale)

Exit codes:
  0 - Success
  1 - File not found
  2 - Invalid JSON
"""
import json
import sys
import os
from datetime import datetime, timezone, timedelta


def parse_args():
    opts = {"compact": False, "project": None, "filter": None, "path": "teamdev-state.json"}
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--compact":
            opts["compact"] = True
        elif args[i] == "--project" and i + 1 < len(args):
            i += 1
            opts["project"] = args[i]
        elif args[i] == "--filter" and i + 1 < len(args):
            i += 1
            opts["filter"] = args[i].lower()
        elif not args[i].startswith("--"):
            opts["path"] = args[i]
        i += 1
    return opts


def relative_time(iso_ts: str) -> str:
    """Convert ISO 8601 timestamp to a human-readable relative time."""
    if not iso_ts:
        return "unknown"
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"

    now = datetime.now(timezone.utc)
    delta = now - ts

    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "just now"

    minutes = total_seconds // 60
    hours = total_seconds // 3600
    days = delta.days

    if minutes < 60:
        return f"{minutes}m ago"
    elif hours < 24:
        return f"{hours}h ago"
    elif days < 30:
        return f"{days}d ago"
    else:
        months = days // 30
        return f"{months} months ago" if months > 1 else "1 month ago"


def short_relative(iso_ts: str) -> str:
    """Shorter relative timestamp for issue lines."""
    if not iso_ts:
        return "?"
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return "?"
    now = datetime.now(timezone.utc)
    delta = now - ts
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "now"
    minutes = total_seconds // 60
    hours = total_seconds // 3600
    days = delta.days
    if minutes < 60:
        return f"{minutes}m ago"
    elif hours < 24:
        return f"{hours}h ago"
    elif days < 30:
        return f"{days}d ago"
    else:
        months = days // 30
        return f"{months}mo ago" if months > 1 else "1mo ago"


STATUS_ORDER = {"ongoing": 0, "finished": 1, "stale": 2}


def sort_key(item):
    return STATUS_ORDER.get(item.get("status", ""), 99)


def count_issues_by_status(task):
    counts = {"ongoing": 0, "finished": 0}
    for issue in task.get("issues", []):
        s = issue.get("status", "ongoing")
        counts[s] = counts.get(s, 0) + 1
    return counts


def format_project(project, compact=False, status_filter=None):
    lines = []
    repo = project.get("repo", "unknown/repo")
    status = project.get("status", "unknown").upper()
    la = project.get("last_activity", "")

    lines.append(f"## Project: {project['name']} ({repo}) -- {status}")
    lines.append(f"   Last activity: {relative_time(la)} ({la})")
    lines.append("")

    tasks = sorted(project.get("tasks", []), key=sort_key)
    if not tasks:
        lines.append("   No tasks tracked yet.")
        lines.append("")
        return lines

    for task in tasks:
        task_status = task.get("status", "unknown")
        if status_filter and task_status != status_filter:
            continue

        tag = task.get("tag", "misc")
        tla = task.get("last_activity", "")
        ic = count_issues_by_status(task)
        total = sum(ic.values())
        issue_summary = f"{total} total ({ic.get('ongoing', 0)} ongoing, {ic.get('finished', 0)} finished)"

        lines.append(f"   ### [{tag}] {task['name']} -- {task_status.upper()}")
        lines.append(f"       Last activity: {relative_time(tla)} ({tla})")
        lines.append(f"       Issues: {issue_summary}")

        if not compact:
            lines.append("")
            issues = sorted(task.get("issues", []), key=sort_key)
            for issue in issues:
                i_status = issue.get("status", "unknown")
                if status_filter and i_status != status_filter:
                    continue
                ref = f"{repo}#{issue['number']}"
                title = issue.get("title", "Untitled")
                ila = issue.get("last_activity", "")
                # Pad for alignment
                label = f"{ref} {title}"
                lines.append(f"       - {label:.<60s} {i_status.upper():<10s} ({short_relative(ila)})")

        lines.append("")

    return lines


def compute_summary(projects, status_filter=None):
    counts = {
        "projects": {"ongoing": 0, "finished": 0, "stale": 0},
        "tasks": {"ongoing": 0, "finished": 0, "stale": 0},
        "issues": {"ongoing": 0, "finished": 0},
    }

    for project in projects:
        ps = project.get("status", "ongoing")
        if not status_filter or ps == status_filter:
            counts["projects"][ps] = counts["projects"].get(ps, 0) + 1

        for task in project.get("tasks", []):
            ts = task.get("status", "ongoing")
            if not status_filter or ts == status_filter:
                counts["tasks"][ts] = counts["tasks"].get(ts, 0) + 1

            for issue in task.get("issues", []):
                ist = issue.get("status", "ongoing")
                if not status_filter or ist == status_filter:
                    counts["issues"][ist] = counts["issues"].get(ist, 0) + 1

    return counts


def main():
    opts = parse_args()
    path = opts["path"]

    if not os.path.exists(path):
        print(f"State file not found: {path}", file=sys.stderr)
        print("NO_STATE_FILE", file=sys.stdout)
        sys.exit(1)

    try:
        with open(path, "r") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(2)

    projects = state.get("projects", [])
    if not projects:
        print("EMPTY_STATE", file=sys.stdout)
        sys.exit(0)

    # Apply project filter
    if opts["project"]:
        pf = opts["project"].lower()
        projects = [p for p in projects if pf in p.get("name", "").lower()]
        if not projects:
            print(f"No project matching '{opts['project']}'", file=sys.stderr)
            sys.exit(0)

    # Apply status filter at project level
    status_filter = opts["filter"]
    if status_filter:
        projects = [p for p in projects if p.get("status") == status_filter
                    or any(t.get("status") == status_filter for t in p.get("tasks", []))]

    # Sort projects by status
    projects = sorted(projects, key=sort_key)

    output = []
    for i, project in enumerate(projects):
        if i > 0:
            output.append("---")
            output.append("")
        output.extend(format_project(project, compact=opts["compact"], status_filter=status_filter))

    # Summary footer
    counts = compute_summary(state.get("projects", []), status_filter)
    pc = counts["projects"]
    tc = counts["tasks"]
    ic = counts["issues"]

    output.append("---")
    output.append("Summary:")
    output.append(f"  Projects: {sum(pc.values())} ({pc['ongoing']} ongoing, {pc['finished']} finished, {pc['stale']} stale)")
    output.append(f"  Tasks:    {sum(tc.values())} ({tc['ongoing']} ongoing, {tc['finished']} finished, {tc['stale']} stale)")
    output.append(f"  Issues:   {sum(ic.values())} ({ic['ongoing']} ongoing, {ic['finished']} finished)")

    print("\n".join(output))


if __name__ == "__main__":
    main()
