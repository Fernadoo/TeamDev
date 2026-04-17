---
name: review-gate
description: >
  This skill should be used when the user wants to run a two-phase code review
  before committing changes. It orchestrates a self-review by Sonnet followed by
  an adversarial review via Codex, and only signals readiness to ship when both
  phases pass. This skill should be triggered when the user says "review",
  "review gate", "check my code", "run review", "pre-commit review", or any
  variation indicating they want their changes validated before committing.
---

# Review Gate -- Two-Phase Pre-Commit Review

Orchestrate a rigorous two-phase code review pipeline that must pass before any
code is committed. Phase 1 is a self-review performed by a Sonnet agent.
Phase 2 is an adversarial review performed by the Codex adversarial-review
skill. Both phases must pass for the code to be declared shippable.

---

## Overview

Run two independent review phases against the current staged and unstaged
changes in the working tree. Collect verdicts from both phases. If either phase
returns a failing verdict, report the specific issues back to the user and
instruct them to return to development to address the problems. If both phases
pass, signal that the code is ready to ship and guide the user toward the
`ship` skill.

This gate exists to catch issues early -- before a commit is created -- so that
every commit in the repository represents code that has survived both an
analytical self-review and a deliberately adversarial second opinion.

---

## Scripts

Deterministic git operations are implemented as scripts in `${CLAUDE_PLUGIN_ROOT}/skills/review-gate/scripts/`.

### gather_diffs.sh

Collects all diff information needed for review: staged diff, unstaged diff, changed file lists, and diff stats.

```
bash "${CLAUDE_PLUGIN_ROOT}/skills/review-gate/scripts/gather_diffs.sh" --format json
```

**Formats**:
- `--format json` (default): Outputs a JSON object with all diff data
- `--format text`: Outputs labeled text sections

**JSON output fields**:
- `staged_diff`: Full staged diff text (or null)
- `unstaged_diff`: Full unstaged diff text (or null)
- `changed_files_unstaged`: Newline-separated file list (or null)
- `changed_files_staged`: Newline-separated file list (or null)
- `stat_unstaged`: Diff stat summary (or null)
- `stat_staged`: Diff stat summary (or null)
- `combined_diff`: Both diffs concatenated with section headers, ready to pass to reviewers
- `total_diff_lines`: Total line count across both diffs
- `is_large_diff`: Boolean, true if total_diff_lines > 2000
- `has_changes`: Always true (script exits 1 if no changes)

**Exit codes**: 0 success, 1 no changes detected, 2 not a git repository.

---

## Step-by-Step Procedure

### Step 1: Gather Diffs

Run the diff collection script:

```
bash "${CLAUDE_PLUGIN_ROOT}/skills/review-gate/scripts/gather_diffs.sh" --format json
```

Parse the JSON output.

- If exit code is 1: inform the user there are no changes to review. Suggest staging changes or verifying the correct repository/branch. Stop execution.
- If exit code is 2: inform the user this is not a git repository. Stop execution.
- If `is_large_diff` is true: warn the user that the diff is large (report `total_diff_lines`) and that review quality may be reduced. Suggest breaking changes into smaller reviews. Proceed regardless.

The `combined_diff` field contains the complete diff payload to pass to both review phases.

### Step 2: Phase 1 -- Self-Review (Sonnet)

Spawn a subagent with the following characteristics:

- **Model**: `sonnet` (i.e., `claude-sonnet-4-6`)
- **Task**: Review the `combined_diff` for correctness, security vulnerabilities, style issues, and logic errors.

Provide the agent with the `combined_diff` from Step 1 and instruct it to evaluate across these dimensions:

1. **Correctness** -- Verify logic is sound. Look for off-by-one errors, incorrect conditionals, missing null/undefined checks, wrong variable references, broken control flow, and behavior that diverges from intent.

2. **Security** -- Scan for: SQL injection, XSS, path traversal, hardcoded secrets/credentials, insecure crypto, unsafe deserialization, SSRF vectors, improper input validation.

3. **Style and Consistency** -- Check that changes follow conventions visible in surrounding code. Flag inconsistent naming, unusual formatting, missing/misleading comments, non-idiomatic patterns.

4. **Logic Errors** -- Identify race conditions, deadlocks, resource leaks, unreachable code, redundant checks, infinite loops, logical contradictions with existing codebase.

The Sonnet agent must return a structured verdict:

- **Status**: `pass` or `fail`
- **Issues**: A list of specific issues found, each with:
  - File path and line range
  - Category (correctness, security, style, logic)
  - Severity (critical, warning, suggestion)
  - Description of the problem
  - Suggested fix or remediation

Store this verdict for the final decision step.

### Step 3: Phase 2 -- Adversarial Review (Codex)

Invoke the `codex:adversarial-review` skill. Pass it the same `combined_diff` from Step 1 so both reviewers examine identical changes.

The adversarial review probes:

- **Edge cases and boundary conditions**: Empty inputs, nil values, max-length strings, zero-element collections, negative numbers, concurrent access.
- **Assumption violations**: Non-null assumptions, non-empty lists, service availability across all execution paths.
- **Error propagation**: Silent failures, swallowed exceptions, unchecked error codes.
- **Regression risk**: Impact on existing callers or dependents of modified code.
- **Architectural concerns**: Tight coupling, separation of concerns violations, hidden dependencies.

Collect the adversarial verdict (same structure: pass/fail + findings). Store alongside the Sonnet verdict.

### Step 4: Decision Logic

Apply the decision matrix:

| Sonnet Verdict | Adversarial Verdict | Outcome              |
|----------------|---------------------|----------------------|
| pass           | pass                | Ready to ship        |
| pass           | fail                | Not ready -- fix     |
| fail           | pass                | Not ready -- fix     |
| fail           | fail                | Not ready -- fix     |

Both phases must pass. There is no override, no "soft pass," and no mechanism to skip a failing phase.

**When both phases pass**:
- State that both the self-review and adversarial review passed.
- Include any non-blocking suggestions (severity "suggestion") from either reviewer.
- Indicate the code is ready to ship.
- Guide the user to proceed with the `ship` skill.

**When either phase fails**:
- Clearly identify which phase(s) failed.
- List every issue, grouped by phase then by severity (critical first, then warnings, then suggestions).
- For each issue: file path, line range, category, description, suggested fix.
- Instruct the user to return to development to address the issues.
- After fixes, the user should invoke `review-gate` again to re-run both phases from scratch.

Do not attempt to auto-fix issues. This skill is review and reporting only.

---

## Error Handling

### Agent Spawn Failure

If the Sonnet agent fails to spawn or returns an error instead of a verdict, report the error. Do not fall back to single-phase review. Both phases are required.

### Adversarial Skill Unavailable

If `codex:adversarial-review` cannot be invoked, report this to the user. Do not treat a missing adversarial review as a pass. Both phases are mandatory.

### Conflicting Verdicts Between Phases

If Phase 1 passes but Phase 2 fails (or vice versa), this is normal and expected. Report both verdicts faithfully. Do not reconcile or dismiss findings from one phase based on the other.

---

## Integration with the Development Workflow

The review gate sits between development and shipping:

```
develop -> review-gate -> ship -> pr-create -> pr-feedback -> develop (loop)
```

Invoke `review-gate` after making changes and before running `ship`. If the gate fails, loop back to development. If it passes, proceed to `ship`.

The review gate does not modify the state file (`${CLAUDE_PLUGIN_ROOT}/teamdev-state.json`). It is a pure validation step with no side effects on project state.
