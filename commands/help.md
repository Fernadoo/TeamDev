---
name: help
description: Display all available teamdev plugin commands and skills
---

# Teamdev Plugin Help

Display a structured overview of all available teamdev components.

## Commands

| Command | Purpose |
|---------|---------|
| `/teamdev:help` | Show this help message |
| `/teamdev:setup` | Initialize the plugin — verify `gh` auth, create state file |

## Skills

### Inspection Chain (daily routine)

| Skill | Purpose |
|-------|---------|
| `teamdev:state-sync` | Sync local `teamdev-state.json` with GitHub issue states |
| `teamdev:issue-triage` | Discover new assigned issues, validate with double-phase review, assign to tasks |
| `teamdev:issue-inspect` | Check tracked issues for new comments, closures, cross-references |
| `teamdev:task-inspect` | Recalculate task statuses from child issues, flag stale tasks (>7 days) |
| `teamdev:project-inspect` | Recalculate project statuses from child tasks, flag stale projects (>7 days) |

### Development Flow

| Skill | Purpose |
|-------|---------|
| `teamdev:project-setup` | Create a new project from a GitHub repo URL, fetch issues, group into tasks |
| `teamdev:issue-pick` | Present ongoing issues and let the user select one to work on |
| `teamdev:status` | Display formatted tree of all projects, tasks, and issues with statuses |

### Review & Ship Pipeline

| Skill | Purpose |
|-------|---------|
| `teamdev:review-gate` | Two-phase code review: Sonnet self-review + codex adversarial-review |
| `teamdev:ship` | Commit, create task branch, migrate commits (rebase/cherry-pick), push |
| `teamdev:pr-create` | Find PR template, create pull request with proper formatting |
| `teamdev:pr-feedback` | Fetch PR review comments, guide the address-feedback inner loop |

## Hook

A **SessionStart** hook automatically runs the full inspection chain on every new session:
`state-sync` → `issue-triage` → `issue-inspect` → `task-inspect` → `project-inspect` → `status`

## Typical Workflow

1. Start a session (hook runs inspection automatically)
2. Run `teamdev:issue-pick` to select an issue
3. Develop the fix
4. Run `teamdev:review-gate` for two-phase code review
5. Run `teamdev:ship` to commit, branch, and push
6. Run `teamdev:pr-create` to open a pull request
7. Run `teamdev:pr-feedback` to fetch and address reviewer comments
8. Repeat steps 3-7 until the PR is approved and merged
