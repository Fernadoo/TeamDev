---
name: pr-feedback
description: >
  This skill should be used when the user wants to fetch and act on pull request
  review comments. It retrieves all review feedback from a PR, organizes it by
  file and reviewer, presents it to the user, and guides them through an inner
  feedback loop of fix-review-ship iterations until the PR is approved. This
  skill should be triggered when the user says "pr feedback", "check PR reviews",
  "handle PR comments", "address review feedback", "pr-feedback", or any
  variation indicating they want to process pull request review comments.
---

# PR Feedback — Fetch Reviews, Present Feedback, Guide the Fix Loop

Fetch all review comments and review verdicts from the current pull request,
organize and present them to the user in a structured format, guide the user
through addressing each piece of actionable feedback, and orchestrate the
inner feedback loop (fix, review-gate, ship) until the PR is approved.

---

## Overview

The pr-feedback skill closes the development loop by connecting PR reviews
back to the development workflow. It handles five responsibilities:

1. Identify the current PR from user input or the current branch.
2. Fetch all review feedback.
3. Present feedback organized by file, reviewer, and blocking status.
4. Walk through each actionable item with the user.
5. Guide the user through repeated fix-review-ship cycles until approval.

---

## Step 1 — Identify the Current PR

### From User Input

If the user provides a PR number or URL directly, extract the PR number.

### From Current Branch

If the user does not specify a PR, detect it automatically:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/pr-feedback/scripts/detect-pr.sh
```

This script outputs JSON:
```json
{
  "number": 42,
  "url": "https://github.com/org/repo/pull/42",
  "head": "feat/add-auth-120-231",
  "state": "OPEN",
  "owner": "org",
  "repo": "repo"
}
```

**Exit code 1** means no PR was found for the current branch. Ask the user
to provide a PR number or URL explicitly, or switch to the correct branch.

Save the `owner`, `repo`, and `number` values for use in Step 2.

---

## Step 2 — Fetch Review Feedback

Run the feedback fetcher with the PR details from Step 1:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/pr-feedback/scripts/fetch-feedback.sh <owner> <repo> <pr_number>
```

This script fetches all three categories of feedback in parallel:
- **Inline comments**: review comments attached to specific lines of code
- **Reviews**: review verdicts (APPROVED, CHANGES_REQUESTED, COMMENTED)
- **General comments**: discussion comments on the PR conversation thread

The script outputs combined JSON to stdout with keys: `inline_comments`,
`reviews`, `general_comments`.

Save the output for formatting in Step 3.

---

## Step 3 — Present Feedback

Pipe the feedback JSON into the formatter:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/pr-feedback/scripts/fetch-feedback.sh <owner> <repo> <number> | \
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-feedback/scripts/format-feedback.py
```

**stdout** contains a structured markdown report with:
- Review verdicts table (reviewer, verdict, summary)
- Blocking status indicator (CHANGES REQUESTED / APPROVED / PENDING)
- Inline comments grouped by file path, sorted by line number
- General conversation comments

**stderr** contains a machine-readable JSON summary:
```json
{
  "has_blocking": true,
  "reviewers": [{"login": "...", "state": "...", "summary": "..."}],
  "files_with_comments": ["src/auth/login.ts", "src/utils/validate.ts"],
  "actionable_count": 5,
  "total_comments": 12
}
```

Present the markdown report to the user. Use the JSON summary to understand
the overall status and prioritize blocking feedback.

### Handling No Feedback

If `actionable_count` is 0 and no reviews exist, inform the user that no
feedback has been received yet. Suggest requesting reviews from specific
team members or checking back later.

---

## Step 4 — Address Each Feedback Item

### Walking Through Actionable Items

For each inline comment that suggests changes (especially from reviewers who
requested changes), present it to the user one at a time:

- The file path and line number
- The reviewer and their comment
- The relevant code context (read the file at the specified line range)

Ask the user how they want to address each item:

- **Fix it** — The user agrees and will make the change. Note the required
  fix for the development phase.
- **Discuss** — The user wants to reply to the reviewer. Help compose a
  response and post it:
  - For inline comment replies:
    ```
    gh api repos/{owner}/{repo}/pulls/{number}/comments \
      --method POST \
      --field body="{reply}" \
      --field in_reply_to={comment_id}
    ```
  - For general PR replies:
    ```
    gh pr comment {number} --body "{reply}"
    ```
- **Skip** — Acknowledged but not acting on it now. Note as deferred.

Collect decisions for all actionable items before starting fixes. This
avoids context-switching between reviewing and coding.

---

## Step 5 — Guide the Inner Feedback Loop

After the user has reviewed all feedback and decided how to address each
item, guide them through the iterative fix cycle.

### The Inner Loop

```
pr-feedback -> develop (fix) -> review-gate -> ship -> check status
     ^                                                      |
     |______________________________________________________|
     (if not approved, fetch new feedback and repeat)
```

### Phase: Development

Guide the user to make the fixes they agreed to in Step 4. For each fix,
remind them of the file, line, feedback, and agreed action. Do not make
fixes automatically — the user drives development.

### Phase: Review Gate

After fixes are made, instruct the user to run `review-gate` to validate
changes. If the gate fails, additional development is needed before
proceeding.

### Phase: Ship

Once the review gate passes, instruct the user to run `ship` to commit and
push. Since the branch and PR already exist, ship will push to the existing
branch (updating the PR automatically).

### Phase: Check PR Status

After pushing, check the approval status:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/pr-feedback/scripts/check-pr-status.sh <pr_number>
```

Outputs JSON:
```json
{"review_decision": "APPROVED", "approved": true}
```

**Exit codes:**
- `0` — PR is approved. Inform the user the PR is ready to merge. Suggest
  `gh pr merge <number>`.
- `1` — Not approved. `review_decision` indicates whether it is
  `CHANGES_REQUESTED` (loop back to Step 2 for fresh feedback) or
  `REVIEW_REQUIRED` (suggest waiting for reviewers).
- `2` — Error fetching status.

### Loop Termination

The inner loop terminates when:
- The PR reaches `APPROVED` status, OR
- The user explicitly decides to stop (e.g., waiting for async reviews), OR
- The PR is merged or closed externally

---

## Error Handling

### PR Not Found

If `detect-pr.sh` exits with code 1, ask the user for the PR number
directly or to switch to the correct branch.

### API Rate Limiting

If GitHub API calls fail due to rate limiting, report the status and suggest
waiting. Use `gh api rate_limit` to check remaining requests.

### Authentication Issues

If `gh` commands fail due to authentication, instruct the user to run
`gh auth login`.

### Empty Feedback

No reviews or comments is not an error. Inform the user and suggest
requesting reviews or waiting.

---

## Integration with the Development Workflow

The pr-feedback skill is the final skill in the main workflow and the entry
point for the iterative feedback loop:

```
develop -> review-gate -> ship -> pr-create -> pr-feedback -> develop (loop)
```

This skill does not modify `${CLAUDE_PLUGIN_ROOT}/teamdev-state.json` directly. State updates are
handled by the `ship` skill during each feedback iteration.

---

## Summary of Actions

1. Run `detect-pr.sh` to identify the current PR (or use user-provided number).
2. Run `fetch-feedback.sh` to retrieve all review feedback.
3. Pipe feedback into `format-feedback.py` for structured presentation.
4. Present the markdown report; use JSON summary for prioritization.
5. Walk through each actionable item, asking: fix, discuss, or skip.
6. Post replies via `gh api` or `gh pr comment` where requested.
7. Guide the inner loop: develop fixes, review-gate, ship, check status.
8. Run `check-pr-status.sh` after each push to determine if approved.
9. Repeat until approved or user exits the loop.
