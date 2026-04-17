---
name: ship
description: >
  This skill should be used when the user wants to commit a resolved issue,
  optionally create a task branch if the task is fully complete, migrate commits,
  and push to the remote. This skill should be triggered when the user says
  "ship", "ship it", "commit and push", "finalize issue", or any variation
  indicating they want to commit completed work and push it upstream. This skill
  assumes the review-gate has already passed.
---

# Ship — Commit, Branch, Migrate, and Push

Commit the resolved issue using the co-authoring commit skill, determine
whether the parent task is now fully finished, create and populate a task
branch if so, push to the remote, and update the state file to reflect the
new status of issues, tasks, and projects.

---

## Overview

The ship skill is the bridge between reviewed code and a pushed branch. It
handles four responsibilities in sequence:

1. Create a co-authored commit for the resolved issue.
2. Check if the parent task is now complete.
3. If complete, create a task branch, migrate commits, and push. If not,
   push the current branch.
4. Update the state file.

---

## Step 1 — Commit the Resolved Issue

Invoke the `commit-commands:commit` skill to create the commit. Provide
context about which issue is being resolved so the commit message references
the correct issue number.

After the commit skill completes, verify a new commit was created:

```
git log -1 --oneline
```

If the commit was not created (nothing staged, skill error), report the
failure and stop. Do not proceed without a successful commit.

---

## Step 2 — Evaluate Task Completion

Run the task completion checker to determine if all issues in the parent
task are now finished:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ship/scripts/check-task-completion.py ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json <issue_number>
```

This script outputs JSON with the task metadata:
```json
{
  "task_complete": true,
  "project_name": "...",
  "task_name": "...",
  "task_tag": "...",
  "issue_numbers": [120, 231],
  "finished_count": 2,
  "total_count": 2
}
```

**Exit codes:**
- `0` — task is complete, proceed to Step 3a (branch creation)
- `1` — task is NOT complete, proceed to Step 3b (push current branch)
- `2` — error (state file missing, issue not found); report to user and stop

Save the output JSON — `task_name`, `task_tag`, and `issue_numbers` are
needed for branch naming in Step 3a.

---

## Step 3a — Task Complete: Create Branch and Migrate Commits

This step only executes when the task is fully complete (exit code 0 from
check-task-completion).

### Build the Branch Name

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ship/scripts/build-branch-name.py <tag> <task_name> <issue_numbers...>
```

Example: `python3 .../build-branch-name.py feat add-auth 120 231` outputs
`feat/add-auth-120-231`.

### Identify Commits to Migrate

Before creating the branch, identify the commit SHAs that belong to this
task on the current working branch. Use `git log --oneline` to find the
relevant commits.

### Create Branch and Cherry-Pick

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/ship/scripts/create-task-branch.sh <branch_name> <commit_sha>...
```

This script:
1. Runs `git fetch origin main`
2. Creates a new branch from `origin/main`
3. Cherry-picks the specified commits onto it

**Exit codes:**
- `0` — success
- `1` — fetch failed
- `2` — branch creation failed
- `3` — cherry-pick failed (conflicts)

**On exit code 3 (cherry-pick conflict):**
1. Report the conflict to the user with full details (which files, nature
   of conflict).
2. Do not attempt to auto-resolve.
3. Instruct the user to resolve manually, then `git cherry-pick --continue`.
4. Pause execution until resolved.

**CRITICAL**: Never use `git merge`. Always use cherry-pick or rebase for
clean, linear history.

---

## Step 3b — Task Not Complete: Stay on Current Branch

If the task still has unfinished issues, do not create a new branch. Proceed
directly to pushing the current branch.

---

## Step 3 (Common) — Push to Remote

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/ship/scripts/push-branch.sh [branch_name]
```

If branch_name is omitted, pushes the current branch. The script sets
upstream tracking with `-u`.

If the push fails, report the error to the user. Do not force-push unless
the user explicitly requests it.

---

## Step 4 — Update the State File

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ship/scripts/update-state.py ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json <issue_number>
```

This script updates the state file in place:
- Sets the issue status to `"finished"` with current timestamp
- Recalculates task status (finished if all issues finished)
- Recalculates project status (finished if all tasks finished)
- Updates `last_activity` timestamps at each level

Outputs a JSON summary of changes to stdout. Verify the output confirms the
expected status transitions.

**Exit codes:**
- `0` — success
- `1` — issue not found
- `2` — error (file missing, invalid JSON)

---

## Error Handling

### State File Missing

If `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` does not exist, the scripts will exit with code 2.
Report the error to the user. Do not create a default state file.

### Issue Not Found in State

If the scripts exit with code 1 (issue not found), ask the user to verify
the issue number and ensure the state file is up to date.

### Empty Commit

If there are no staged changes and the commit skill produces no commit, do
not proceed with branching or pushing. Report that there is nothing to ship.

---

## Integration with the Development Workflow

The ship skill sits after review-gate and before pr-create:

```
develop -> review-gate -> ship -> pr-create -> pr-feedback -> develop (loop)
```

Always ensure `review-gate` has passed before invoking `ship`. After
shipping, if the task is complete and a branch was created, the natural
next step is `pr-create`.

---

## Summary of Actions

1. Invoke `commit-commands:commit` for the resolved issue.
2. Verify the commit was created (`git log -1 --oneline`).
3. Run `check-task-completion.py` to evaluate task status.
4. If task complete: run `build-branch-name.py`, identify commits, run
   `create-task-branch.sh`.
5. If task not complete: stay on current branch.
6. Run `push-branch.sh` to push to remote.
7. Run `update-state.py` to mark issue finished and recalculate statuses.
