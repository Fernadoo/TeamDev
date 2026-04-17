---
name: status
description: >
  This skill should be used when the user wants to see an overview of their
  tracked projects, tasks, and issues with current statuses. It reads the local
  ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json file and displays a formatted, hierarchical summary grouped
  by status, with clickable GitHub issue links and activity timestamps.
---

# Status

Display a formatted overview of all tracked projects, tasks, and issues from the local teamdev state file, organized by status and annotated with activity timestamps and GitHub links.

## Overview

Read the `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` file from the current working directory, and produce a clear, scannable hierarchical summary showing what is active, completed, and stale across all tracked development work. All formatting and computation is handled by the `format-status.py` script.

## Scripts

All deterministic operations are delegated to scripts in `${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/`:

| Script | Purpose |
|--------|---------|
| `format-status.py` | Reads `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`, computes relative timestamps, formats the full tree display with GitHub links, issue counts, and summary footer. Supports `--compact`, `--project NAME`, and `--filter STATUS` options. |

## Prerequisites

Before displaying the status overview, recommend running the `state-sync` skill first to ensure the local state file reflects the latest GitHub data. Mention this recommendation to the user but do not block on it -- if the user wants to see the current local state without syncing, proceed.

If the user explicitly asks for a fresh or up-to-date status, run state-sync before producing the display.

## Step-by-Step Procedure

### 1. Generate the Status Display

Run the appropriate variant of the format script based on what the user asked for:

**Full status (default):**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/format-status.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

**Compact mode** (user asks for brief/compact view):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/format-status.py" --compact ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

**Single project filter** (user asks about a specific project):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/format-status.py" --project "project-name" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

**Status filter** (user asks to see only ongoing/finished/stale items):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/format-status.py" --filter ongoing ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

Options can be combined, e.g. `--compact --filter ongoing`.

### 2. Handle Script Output

Check the script's stdout and exit code:

- **Exit 0, stdout contains `EMPTY_STATE`**: No projects are being tracked. Inform the user and suggest running the `project-setup` skill to add a project.
- **Exit 0, stdout contains formatted output**: Present the output directly to the user. The script produces a ready-to-display hierarchical tree with a summary footer.
- **Exit 1, stdout contains `NO_STATE_FILE`**: The state file does not exist. Inform the user that no teamdev state has been initialized and suggest running `project-setup`.
- **Exit 2**: Invalid JSON in the state file. Report the parse error from stderr and stop.

### 3. Offer Next Actions

Based on the displayed state, suggest relevant next actions:

- If there are stale items: suggest reviewing them for archival or removal.
- If there are ongoing items: no special suggestion needed.
- If everything is finished or stale: suggest setting up a new project or cleaning up stale entries.
- If `last_activity` timestamps are old across the board: suggest running `state-sync` to refresh.

Keep suggestions to one or two sentences.

## Output Format Reference

The script produces output in this format:

```
## Project: my-awesome-project (owner/repo) -- ONGOING
   Last activity: 2 hours ago (2026-04-16T10:00:00Z)

   ### [feat] implement-auth -- ONGOING
       Last activity: 2 hours ago (2026-04-16T10:00:00Z)
       Issues: 3 total (2 ongoing, 1 finished)

       - owner/repo#120 Add login endpoint ............. ONGOING    (2h ago)
       - owner/repo#121 Add token refresh .............. ONGOING    (5h ago)
       - owner/repo#119 Set up auth middleware ......... FINISHED   (2d ago)

   ### [bugfix] fix-pagination -- FINISHED
       Last activity: 3 days ago (2026-04-13T08:30:00Z)
       Issues: 2 total (0 ongoing, 2 finished)

       - owner/repo#115 Fix offset calculation ........ FINISHED   (3d ago)
       - owner/repo#116 Add pagination tests .......... FINISHED   (3d ago)

---
Summary:
  Projects: 2 (1 ongoing, 0 finished, 1 stale)
  Tasks:    3 (1 ongoing, 1 finished, 1 stale)
  Issues:   6 (2 ongoing, 4 finished)
```

Items are ordered by actionability: ongoing first, then finished, then stale. Issue lines include clickable `owner/repo#number` references and dot-padded alignment.

## Error Handling

- State file not found: detected by exit code 1. Suggest `project-setup`.
- Empty state: detected by `EMPTY_STATE` output. Suggest `project-setup`.
- Structural issues (missing fields, wrong types): the script displays as much valid data as possible and notes issues on stderr.
- Unparseable `last_activity` timestamps: displayed as "unknown" for the relative time.

## Edge Cases

- Projects with many tasks (10+): all are displayed; suggest compact mode if output is long.
- Tasks with many issues (20+): all are displayed with a count at the task level.
- Mixed timezone timestamps: normalized to UTC for comparison; displayed as-is from state file.
- Very old stale items: displayed at the bottom of the stale section with clear age indication.
