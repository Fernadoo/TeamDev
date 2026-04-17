I'd like to make this plugin mainly for git-repo based teamwork development, by consolidating the following paradigm.

One's dev work usually looks like: (here we only show task status, but actually there should also be issue status, and project status)
- project 1
    - task 1: status: ongoing
        - issue #120
        - issue #231
    - task 2: status: finished
        - issue #22
- project 2
    - task 1: status: ongoing
        - issue #232
        - issue #110
        - issue #135
- project 3
    - task 1: status: stale
        - issue #120
        - issue #231

Each task is a collection of related issues. The issue here is the smallest unit of work, and we equal it to a GitHub issue. A project is a collection of related tasks, and we equal it to a Git repo, e.g., github, gitlab, etc.

project status := ongoing | finished | stale (after being finished for a long enough time)
task status := ongoing | finished | stale (after being finished for a long enough time)
issue status := ongoing | finished

A daily routine:
1. inspections before starting development -> 
2. development ->
3. code review ->
4. commit & push ->
5. creating PR and receiving PR review feedback from colleagues ->
6. addressing PR review feedback -> *(inner loop over steps 2,3,4 until the PR is approved ->)*
7. **PR merged!**

## 1. before starting development:
1. issue insepction:
    1.1. see if there is any new issues assigned to me,
        - if any, use a double-phase review to validate whether the issue is really reproducible, and whether the proposed solution is reasonable, 
            - use `claude-sonnet-4-6` for a self-review
            - use `codex:adversarial-review` for an adversarial review
          if the issue is not valid, then label the issue as *wontfix* but do not close it yet (it should be closed by the repo owner).
          if the issue is valid, then go through the following two steps.
        - if any valid issues, see if this issue can be merged into an existing task; if not, create a new task for it,
    1.2. see if there is any update on the issues I am working on, e.g., new comment, new parent/sub issues, new commit, etc. If any, update the issue status accordingly, 
        - if there is a new comment, then the issue is ongoing,
        - if there is a new parent/sub issue, then the issue is ongoing, and the new parent/sub issue is also ongoing, and should be merged into the same task,
        - if there is a new commit that claims to `resolve` or `close` the issue, then the issue is finished, etc.
3. task inspection:
    3.1. if there is any ongoing task, see if there is any update on the issues in this task, if there is any update, update the task status accordingly, with similar rules as issue status update.
    3.2. if there is any finished task, see if it has been finished for a long enough time, if yes, then mark it as stale.
    3.3. if there is any stale task, use `AskUserQuestion` to ask the user if they want to delete this task.
4. project inspection:
    - similar rules as task inspection.
    - users can always create a new project by providing the project name and the git repo url, and the plugin will automatically fetch the existing tasks and issues from the git repo, and update the project/task/issue status accordingly.

## 2. development:
1. pick an ongoing issue within an ongoing task. Better use `AskUserQuestion` to let the user specify the issue.

## 3. code review:
- use `claude-sonnet-4-6` for a self-review, and use `codex:adversarial-review` for an adversarial review, to review the code changes before committing.
- if the code review fails, then go back to development step, and repeat the code review until it passes.

## 4. commit & push:
after the two-phase code review passes,
1. for this particular issue that is resolved, make a coauthoring commit using `/commit-commands:commit`
2. if the parent task to which this issue belongs is also finished, then make a coauthoring commit for the parent task using `/commit-commands:commit`. 
    - if so, checkout a new branch for this task based on the latest `origin/main` branch, under the name as `{tag}/{task_name}-<issue_number_list>`. The tag is used to indicate the type of the task, e.g., `feat`, `bugfix`, `refactor`, etc. The issue number list is used to indicate which issues are resolved in this task, e.g., `120-231-232`. Use either `git rebase` or `git cherry-pick` to migrate the commits to this new branch. **MUST not use git merge, which may lead to less readable commit histories**
3. push the branch to the remote repo.

## 5. creating PR and receiving PR review feedback from colleagues:
1. before creating a PR, check if there is any `PULL_REQUEST_TEMPLATE`, which is usually under the `.github` folder with similar file names.
2. if any, then use the template to create the PR.
3. after receiving PR review feedback from colleagues, fetch the feedback which is usually in the form of comments.


Now, to achieve the above paradigm, tell me what is your idea to implement those possibly involved `skills` (and maybe `agents`),
