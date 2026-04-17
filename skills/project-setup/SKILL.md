---
name: project-setup
description: >
  This skill should be used when the user wants to create a new project in the
  teamdev state, set up tracking for a GitHub repository, import existing issues,
  organize issues into tasks, or bootstrap the ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json file for the
  first time. It guides the user through an interactive workflow to configure a
  project with tasks and issues sourced from GitHub.
---

# Project Setup

Create a new project entry in the local teamdev state file by collecting project details from the user, fetching existing GitHub issues, and organizing them into named tasks with tags.

## Overview

Guide the user through an interactive setup flow: gather the project name and GitHub repository, validate the repository exists, fetch issues assigned to the user, present the issues for grouping into logical tasks, and write the fully populated project to `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`. Finish by running state-sync to populate all derived statuses.

## Scripts

All deterministic operations are delegated to scripts in `${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/`:

| Script | Purpose |
|--------|---------|
| `validate-repo.sh` | Validate a GitHub repo exists and is accessible. Takes `owner/repo` as argument, outputs repo JSON to stdout. Validates format and runs `gh repo view`. |
| `fetch-issues.sh` | Fetch all issues assigned to `@me` from a repo. Takes `owner/repo` as argument, outputs JSON array to stdout. |
| `format-issues.py` | Format fetched issues as a numbered list for user presentation. Reads JSON from stdin, outputs formatted list to stdout, index-to-number mapping to stderr. |
| `build-project.py` | Build a project entry and append it to the state file. Reads project config JSON from stdin, validates, constructs the full project hierarchy with computed statuses, and writes to the state file. Outputs a summary to stdout. |

## Step-by-Step Procedure

### 1. Collect Project Information

Ask the user for two pieces of information using **separate prompts**:

**Repository**: The GitHub repository in `owner/repo` format (e.g., `anthropic/claude-code`). If the user provides a full URL like `https://github.com/owner/repo`, extract the `owner/repo` portion.

**Project name**: A short, human-readable identifier. Suggest a default based on the repo name (the part after the slash), but let the user override it. Recommend lowercase with hyphens (e.g., `my-project`).

### 2. Validate the Repository

Run:
```bash
"${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/validate-repo.sh" <owner/repo>
```

- **Success (exit 0)**: The script outputs JSON with the repo name, owner, and description. Display the repo description to the user for confirmation.
- **Failure**: Display the error from the script. If it mentions authentication, suggest `gh auth login`. If it mentions "not found", ask the user to check the repo name. Do not proceed until validation passes.

### 3. Fetch Existing Issues

Run:
```bash
"${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/fetch-issues.sh" <owner/repo>
```

Then format the output for presentation:
```bash
"${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/fetch-issues.sh" <owner/repo> | \
    python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/format-issues.py"
```

The format script outputs a numbered list to stdout (for the user) and an index-to-issue-number mapping to stderr (for your use in the grouping step).

If the script exits with code 1 (no issues) or outputs `NO_ISSUES`, inform the user and offer two options:
1. Continue with an empty project (no tasks, no issues) and add them later.
2. Cancel setup and come back when issues exist.

### 4. Present Issues for Grouping

Display the formatted issue list from `format-issues.py` to the user. Explain that tasks are logical groupings of related issues -- for example, all authentication issues might form one task, while pagination issues form another.

Ask the user to select issues for the first task by entering the list numbers (e.g., "1, 2, 3"). Use the index-to-number mapping from stderr to resolve list numbers to actual GitHub issue numbers.

### 5. Create Tasks Iteratively

For each group of issues the user defines, collect:

**Task name**: A short identifier (e.g., "implement-auth"). Suggest a name based on common themes in the selected issue titles.

**Task tag**: A category label. Present these standard options:
- `feat` -- New feature
- `bugfix` -- Bug fix
- `refactor` -- Code restructuring
- `docs` -- Documentation
- `test` -- Test additions
- `chore` -- Maintenance

After creating one task, show the remaining ungrouped issues and ask if the user wants to create another task. Continue until:
- All issues are assigned, or
- The user indicates they are done

### 6. Handle Ungrouped Issues

If issues remain ungrouped, ask the user whether to:
1. Create a catch-all task (e.g., "miscellaneous") for the remaining issues.
2. Leave them untracked (they stay on GitHub but are not in the local state).

### 7. Build and Write the Project

Construct a JSON config object with all collected information and pipe it to `build-project.py`:

```bash
cat <<'EOF' | python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-setup/scripts/build-project.py" ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
{
  "project_name": "<name>",
  "repo": "<owner/repo>",
  "tasks": [
    {
      "name": "<task-name>",
      "tag": "<tag>",
      "issues": [
        {"number": 120, "title": "...", "state": "OPEN", "updatedAt": "..."}
      ]
    }
  ]
}
EOF
```

The script:
- Checks for duplicate project names (exits 1 with `DUPLICATE_PROJECT:<name>` on stderr if found). If this happens, ask the user to choose a different name.
- Maps GitHub states to local statuses (`OPEN` -> `ongoing`, `CLOSED` -> `finished`)
- Computes `last_activity` timestamps at all levels
- Derives task and project statuses from child entities
- Validates all required fields
- Appends the project to the state file and writes it
- Outputs a summary JSON to stdout with counts

### 8. Run State Sync

After the project is written, run the `state-sync` skill to fully validate and populate all statuses. This ensures consistency and applies staleness detection.

### 9. Display the Result

The summary from `build-project.py` contains the project name, repo, status, task count, issue count, and ongoing/finished breakdowns. Present it to the user:

```
Project "<name>" created successfully!

  Repository: owner/repo
  Tasks: 3
  Issues: 8 (5 ongoing, 3 finished)

  Tasks:
    [feat] implement-auth -- 3 issues
    [bugfix] fix-pagination -- 3 issues
    [refactor] db-connection-pool -- 2 issues
```

## Input Validation Rules

- **Project name**: Non-empty, no filesystem-invalid characters. Recommend lowercase with hyphens.
- **Repository**: Must match `owner/repo` format. `validate-repo.sh` handles format checking. If a full URL is provided, extract `owner/repo` before calling the script.
- **Task name**: Non-empty, unique within the project. Recommend lowercase with hyphens.
- **Tag**: Non-empty. Accept any string but suggest standard values.
- **Issue numbers**: Must correspond to issues in the fetched list. Each issue belongs to exactly one task -- reject duplicates.

## Error Handling

- `gh` not installed: detected early by `validate-repo.sh` or `fetch-issues.sh`. Direct user to install GitHub CLI.
- `gh` not authenticated: detected during repo validation. Direct user to `gh auth login`.
- Corrupted state file: `build-project.py` will report the JSON parse error. Ask user if they want to back up and start fresh.
- Invalid input at any prompt: explain the error and re-prompt. Do not abort the flow for recoverable input errors.
- Write failure: `build-project.py` exits 2 with error details. Report to the user.

## Edge Cases

- Repository with zero assigned issues: allow creating an empty project with no tasks.
- Repository with hundreds of issues: `fetch-issues.sh` uses `--limit 500`. Consider suggesting label-based filtering if the list is overwhelming.
- User wants multiple repos under one project: not supported. Suggest creating separate projects per repo.
- Same issue in two tasks: reject during the grouping step (input validation).
- Re-running for an existing repo: allowed with a different project name. `build-project.py` checks for name uniqueness.
