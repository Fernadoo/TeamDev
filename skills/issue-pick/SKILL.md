---
name: issue-pick
description: "This skill should be used when the user wants to select a specific GitHub issue to work on from their tracked ongoing issues. This skill should be triggered when the user mentions picking an issue, choosing what to work on, selecting an issue, starting work on an issue, or asking which issues are available to work on."
---

# Issue Pick

Present the user with all ongoing issues from the teamdev state, organized by project and task, allow them to select one, display full issue details, and output the selected issue number and repository so development can begin.

## Prerequisites

Verify the following before proceeding:

1. Confirm the state file `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` exists in the current working directory. If absent, notify the user that no projects are tracked and abort.
2. Read and parse the state file completely. Validate that the JSON structure is well-formed and contains a `projects` array.
3. Confirm the `gh` CLI is authenticated by running `gh auth status`. If authentication fails, notify the user and abort.

## Phase 1: Collect Eligible Issues

Run the collection script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-pick/scripts/collect_eligible_issues.py ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

The script outputs a JSON array of issue objects, each containing: `number`, `title`, `status`, `last_activity`, `repo`, `project_name`, `task_name`, `task_tag`. Only issues where the parent project, parent task, and the issue itself all have `status: "ongoing"` are included.

If the output is an empty array, inform the user that there are no ongoing issues available. Suggest running `issue-triage` to discover new issues or `issue-inspect` to refresh statuses. If there are tracked projects but all issues are finished, emphasize `issue-triage`; if no projects exist at all, suggest adding a project first.

### Large Number of Issues

If more than 30 eligible issues exist, offer the user optional filters via `AskUserQuestion` before displaying the full list:

> "There are <N> ongoing issues. Filter by project, task tag, or show all?"

Apply the selected filter to the issues array before proceeding.

### Stale Issues Warning

If all eligible issues have `last_activity` older than 14 days, mention this to the user and suggest running `issue-inspect` first.

## Phase 2: Build the Selection Menu

Pipe the eligible issues (possibly filtered) into the formatting script:

```bash
echo '<eligible_issues_json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-pick/scripts/format_issue_menu.py
```

The script outputs:
- **stdout**: A formatted hierarchical menu with sequential numbering, grouped by project and task, with stale indicators for issues inactive > 7 days. Includes a legend with totals and activity date range.
- **stderr**: A JSON selection map keyed by menu number, e.g., `{ "1": { "number": 42, "repo": "owner/repo", "project_name": "...", "task_name": "...", "title": "..." }, ... }`

Capture both outputs. Present the stdout menu to the user. Use the stderr map to resolve user selections.

## Phase 3: User Selection

Present the menu to the user via `AskUserQuestion`:

> "Select an issue to work on by entering its number:"

Validate the user's input against the selection map:
- If the number matches a key in the selection map, proceed.
- If invalid (out of range, not a number, empty), re-prompt with a clarifying message indicating the valid range.
- If the user types `0` or `cancel`, inform them no issue was selected and terminate.
- If the user types `#<number>` (a GitHub issue number), attempt to match it against the selection map values. If a unique match is found, use it. If ambiguous (same number in multiple repos), ask the user to clarify by menu number.

### Single Issue Available

If only one eligible issue exists, still present it but ask for confirmation:

> "There is only one ongoing issue available. Work on #<number> - <title>? (yes/no)"

If the user declines, terminate with a suggestion to run `issue-triage`.

## Phase 4: Fetch Full Issue Details

Once the user selects a valid issue, retrieve complete details:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/issue-pick/scripts/fetch_issue_view.sh <number> <owner/repo>
```

The script outputs plain text followed by `---JSON---` followed by structured JSON. Split on the separator.

If the script exits non-zero, inform the user of the error and offer to try again or select a different issue.

### Display the Issue

Present the full issue to the user:

1. **Header**: Issue number, title, and repository.
2. **Metadata**: Labels, assignees, milestone (if any), creation date, last update date (from the JSON portion).
3. **Body**: The full issue body rendered as markdown.
4. **Comments**: All comments in chronological order, each prefixed with author and timestamp. If more than 10 comments, show the first 3 and last 3 with a note about how many were omitted. Offer to show all if requested.

## Phase 5: Output Selection

After displaying the full issue, output a clear structured summary:

```
Selected issue: #<number>
Repository: <owner/repo>
Project: <project-name>
Task: <task-name>
Title: <issue-title>
```

Confirm to the user that the issue has been selected and suggest next steps (creating a feature branch, checking out the repo, reviewing related code).

## Phase 6: Update State Timestamps

Run the timestamp update script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-pick/scripts/update_pick_timestamps.py \
  ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json "<project_name>" "<task_name>" <issue_number>
```

The script updates the selected issue's `last_activity` to the current timestamp and propagates upward to the parent task and project. It outputs the full updated state JSON on stdout.

Write the output to `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` using the Write tool with 2-space indented JSON.

If writing the state fails, inform the user that the selection was successful but the state file could not be updated. The timestamp update is non-critical.

## Error Handling

- **State file missing or malformed**: Notify the user with a clear error message and abort.
- **GitHub fetch failure**: If `fetch_issue_view.sh` fails, inform the user and offer to retry or select a different issue.
- **State write failure**: Inform the user that selection succeeded but state could not be updated. Development can proceed regardless.
- **Authentication expired**: If a `gh` command fails with authentication error mid-flow, notify the user and suggest `gh auth login`.

## Important Constraints

- Never modify issues on GitHub. This skill only reads from GitHub and writes to the local state file.
- Never auto-select an issue for the user. Always require explicit user confirmation.
- Never remove or modify issue statuses during the pick process. This skill only updates `last_activity` timestamps.
- Preserve all existing state data when writing. Only modify timestamps on the selected issue and its parent task/project.
- Always display the full issue details before finalizing selection.
- Use ISO 8601 format with timezone designator for all timestamps (e.g., `2026-04-16T12:00:00Z`).
- Output the selected issue number and repository in a consistent format that other tools or skills can parse.
