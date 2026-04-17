---
name: task-inspect
description: This skill should be used when the user wants to inspect, review, or audit tasks across all projects in their teamdev state. This skill should be used when the user asks to check task statuses, find stale tasks, clean up finished tasks, or recalculate task health from their underlying GitHub issues. This skill should be used when the user mentions "inspect tasks", "check tasks", "task status", "stale tasks", "clean up tasks", or "audit tasks".
---

# Task Inspection

Inspect all tasks across every project in the teamdev state file. Derive each task's status from its child issues, detect staleness, prompt the user for cleanup of stale tasks, propagate status changes upward to parent projects, and persist the updated state.

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

All deterministic operations are implemented as scripts in `${CLAUDE_PLUGIN_ROOT}/skills/task-inspect/scripts/`.

### recalculate_tasks.py

Recalculates all task statuses from child issues, updates last_activity, detects staleness, and propagates changes to project statuses.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/task-inspect/scripts/recalculate_tasks.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

**Input**: Path to state file. Optional `--current-date ISO` for testing.

**Output** (JSON to stdout):
- `state`: The updated state object (tasks and projects recalculated)
- `changes`: List of human-readable status transitions (e.g., "Task 'foo' in project 'bar': ongoing -> finished")
- `stale_tasks`: Array of objects `{project_name, task_name, last_activity}` for each stale task requiring user decision
- `warnings`: List of warnings (tasks with no issues, null timestamps, etc.)

**Exit codes**: 0 success, 1 file not found, 2 invalid JSON / missing projects.

### remove_task.py

Removes a single task from a project's tasks array.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/task-inspect/scripts/remove_task.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json "<project_name>" "<task_name>"
```

**Input**: State file path, project name, task name.

**Output**: Updated state JSON to stdout (task removed).

**Exit codes**: 0 success, 1 file not found, 2 invalid JSON, 3 project/task not found.

### write_state.py

Writes state JSON (from stdin) to a file with 2-space indentation and verifies the write.

```
echo '<state_json>' | python3 "${CLAUDE_PLUGIN_ROOT}/skills/task-inspect/scripts/write_state.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

**Input**: JSON on stdin, output file path as argument.

**Output**: Prints "OK" on success.

**Exit codes**: 0 success, 1 invalid JSON on stdin, 2 write/verification failed.

## Step-by-Step Procedure

### Step 1: Recalculate All Tasks and Projects

Run the recalculation script:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/task-inspect/scripts/recalculate_tasks.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

Capture the JSON output. Parse it to extract `state`, `changes`, `stale_tasks`, and `warnings`.

If the script exits with a non-zero code, report the error to the user and halt.

If `warnings` is non-empty, log each warning for the user's awareness.

### Step 2: Handle Stale Tasks (User Decisions)

For each entry in the `stale_tasks` array from Step 1, prompt the user for a decision using AskUserQuestion. Present the task name, its parent project name, and the `last_activity` date.

Construct the prompt: "Task '[task_name]' in project '[project_name]' has been stale since [last_activity]. Do you want to delete this task? (yes/no)"

Process stale tasks one at a time. Wait for each response before proceeding to the next.

- If the user answers **yes**: run the removal script on the current state, feeding the previous state as input:

  ```
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/task-inspect/scripts/remove_task.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json "<project_name>" "<task_name>"
  ```

  Capture the updated state from stdout. This becomes the working state for subsequent removals. Record that the task was deleted.

- If the user answers **no**: leave the task as stale. Record that the task was kept.

- If the user's response is ambiguous, ask again with clearer phrasing.

### Step 3: Write Updated State

After all stale task decisions are resolved, pipe the final state to the write script:

```
echo '<final_state_json>' | python3 "${CLAUDE_PLUGIN_ROOT}/skills/task-inspect/scripts/write_state.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

If the script prints "OK", the write succeeded. If it exits non-zero, report the error and display the changes that would have been made.

### Step 4: Display Summary

Using the `changes` array from Step 1 and the deletion decisions from Step 2, present a concise summary:

- Total number of tasks inspected across all projects.
- Number of tasks whose status changed (from what to what).
- Number of stale tasks found.
- Number of stale tasks deleted by user decision.
- Number of stale tasks kept by user decision.
- Any projects whose status changed as a result of task updates.

Format the summary as a concise, readable list. Do not include the full state dump. Only highlight what changed.

## Edge Cases and Error Handling

- If a project has an empty `tasks` array, the recalculation script skips it during task iteration but still includes it in project status propagation.
- If a task has an empty `issues` array, the script logs a warning and skips status recalculation for that task. Its existing status and `last_activity` remain unchanged.
- If `last_activity` is missing or null on a task or issue, the script skips staleness checks and logs a warning.
- If the state file is locked or unwritable, report the error to the user and display the changes that would have been made without persisting them.
- If the user provides an ambiguous response to a stale task prompt, ask again with clearer phrasing.

## Important Constraints

- Do not modify issue-level data during task inspection. Issues are the source of truth for task status.
- Do not fetch any data from GitHub during this inspection. Work exclusively with data in the state file.
- Do not reorder tasks or projects in the arrays. Preserve existing order except where deletions remove items.
- Process all projects and tasks in a single pass.
- Always write the state file at the end, even if no changes were made, to normalize the format.
