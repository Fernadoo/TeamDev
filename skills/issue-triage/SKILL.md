---
name: issue-triage
description: "This skill should be used when the user wants to discover new GitHub issues assigned to them, validate those issues through a double-phase review process, and either label them as wontfix or assign them to existing or new tasks in the teamdev state. This skill should be triggered when the user mentions triaging issues, checking for new assignments, reviewing incoming issues, or wants to process unhandled GitHub issues across their tracked projects."
---

# Issue Triage

Discover new GitHub issues assigned to the current user across all tracked project repositories, validate each issue through a structured double-phase review, and either reject invalid issues by labeling them `wontfix` or integrate valid issues into the task tracking state.

## Prerequisites

Verify the following before proceeding:

1. Confirm the state file `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` exists in the current working directory. If absent, notify the user that no projects are tracked and abort.
2. Read and parse the state file to extract the list of projects and their associated repositories.
3. Ensure the `gh` CLI is authenticated and functional by running `gh auth status`.

## Phase 1: Fetch Assigned Issues

For each ongoing project in the state file, run the fetch script:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/scripts/fetch_assigned_issues.sh <owner/repo>
```

The script outputs a JSON array of issues assigned to `@me` on stdout. If it exits non-zero, the repo fetch failed -- record the failure, log the stderr message, and continue with remaining projects.

After fetching, tag each returned issue object with `"project_name"` and `"repo"` fields corresponding to the originating project, then merge all results into a single JSON array.

Present the user with a note about which repositories were successfully queried and which were not.

## Phase 2: Identify New Issues

Pipe the merged issue array (with `project_name` and `repo` fields) into the comparison script:

```bash
echo '<merged_issues_json>' | python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/scripts/find_new_issues.py ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json
```

The script outputs a JSON array of only the new (untracked) issues on stdout.

If the output is an empty array, inform the user that all assigned issues are already tracked and terminate gracefully.

If new issues are found, present a brief summary listing each new issue's number, title, and originating project/repo before proceeding to validation.

## Phase 3: Double-Phase Validation

For each new issue, perform a two-stage validation process. Process issues one at a time and present progress indicators (e.g., "Validating issue 3 of 7").

### Stage A: Self-Review via Sonnet

Invoke the Agent tool with `model: "sonnet"` (claude-sonnet-4-6) to perform an analytical self-review of the issue. Provide the agent with the full issue body, title, labels, and the repository name for context. The agent should also receive the project name and task context from the state so it can assess relevance to the project's scope. Instruct the agent to evaluate:

1. **Reproducibility**: Based on the information provided, is the issue likely reproducible? Does it include sufficient steps, environment details, or evidence?
2. **Clarity**: Is the issue clearly written with an identifiable problem statement and expected behavior?
3. **Scope**: Is the issue reasonably scoped, or does it conflate multiple unrelated problems?
4. **Proposed solution feasibility**: If the issue suggests a fix or approach, is that approach technically reasonable given the repository context?

The agent must return a structured verdict: `VERDICT: valid` or `VERDICT: invalid`, followed by a 2-3 sentence justification.

### Stage B: Adversarial Review via Codex

Invoke the `codex:adversarial-review` skill (via the Skill tool), passing the issue title, body, labels, repository context, and the self-review verdict from Stage A. Capture both the verdict and the full reasoning text.

### Combining Verdicts

- If **both** reviews return `valid`, the issue is **valid**.
- If **both** reviews return `invalid`, the issue is **invalid**.
- If the reviews **disagree**, treat as **ambiguous**. Present the conflicting reasoning to the user via `AskUserQuestion` and let them make the final call.

## Phase 4: Handle Invalid Issues

For each invalid issue, run the labeling script:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/scripts/label_wontfix.sh <issue_number> <owner/repo>
```

The script handles label creation if the `wontfix` label does not yet exist on the repository. Do **not** close the issue.

Log the action taken for the user's reference, including the issue number, title, repository, and the reasoning from both validation phases.

## Phase 5: Integrate Valid Issues into State

For each valid issue, use `AskUserQuestion` to determine where it belongs:

1. **Merge into an existing task**: Display a numbered list of all ongoing tasks across the issue's parent project, showing each task's name, tag, and current issue count. Allow the user to select one by number.
2. **Create a new task**: Prompt the user for a task name and tag.

### Adding to an existing task

Construct the issue JSON object and run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/scripts/add_issue_to_task.py \
  ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json "<project_name>" "<task_name>" '<issue_json>'
```

Where `<issue_json>` is:
```json
{"number": <N>, "title": "<title>", "status": "ongoing", "last_activity": "<current_ISO_8601>"}
```

The script outputs the full updated state JSON on stdout. Write it to `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`.

### Creating a new task

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/scripts/create_task_entry.py \
  ${CLAUDE_PLUGIN_ROOT}/teamdev-state.json "<project_name>" "<task_name>" "<tag>" '<issue_json>'
```

The script creates the task with `status: "ongoing"`, current timestamp, and the issue appended. It outputs the full updated state JSON on stdout. Write it to `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`.

## Phase 6: Update State File

The `add_issue_to_task.py` and `create_task_entry.py` scripts automatically propagate `last_activity` timestamps to both the task and project levels. Write the script output to `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` using the Write tool with proper formatting after each integration step.

If the user aborts mid-triage, the state file already reflects all previously processed issues since each integration writes immediately.

## Error Handling

- **GitHub API failures**: If `fetch_assigned_issues.sh` exits non-zero, log the error, skip that repo, continue.
- **State file parse errors**: If the state file contains invalid JSON, notify the user and abort without making changes.
- **Empty projects list**: If no ongoing projects exist in state, inform the user and suggest they add a project first.
- **Label creation failures**: Handled internally by `label_wontfix.sh` (creates label then retries).

## Output Summary

After all processing is complete, present a concise summary:

- Total issues fetched across all repos
- Number of new (previously untracked) issues found
- Number of issues validated as valid and added to tasks
- Number of issues labeled as `wontfix`
- Number of ambiguous issues resolved by user decision
- Any repos that were skipped due to errors

## Important Constraints

- Never close issues automatically. Only label them.
- Never modify issue titles or bodies on GitHub. Only add labels.
- Always ask the user before creating new tasks. Never auto-create tasks without explicit user confirmation.
- Preserve all existing state data. Only append new issues and update timestamps -- never remove or overwrite existing tracked issues.
- Use ISO 8601 format with timezone designator (e.g., `2026-04-16T12:00:00Z`) for all timestamps.
- Process issues one at a time through validation to keep the user informed of progress.
- If the user aborts mid-triage, all state changes made so far are already persisted.
