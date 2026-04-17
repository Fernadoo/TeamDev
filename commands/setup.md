---
name: setup
description: Initialize the teamdev plugin — verify GitHub CLI auth, create state file, and optionally set up the first project
---

# Teamdev Setup

Initialize the teamdev plugin for the current environment.

## Step 1: Verify GitHub CLI

Check that `gh` is installed and authenticated:

```
gh auth status
```

If not authenticated, inform the user to run `gh auth login` and stop. Do not proceed without valid auth — all teamdev skills depend on `gh`.

## Step 2: Initialize State File

Check if `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` exists.

- If it exists: read it and display a summary of existing projects/tasks/issues using `teamdev:status`.
- If it does not exist: create it with the initial empty structure:

```json
{
  "projects": []
}
```

Confirm the file was created successfully.

## Step 3: Offer First Project Setup

Use AskUserQuestion to ask the user if they want to set up their first project now.

- If yes: invoke the `teamdev:project-setup` skill to walk through project creation (repo URL, fetch issues, group into tasks).
- If no: inform the user they can run `teamdev:project-setup` anytime later.

## Step 4: Confirm Setup Complete

Display a summary:
- GitHub CLI: authenticated as `<username>`
- State file: `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` (new / existing with N projects)
- SessionStart hook: active (daily inspection will run on next session start)

Inform the user the plugin is ready. Mention they can run `/teamdev:help` to see all available commands and skills.
