---
name: state-sync
description: >
  This skill should be used when the user wants to synchronize the local teamdev
  state file with live GitHub data, refresh issue statuses, recalculate task and
  project statuses, or detect stale items. It reads the local ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json,
  queries GitHub for current issue states via the gh CLI, and writes the updated
  state back to disk.
---

# State Sync

Synchronize the local `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` file with live GitHub issue data, recalculate all derived statuses, and persist the updated state.

## Overview

Read the local state file, fetch current issue information from GitHub for every tracked project, update issue statuses based on their GitHub state, propagate status changes upward through tasks and projects, detect staleness, and write the result back to the state file. Every status field in the state file is derived from GitHub data and time-based rules -- never set manually.

## Scripts

All deterministic operations are delegated to scripts in `${CLAUDE_PLUGIN_ROOT}/skills/state-sync/scripts/`:

| Script | Purpose |
|--------|---------|
| `read-state.py` | Read and validate `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`. Exit 0 = valid state on stdout, exit 1 = file not found (empty state on stdout), exit 2 = invalid JSON (error on stderr). |
| `fetch-issues.sh` | Fetch all issues assigned to `@me` from a given repo via `gh issue list`. Takes `owner/repo` as argument, outputs JSON array to stdout. |
| `update-issues.py` | Compare GitHub issue data against local state and update statuses/titles/timestamps. Takes state file path, GitHub issues JSON path, and project name as args. Outputs updated state JSON to stdout, report to stderr. |
| `recalculate-statuses.py` | Recalculate all task/project statuses from child entities, apply staleness detection. Reads state from stdin, outputs updated state to stdout, change report to stderr. Accepts `--stale-days N` (default 7). |
| `write-state.py` | Validate state structure and write to disk. Reads JSON from stdin, writes to the specified path (default `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`). Exit 1 = validation error, exit 2 = write error. |

## Step-by-Step Procedure

### 1. Read the Local State File

Run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/state-sync/scripts/read-state.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

- **Exit 0**: Valid state JSON is on stdout. Capture it and proceed.
- **Exit 1**: File not found. The script outputs an empty initial state `{"projects": []}`. Write this to disk using `write-state.py` and inform the user the state was initialized.
- **Exit 2**: Malformed JSON. Report the error from stderr to the user and stop. Do not overwrite a corrupted file without explicit user confirmation.

### 2. Fetch GitHub Data for Each Project

For each project in the state, extract the `repo` field and run:
```bash
"${CLAUDE_PLUGIN_ROOT}/skills/state-sync/scripts/fetch-issues.sh" <owner/repo>
```

Save the output to a temporary file for each project. If the command fails for a specific repo (network error, auth failure, 404), log the error but continue with remaining projects. Do not abort the entire sync because one repository is unreachable.

If `fetch-issues.sh` warns that `gh` is not installed, stop and tell the user to install it from https://cli.github.com/ or run `gh auth login`.

### 3. Update Issue Statuses

For each project that returned GitHub data, run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/state-sync/scripts/update-issues.py" \
    state.json gh-issues.json "<project-name>"
```

This script:
- Matches local issues to GitHub issues by `number`
- Maps GitHub `OPEN` -> `ongoing`, `CLOSED` -> `finished`
- Updates `title` and `last_activity` from GitHub data
- Outputs the updated state JSON to stdout
- Outputs a report to stderr with: issues updated, status changes, issues not found on GitHub

Capture the updated state and the report. For issues reported as "not found on GitHub", note them in the sync output -- they may have been unassigned or deleted. Do not remove them from the state automatically.

Pipe the updated state into the next project's update, chaining updates across all projects.

### 4. Recalculate All Derived Statuses

After all issue updates, pipe the state through:
```bash
cat updated-state.json | python3 "${CLAUDE_PLUGIN_ROOT}/skills/state-sync/scripts/recalculate-statuses.py"
```

This script applies the following rules (described here for your reference when interpreting results):

**Task status** (derived from child issues):
- `ongoing` if any child issue is `ongoing`
- `finished` if all child issues are `finished`
- `stale` if `finished` and `last_activity` is older than 7 days

**Project status** (derived from child tasks):
- `ongoing` if any child task is `ongoing`
- `finished` if all child tasks are `finished` or `stale`
- `stale` if `finished` and `last_activity` is older than 7 days

The script reports status changes and newly stale items on stderr.

Tasks or projects with zero children are left unchanged.

### 5. Write Updated State to Disk

Pipe the final state through:
```bash
cat final-state.json | python3 "${CLAUDE_PLUGIN_ROOT}/skills/state-sync/scripts/write-state.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

The script validates that every project, task, and issue has all required fields before writing. If validation fails, it reports errors on stderr and exits without writing. Relay the validation errors to the user.

### 6. Report Sync Results

Collect all reports from stderr across the pipeline and present a summary:
- Number of projects synced
- Number of issues updated (with breakdown of status changes)
- Issues not found on GitHub
- Projects that could not be reached (network/auth errors)
- Items newly marked as stale

## Data Model Reference

```json
{
  "projects": [
    {
      "name": "project-name",
      "repo": "owner/repo",
      "status": "ongoing | finished | stale",
      "last_activity": "2026-04-16T12:00:00Z",
      "tasks": [
        {
          "name": "task-name",
          "tag": "feat | bugfix | refactor | ...",
          "status": "ongoing | finished | stale",
          "last_activity": "2026-04-16T12:00:00Z",
          "issues": [
            {
              "number": 120,
              "title": "Short issue title",
              "status": "ongoing | finished",
              "last_activity": "2026-04-16T12:00:00Z"
            }
          ]
        }
      ]
    }
  ]
}
```

## Status Rules Summary

| Level   | Ongoing                        | Finished                        | Stale                                |
|---------|--------------------------------|---------------------------------|--------------------------------------|
| Issue   | GitHub state is open           | GitHub state is closed          | N/A (issues do not go stale)         |
| Task    | Any child issue is ongoing     | All child issues are finished   | Finished and last_activity > 7 days  |
| Project | Any child task is ongoing      | All child tasks are finished    | Finished and last_activity > 7 days  |

## Error Handling

- If `gh` is not installed or not authenticated: `fetch-issues.sh` will report the error. Suggest running `gh auth login`.
- If a specific repository returns a 404: note it in the sync report, continue with other projects.
- If the state file is locked or unwritable: `write-state.py` will exit 2 with the filesystem error. Report it to the user.
- Never remove data from the state file automatically. Only add or update fields.

## Edge Cases

- A newly created project with no tasks yet: `recalculate-statuses.py` skips it, keeping existing status.
- A task with all issues removed from GitHub (unassigned): `update-issues.py` reports them as not found; keep in state, flag in report.
- Multiple projects pointing to the same repository: run `fetch-issues.sh` separately for each.
- Timestamps in different formats: scripts normalize to ISO 8601 with UTC timezone suffix `Z` when writing.
