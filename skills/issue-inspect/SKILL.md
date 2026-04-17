---
name: issue-inspect
description: "This skill should be used when the user wants to check tracked GitHub issues for recent activity, detect new comments or state changes, identify cross-references between issues, and update the teamdev state file with current statuses and timestamps. This skill should be triggered when the user mentions inspecting issues, checking issue updates, syncing issue statuses, refreshing issue state, or reviewing recent activity on tracked issues."
---

# Issue Inspect

Check all tracked ongoing issues across every project and task in the teamdev state for new comments, state changes, cross-references, and commit-based closures. Update the state file to reflect the current reality on GitHub.

## Prerequisites

Verify the following before beginning inspection:

1. Confirm the state file `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` exists in the current working directory. If absent, notify the user and abort.
2. Read and parse the state file completely. Validate that the JSON structure is well-formed and contains a `projects` array.
3. Confirm the `gh` CLI is authenticated by running `gh auth status`. If not authenticated, notify the user and abort.

## Phase 1: Collect Trackable Issues

Run the collection script to build the working list:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-inspect/scripts/collect_trackable_issues.py ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

The script outputs a JSON array of issue objects, each containing: `number`, `title`, `status`, `last_activity`, `repo`, `project_name`, `task_name`. Only issues where the parent project, parent task, and the issue itself all have `status: "ongoing"` are included.

If the output is an empty array, inform the user that there are no ongoing issues to inspect and terminate gracefully.

Otherwise, inform the user how many issues will be inspected across how many projects and tasks. If the count exceeds 30, note that inspection may take a moment.

## Phase 2: Fetch Current Issue Data from GitHub

For each issue in the working list, fetch its current state sequentially:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/issue-inspect/scripts/fetch_issue_details.sh <number> <owner/repo>
```

The script outputs JSON with `comments`, `state`, `body`, `labels`, `updatedAt` on stdout. If it exits non-zero, log the error, mark the issue for manual review, and continue with remaining issues.

## Phase 3: Detect Changes

For each successfully fetched issue, pipe the GitHub JSON into the detection script:

```bash
echo '<github_json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-inspect/scripts/detect_changes.py "<tracked_last_activity>"
```

The script outputs a JSON object containing:
- `new_comments`: `{ "count": N, "authors": [...], "latest_timestamp": "..." }`
- `closed_on_github`: boolean
- `github_updated_at`: timestamp string
- `commit_closures`: array of `{ "pattern": "...", "referenced_number": N }`
- `cross_references`: array of `{ "pattern": "...", "referenced_number": N, "repo": "..." }`
- `has_changes`: boolean

Build a list of change records for issues that have changes. For each changed issue, construct:

```json
{
  "project_name": "...",
  "task_name": "...",
  "issue_number": N,
  "new_status": "<ongoing or finished>",
  "new_last_activity": "<appropriate timestamp>"
}
```

Rules for determining updates:
- If `closed_on_github` is true, set `new_status` to `"finished"` and `new_last_activity` to `github_updated_at`.
- If `commit_closures` references this issue's number, set `new_status` to `"finished"` and `new_last_activity` to current ISO 8601 timestamp.
- If `new_comments.count > 0`, keep status as `"ongoing"` and set `new_last_activity` to `new_comments.latest_timestamp`.
- If multiple conditions apply, `"finished"` takes priority over `"ongoing"`.

Collect all cross-references where the referenced issue is tracked in a **different task** for Phase 5.

## Phase 4: Apply Changes and Propagate Timestamps

Pipe the change records into the apply script:

```bash
echo '<changes_json_array>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-inspect/scripts/apply_changes.py ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

The script:
- Applies all issue-level status and timestamp changes.
- Propagates timestamps upward: each modified task's `last_activity` is set to the max of its issues, and each modified project's `last_activity` to the max of its tasks.
- Outputs the updated state JSON on **stdout**.
- Outputs a staleness report on **stderr** as JSON with `all_finished_tasks` and `stale_tasks` arrays.

Capture both outputs. The stdout becomes the new state; the stderr informs Phase 6.

## Phase 5: Handle Cross-Reference Suggestions

If cross-references were detected in Phase 3 suggesting issues in different tasks might belong together, present them to the user via `AskUserQuestion`.

For each cross-reference group, display:
- The source issue (number, title, current project/task)
- The referenced issue (number, title, current project/task)
- The nature of the reference (parent/child, dependency, related)

Allow the user to choose:
1. **Move the source issue** to the referenced issue's task.
2. **Move the referenced issue** to the source issue's task.
3. **Leave both issues** in their current tasks.

If the user chooses to move, run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-inspect/scripts/move_issue.py \
  ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json <issue_number> "<src_project>" "<src_task>" "<dst_project>" "<dst_task>"
```

The script outputs the updated state JSON on stdout. Write it to `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`.

## Phase 6: Detect Stale Tasks

Use the staleness report from Phase 4 (stderr output of `apply_changes.py`).

- **`all_finished_tasks`**: For each task where all issues are finished, ask the user via `AskUserQuestion` whether to mark the task itself as `"finished"`. Apply only if confirmed (update the task status in the state manually and re-write).
- **`stale_tasks`**: Note these in the summary report as potentially stale (last activity > 14 days, no changes this run). Do not change their status automatically.

## Phase 7: Write Updated State

Write the final state to `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` using the Write tool with 2-space indented JSON.

Before writing, verify:
- No issues were accidentally duplicated across tasks.
- No issues lost required fields during processing.
- All timestamps are valid ISO 8601 format.

## Phase 8: Generate Summary Report

Present a comprehensive summary:

**Activity Overview**:
- Total issues inspected
- Issues with new comments (list each with issue number, repo, count of new comments)
- Issues closed on GitHub (list each with issue number, repo)
- Issues closed via commit references (list each with issue number, repo)
- Issues with no changes detected

**Cross-Reference Findings**:
- Any cross-references detected and the user's decisions
- Issues that were moved between tasks

**Staleness Alerts**:
- Tasks where all issues are finished (and user's decisions)
- Tasks flagged as potentially stale

**Errors**:
- Any issues that could not be fetched from GitHub
- Any unexpected data encountered

## Error Handling

- **Rate limiting**: If `gh` commands return rate-limit errors, pause and inform the user.
- **Deleted issues**: If an issue no longer exists on GitHub (404), flag it in the report and suggest removal. Do not remove automatically.
- **Permission changes**: If a repository is no longer accessible, skip all issues for that repo and continue.
- **Malformed state**: If the state file has structural issues, report the problems and abort without partial changes.

## Important Constraints

- Never close or modify issues on GitHub. This skill only reads from GitHub and writes to the local state file.
- Never remove issues from the state file without explicit user confirmation.
- Never create new issues or tasks. This skill only updates existing tracked entities.
- Always preserve the full state structure when writing.
- Process all ongoing projects, not just a subset.
- Use ISO 8601 format with timezone designator for all timestamps (e.g., `2026-04-16T12:00:00Z`).
