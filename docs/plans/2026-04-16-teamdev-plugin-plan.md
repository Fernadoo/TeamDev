# Teamdev Plugin Implementation Plan

**Date**: 2026-04-16
**Design doc**: [2026-04-16-teamdev-plugin-design.md](./2026-04-16-teamdev-plugin-design.md)

## Phase 1: Foundation

### Step 1.1: Update plugin.json manifest
- **File**: `.claude-plugin/plugin.json`
- **Action**: Already exists with name/description/version/author. No changes needed.

### Step 1.2: Create state-sync skill
- **File**: `skills/state-sync/SKILL.md`
- **What it does**:
  - Reads `teamdev-state.json` from the project root (or `~/.claude/teamdev-state.json` for cross-project)
  - If file doesn't exist, initializes empty state `{"projects": []}`
  - For each project in state, calls `gh issue list --repo owner/repo --assignee @me --json number,title,state,labels,updatedAt` to fetch current GitHub state
  - Updates issue statuses based on GitHub state (open -> ongoing, closed -> finished)
  - Recalculates task statuses from child issues
  - Recalculates project statuses from child tasks
  - Marks tasks/projects as stale if finished > 7 days (comparing `last_activity` to current date)
  - Writes updated state back to JSON file
- **Dependencies**: None (foundational skill)

### Step 1.3: Create status skill
- **File**: `skills/status/SKILL.md`
- **What it does**:
  - Reads `teamdev-state.json`
  - Displays formatted table/tree of all projects -> tasks -> issues with their statuses
  - Groups by status (ongoing first, then finished, then stale)
  - Shows issue numbers as clickable `owner/repo#123` links
- **Dependencies**: state-sync (should run state-sync first to ensure fresh data)

## Phase 2: Inspection Chain

### Step 2.1: Create issue-triage skill
- **File**: `skills/issue-triage/SKILL.md`
- **What it does**:
  - Fetches newly assigned issues via `gh issue list --assignee @me --json number,title,body,labels,createdAt`
  - Compares against tracked issues in state to find new ones
  - For each new issue, runs double-phase validation:
    1. Uses `claude-sonnet-4-6` (via Agent tool with model override) for self-review: is the issue reproducible? Is the proposed solution reasonable?
    2. Invokes `codex:adversarial-review` for adversarial review
  - If invalid: labels issue as `wontfix` via `gh issue edit --add-label wontfix`
  - If valid: uses AskUserQuestion to ask user which existing task to merge into, or creates a new task
  - Updates state file
- **Dependencies**: state-sync must run first

### Step 2.2: Create issue-inspect skill
- **File**: `skills/issue-inspect/SKILL.md`
- **What it does**:
  - For each tracked ongoing issue, checks for updates via `gh issue view <number> --repo owner/repo --json comments,state,body,labels,updatedAt`
  - Detects: new comments, state changes, references to other issues (parent/sub)
  - If new parent/sub issue found: suggests merging into same task via AskUserQuestion
  - If issue closed by commit referencing `resolve`/`close`: mark as finished
  - Updates `last_activity` timestamps
  - Updates state file
- **Dependencies**: state-sync, issue-triage should run before this

### Step 2.3: Create task-inspect skill
- **File**: `skills/task-inspect/SKILL.md`
- **What it does**:
  - For each task, recalculates status from child issues
  - Checks staleness: if task finished and `last_activity` > 7 days ago, mark stale
  - For stale tasks: uses AskUserQuestion to ask user if they want to delete
  - If user says delete: removes task from state
  - Updates state file
- **Dependencies**: issue-inspect should run before this

### Step 2.4: Create project-inspect skill
- **File**: `skills/project-inspect/SKILL.md`
- **What it does**:
  - For each project, recalculates status from child tasks
  - Checks staleness: if project finished and `last_activity` > 7 days ago, mark stale
  - For stale projects: uses AskUserQuestion to ask user if they want to delete
  - If user says delete: removes project from state
  - Updates state file
- **Dependencies**: task-inspect should run before this

## Phase 3: Development Flow

### Step 3.1: Create project-setup skill
- **File**: `skills/project-setup/SKILL.md`
- **What it does**:
  - Asks user for project name and git repo URL (owner/repo format) via AskUserQuestion
  - Validates repo exists via `gh repo view owner/repo`
  - Fetches existing issues assigned to user via `gh issue list`
  - Groups issues into tasks via AskUserQuestion (user decides grouping)
  - Creates project entry in state file with tasks and issues
  - Runs state-sync to populate initial statuses
- **Dependencies**: state-sync

### Step 3.2: Create issue-pick skill
- **File**: `skills/issue-pick/SKILL.md`
- **What it does**:
  - Reads state, filters to ongoing issues across all ongoing tasks
  - Presents them to user via AskUserQuestion with project/task context
  - Returns the selected issue number and repo for the user to work on
  - Optionally shows issue body/comments for context via `gh issue view`
- **Dependencies**: state-sync (for fresh data)

## Phase 4: Review & Ship

### Step 4.1: Create review-gate skill
- **File**: `skills/review-gate/SKILL.md`
- **What it does**:
  - Phase 1: Self-review using `claude-sonnet-4-6` (Agent tool with model: "sonnet")
    - Reviews staged/unstaged changes (`git diff`, `git diff --cached`)
    - Checks for correctness, security issues, style
    - Returns pass/fail with specific feedback
  - Phase 2: Adversarial review using `codex:adversarial-review`
    - Invokes the external skill on the same changes
    - Collects verdict
  - If either phase fails: reports specific issues, user goes back to development
  - If both pass: signals ready to ship
- **Dependencies**: None (standalone, but typically invoked after development)

### Step 4.2: Create ship skill
- **File**: `skills/ship/SKILL.md`
- **What it does**:
  - Step 1: For the resolved issue, make a co-authoring commit via `commit-commands:commit`
  - Step 2: Check if the parent task is now fully finished (all issues resolved)
    - If task finished:
      - Create branch `{tag}/{task_name}-<issue_number_list>` from `origin/main`
      - Tag comes from task.tag (feat, bugfix, refactor, etc.)
      - Issue number list formatted as `120-231-232`
      - Use `git rebase` or `git cherry-pick` to migrate commits to this branch (NEVER git merge)
  - Step 3: Push branch to remote via `git push -u origin <branch>`
  - Updates state file (mark issue as finished, recalculate task status)
- **Dependencies**: review-gate must pass first, commit-commands:commit (external)

### Step 4.3: Create pr-create skill
- **File**: `skills/pr-create/SKILL.md`
- **What it does**:
  - Checks for `PULL_REQUEST_TEMPLATE` in `.github/` directory (various naming conventions)
  - If template found, uses it to structure the PR body
  - Creates PR via `gh pr create --title "..." --body "..."`
  - Title format: `{tag}: {task_name} (#issue_list)`
  - Body includes: task description, resolved issues list, commit summary
  - Returns PR URL
- **Dependencies**: ship (branch must be pushed first)

### Step 4.4: Create pr-feedback skill
- **File**: `skills/pr-feedback/SKILL.md`
- **What it does**:
  - Fetches PR review comments via `gh api repos/owner/repo/pulls/<number>/comments`
  - Also fetches PR reviews via `gh api repos/owner/repo/pulls/<number>/reviews`
  - Presents feedback to user in organized format (by file, by reviewer)
  - For each piece of feedback, asks user how to address it
  - Guides user back through: development -> review-gate -> ship cycle
  - This is the inner loop (steps 2,3,4 from the spec) until PR is approved
- **Dependencies**: pr-create (PR must exist)

## Phase 5: Hook & Cleanup

### Step 5.1: Create daily-inspection hook
- **File**: `hooks/hooks.json`
- **What it does**:
  - SessionStart prompt-based hook
  - Triggers the full inspection chain: state-sync -> issue-triage -> issue-inspect -> task-inspect -> project-inspect
  - Uses a prompt that instructs Claude to run each skill in sequence
- **Configuration**:
  ```json
  {
    "SessionStart": [{
      "hooks": [{
        "type": "prompt",
        "prompt": "Run the teamdev daily inspection: first sync state, then triage new issues, inspect tracked issues, inspect tasks, and inspect projects. Use the teamdev skills in this order: state-sync, issue-triage, issue-inspect, task-inspect, project-inspect."
      }]
    }]
  }
  ```

### Step 5.2: Clean up placeholder files
- Remove empty placeholder files: `commands/help.md`, `commands/setup.md`, `commands/new-project.md`, `commands/new-task.md`, `commands/project-status.md`, `commands/task-status.md`
- Remove `commands/` directory entirely (no commands in this plugin)
- Update README.md with plugin usage documentation

## Implementation Order

```
Phase 1 (Foundation)     Phase 2 (Inspection)     Phase 3 (Dev Flow)     Phase 4 (Review & Ship)     Phase 5
─────────────────────    ────────────────────     ──────────────────     ───────────────────────     ────────
1.1 plugin.json          2.1 issue-triage         3.1 project-setup     4.1 review-gate             5.1 hook
1.2 state-sync       →   2.2 issue-inspect     →  3.2 issue-pick     →  4.2 ship                →   5.2 cleanup
1.3 status               2.3 task-inspect                                4.3 pr-create
                          2.4 project-inspect                            4.4 pr-feedback
```

**Parallelization opportunities**:
- Within Phase 1: state-sync and status can be written in parallel
- Within Phase 2: All 4 inspection skills can be written in parallel (they reference each other but are separate files)
- Within Phase 3: project-setup and issue-pick can be written in parallel
- Within Phase 4: review-gate, ship, pr-create, pr-feedback can be written in parallel (separate files, cross-references only)
- Phase 5 must be last

**Total files to create/modify**: 14 (12 SKILL.md files + 1 hooks.json + cleanup)
