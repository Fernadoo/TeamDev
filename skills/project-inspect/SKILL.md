---
name: project-inspect
description: This skill should be used when the user wants to inspect, review, or audit projects in their teamdev state. This skill should be used when the user asks to check project statuses, find stale projects, clean up old projects, or recalculate project health from their underlying tasks. This skill should be used when the user mentions "inspect projects", "check projects", "project status", "stale projects", "clean up projects", or "audit projects".
---

# Project Inspection

Inspect all projects in the teamdev state file. Derive each project's status from its child tasks, detect staleness, prompt the user for cleanup of stale projects, and persist the updated state. Display a summary of all changes made during the inspection.

## State File Location

The state file is `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` in the current working directory. If the file does not exist, inform the user that no teamdev state was found and stop execution. Do not create a new state file during inspection.

## Data Model Reference

The state file follows this structure:

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

## Scripts

All deterministic operations are implemented as scripts in `${CLAUDE_PLUGIN_ROOT}/skills/project-inspect/scripts/`.

### recalculate_projects.py

Recalculates all project statuses from child tasks, updates last_activity, and detects staleness.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-inspect/scripts/recalculate_projects.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

**Input**: Path to state file. Optional `--current-date ISO` for testing.

**Output** (JSON to stdout):
- `state`: The updated state object
- `changes`: Array of objects `{project_name, old_status, new_status}` for each status transition
- `stale_projects`: Array of objects `{project_name, repo, last_activity}` for each stale project requiring user decision
- `warnings`: List of warnings (projects with no tasks, null timestamps, etc.)
- `status_counts`: Object with counts per status (`{ongoing, finished, stale}`)
- `total_inspected`: Total number of projects inspected

**Exit codes**: 0 success, 1 file not found, 2 invalid JSON / missing projects.

**Status derivation rules**:
- A task with status "stale" is treated as effectively finished for project status derivation.
- If any task is "ongoing", project is "ongoing".
- If all tasks are "finished" or "stale", project is "finished".
- If project is "finished" and last_activity > 7 days ago, project becomes "stale".

### remove_project.py

Removes a project entirely (including all nested tasks and issues) from the state.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-inspect/scripts/remove_project.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json "<project_name>"
```

**Input**: State file path, project name.

**Output**: Updated state JSON to stdout (project removed).

**Exit codes**: 0 success, 1 file not found, 2 invalid JSON, 3 project not found.

### write_state.py

Writes state JSON (from stdin) to a file with 2-space indentation and verifies the write.

```
echo '<state_json>' | python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-inspect/scripts/write_state.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

**Input**: JSON on stdin, output file path as argument.

**Output**: Prints "OK" on success.

**Exit codes**: 0 success, 1 invalid JSON on stdin, 2 write/verification failed.

## Step-by-Step Procedure

### Step 1: Recalculate All Projects

Run the recalculation script:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-inspect/scripts/recalculate_projects.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

Capture the JSON output. Parse it to extract `state`, `changes`, `stale_projects`, `warnings`, `status_counts`, and `total_inspected`.

If the script exits with a non-zero code, report the error to the user and halt.

If `warnings` is non-empty, log each warning for the user's awareness.

### Step 2: Handle Stale Projects (User Decisions)

For each entry in the `stale_projects` array from Step 1, prompt the user for a decision using AskUserQuestion. Present the project name, its repository, and the `last_activity` date.

Construct the prompt: "Project '[project_name]' (repo: [repo]) has been stale since [last_activity]. Do you want to delete this project? (yes/no)"

Process stale projects one at a time. Wait for each response before proceeding to the next. This gives the user time to consider each decision individually and understand the implications of deleting a project with all its nested data.

- If the user answers **yes**: run the removal script:

  ```
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-inspect/scripts/remove_project.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json "<project_name>"
  ```

  Capture the updated state from stdout. This becomes the working state for subsequent removals. Record that the project was deleted (name and all nested data removed).

- If the user answers **no**: leave the project as stale. Record that the project was kept.

- If the user's response is ambiguous, ask again with clearer phrasing. Do not interpret ambiguous responses as either affirmative or negative.

### Step 3: Write Updated State

After all stale project decisions are resolved, pipe the final state to the write script:

```
echo '<final_state_json>' | python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-inspect/scripts/write_state.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

If the script prints "OK", the write succeeded. If it exits non-zero, report the error and display the changes that would have been made.

### Step 4: Display Summary

Using the data from Steps 1-2, present a clear and concise summary. The summary is a critical part of this skill and must always be shown. Include:

- Total number of projects inspected (from `total_inspected`).
- For each entry in `changes`, show the transition (e.g., "ongoing -> finished", "finished -> stale").
- Number of stale projects found.
- Number of stale projects deleted by user decision, listing their names.
- Number of stale projects kept by user decision, listing their names.
- Current status distribution (from `status_counts`, adjusted for any deletions in Step 2).

Format the summary as a structured, readable list. Example:

```
Project Inspection Summary
--------------------------
Projects inspected: 5
Status changes:
  - "auth-service": ongoing -> finished
  - "legacy-api": finished -> stale
Stale projects found: 2
  - "legacy-api" (stale since 2026-04-01) - deleted by user
  - "old-dashboard" (stale since 2026-03-28) - kept by user
Current status distribution:
  - Ongoing: 2 projects
  - Finished: 1 project
  - Stale: 1 project
```

The summary must always be displayed, even if no changes were made. In that case, indicate that all projects are up to date and no action was needed.

## Edge Cases and Error Handling

- If the `projects` array is empty, report that no projects exist to inspect, write the state file unchanged, and display a summary indicating zero projects inspected.
- If a project has an empty `tasks` array, the recalculation script logs a warning and skips status recalculation. Its existing status and `last_activity` remain unchanged.
- If `last_activity` is missing or null, the script skips staleness checks and logs a warning.
- If the state file is locked or unwritable, report the error and display the changes that would have been made.
- If all projects are deleted by the user, the write script writes an empty `projects` array. Do not delete the state file itself.

## Important Constraints

- Do not modify task-level or issue-level data during project inspection. Tasks and issues are the source of truth for project status. Only project-level `status` and `last_activity` fields may be updated (aside from whole-project deletions).
- Do not fetch any data from GitHub during this inspection. Work exclusively with data in the state file.
- Do not reorder projects in the array. Preserve existing order except where deletions remove items.
- Process all projects in a single pass.
- Always write the state file at the end, even if no changes were made, to normalize the format.
- When deleting a stale project, remove it entirely including all nested tasks and issues. There is no partial deletion.
