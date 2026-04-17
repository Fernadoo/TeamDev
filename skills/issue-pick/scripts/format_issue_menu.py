#!/usr/bin/env python3
"""Format eligible issues into a hierarchical selection menu.

Usage: format_issue_menu.py [--stale-days N]
Reads JSON array of eligible issues from stdin (as output by collect_eligible_issues.py).

Options:
  --stale-days N   Number of days after which an issue is flagged as stale (default: 7)

Output: Plain text menu on stdout, plus a JSON mapping on stderr:
  { "1": { "number": N, "repo": "...", "project_name": "...", "task_name": "..." }, ... }

Exit codes: 0 = success, 1 = error
"""

import json
import sys
from datetime import datetime, timezone, timedelta


def main():
    stale_days = 7
    args = sys.argv[1:]
    if "--stale-days" in args:
        idx = args.index("--stale-days")
        stale_days = int(args[idx + 1])

    try:
        issues = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing stdin JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not issues:
        print("No eligible issues found.")
        json.dump({}, sys.stderr)
        sys.exit(0)

    now = datetime.now(timezone.utc)
    stale_cutoff = (now - timedelta(days=stale_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Group by project -> task
    grouped = {}
    for issue in issues:
        pname = issue["project_name"]
        tname = issue["task_name"]
        grouped.setdefault(pname, {}).setdefault(tname, []).append(issue)

    # Build menu text and selection map
    lines = []
    selection_map = {}
    seq = 1

    project_count = len(grouped)
    task_count = sum(len(tasks) for tasks in grouped.values())
    total_count = len(issues)

    # Collect all last_activity for date range
    all_dates = [i["last_activity"] for i in issues if i.get("last_activity")]

    for pname, tasks in sorted(grouped.items()):
        repo = ""
        for tname, task_issues in sorted(tasks.items()):
            if not repo and task_issues:
                repo = task_issues[0].get("repo", "")

        lines.append(f"Project: {pname} (repo: {repo})")
        if total_count > 20:
            pcount = sum(len(ti) for ti in tasks.values())
            lines[-1] += f"  [{pcount} issues]"

        for tname, task_issues in sorted(tasks.items()):
            tag = task_issues[0].get("task_tag", "") if task_issues else ""
            task_line = f"  Task: {tname} [{tag}]"
            if total_count > 20:
                task_line += f"  [{len(task_issues)} issues]"
            lines.append(task_line)

            for issue in task_issues:
                stale_marker = ""
                la = issue.get("last_activity", "")
                if la and la < stale_cutoff:
                    stale_marker = f" (stale: last activity {la[:10]})"
                lines.append(
                    f"    {seq}. #{issue['number']} - {issue['title']}{stale_marker}"
                )
                selection_map[str(seq)] = {
                    "number": issue["number"],
                    "repo": issue.get("repo", ""),
                    "project_name": pname,
                    "task_name": tname,
                    "title": issue.get("title", ""),
                }
                seq += 1

    # Legend
    lines.append("")
    lines.append(f"Total: {total_count} issues across {project_count} projects and {task_count} tasks")
    if all_dates:
        lines.append(f"Activity range: {min(all_dates)[:10]} to {max(all_dates)[:10]}")

    print("\n".join(lines))
    json.dump(selection_map, sys.stderr, indent=2)


if __name__ == "__main__":
    main()
