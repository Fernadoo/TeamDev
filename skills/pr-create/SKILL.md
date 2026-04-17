---
name: pr-create
description: >
  This skill should be used when the user wants to create a pull request for
  a completed task branch. It finds the repository's PR template, builds the
  PR title and body, and creates the PR via the GitHub CLI. This skill should
  be triggered when the user says "create PR", "open PR", "make a pull request",
  "pr-create", or any variation indicating they want to open a pull request for
  their current task branch.
---

# PR Create — Find Template and Open a Pull Request

Locate the repository's pull request template (if one exists), construct a
well-formatted PR title and body from the state file and commit history,
create the pull request via `gh pr create`, and return the PR URL to the user.

---

## Overview

The pr-create skill automates pull request creation for completed task branches.
It performs four steps in sequence:

1. Search for a `PULL_REQUEST_TEMPLATE` file in the repository.
2. Build the PR title and body using data from the state file and git log.
3. Create the PR via the GitHub CLI targeting the main branch.
4. Output the PR URL to the user for reference.

This skill should be invoked after the `ship` skill has created and pushed
a task branch. It requires that the current branch is the task branch that
should become the PR's head.

---

## Step 1 — Find the PR Template

Run the template finder script:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/pr-create/scripts/find-pr-template.sh <repo_root>
```

This script searches standard locations (`.github/`, root, `docs/`) and
outputs JSON:

- **Template found:** `{"found": true, "path": "/path/to/template", "multiple": false}`
- **Multiple templates:** `{"found": true, "paths": [...], "multiple": true}`
- **No template:** `{"found": false}`

**Exit codes:**
- `0` — template(s) found
- `1` — no template found (this is not an error; proceed with default body)

**If multiple templates are found:** Present the list to the user and ask
which one to use via a question prompt. If only one template exists, use it
automatically.

If a template is found, read its contents for use in Step 2.

---

## Step 2 — Build PR Content

### Gather Commit Information

Run the following to collect the commit log:

```
git log --oneline origin/main..HEAD
```

If the output is empty, warn the user that the branch has no commits ahead
of main. Ask the user to confirm before proceeding — a PR with no changes
is likely an error.

### Build the PR Title

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-create/scripts/build-pr-title.py <tag> <task_name> <issue_numbers...>
```

Extract `tag`, `task_name`, and issue numbers from `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` by
reading the state file and finding the task that matches the current branch.

The script outputs a formatted title like: `feat: add auth (#120, #231)`

It automatically truncates to 72 characters if needed.

### Build the PR Body

```
git log --oneline origin/main..HEAD | python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-create/scripts/build-pr-body.py [--template <path>] ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json <issue_number>
```

Arguments:
- `--template <path>` — optional, path to PR template from Step 1
- `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` — the state file path
- `<issue_number>` — any issue number from the task (used to locate the task)

The script reads the commit log from stdin and outputs the PR body markdown
to stdout. If a template is provided, it fills in sections; otherwise it
uses a default structure with Summary, Changes, Resolved Issues (with
`Closes #N` syntax), and Commit Log sections.

**After the script outputs the body**, review it and use your judgment to
improve the Summary and Changes sections. Synthesize the commit messages
into a coherent narrative of what changed and why. The script provides the
structural scaffolding; you provide the editorial quality.

---

## Step 3 — Create the Pull Request

Write the finalized body to a temporary file, then run:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/pr-create/scripts/create-pr.sh "<title>" <body_file> [base_branch]
```

Arguments:
- `title` — the PR title from build-pr-title.py
- `body_file` — path to a file containing the PR body markdown
- `base_branch` — target branch (default: `main`)

The script outputs the PR URL to stdout on success.

**Exit code 1** means `gh pr create` failed. Diagnose the error:
- **Not authenticated**: instruct user to run `gh auth login`
- **Branch not pushed**: run `git push -u origin <branch>` first
- **PR already exists**: report the existing PR URL, ask if user wants to update
- **Repo not found**: verify remote URL and access

---

## Step 4 — Output the PR URL

Present the PR URL to the user. Include:
- The full PR URL
- The PR number
- A note that the PR targets `main`
- A reminder that listed issues will auto-close on merge (due to `Closes #N`)

Guide the user on next steps:
- Wait for CI checks to pass
- Request reviewers if not auto-assigned
- If feedback is received, use the `pr-feedback` skill to process it

---

## Error Handling

### State File Missing

If `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` does not exist, report the error. The state file is
required to construct the PR title and body with accurate task and issue
information.

### Task Not Found

If the current branch name cannot be matched to a task in the state file,
ask the user to identify which task this PR is for. Parse the branch name
to extract the tag and task name as hints.

### GitHub CLI Not Available

If the `gh` command is not installed or not in PATH, instruct the user to
install it (`brew install gh` on macOS, or see
https://cli.github.com/manual/installation) and authenticate with
`gh auth login`.

---

## Integration with the Development Workflow

The pr-create skill sits after ship and before pr-feedback:

```
develop -> review-gate -> ship -> pr-create -> pr-feedback -> develop (loop)
```

This skill does not modify `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`. The state file was already
updated by the `ship` skill.

---

## Summary of Actions

1. Run `find-pr-template.sh` to locate PR template files.
2. If multiple templates found, ask user which to use.
3. Read `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` to extract task name, tag, and issue details.
4. Run `build-pr-title.py` to construct the PR title.
5. Pipe commit log into `build-pr-body.py` to construct the PR body.
6. Review and improve the generated Summary/Changes sections.
7. Write body to temp file, run `create-pr.sh` to create the PR.
8. Present the PR URL and guide user on next steps.
