# Working on RosterIQ

## Review a task

Open [Issues](https://github.com/eric99r/RosterIQ/issues), then check the outcome,
acceptance checklist, and dependencies. Update the issue if the scope needs to
change. Ready means work can begin; planned tasks require their dependencies first.
RIQ-17 needs league settings and access details before it can be completed.

Keep credentials and private league exports out of public issues and commits.
Use synthetic fixtures for tests. Do not infer scoring rules from platform or
league size; incomplete configuration should remain explicit.

## Implement and review

1. Start from current `main` on a feature branch, for example `feat/riq-01-identities`.
2. Read the issue, relevant code, README, and research notes. Keep changes within
   the issue's acceptance criteria and preserve existing IDs and development data.
3. Run the applicable Linux checks documented in README. Database-changing tasks
   need migration checks against disposable data. If the execution environment
   cannot run Docker, report that limitation and use GitHub Actions for container
   validation; do not claim unrun checks passed.
4. Open a pull request explaining the behavior change and validation results.
   Include `Closes #1` (using the actual issue number) to link the issue.
5. Review the PR's **Files changed** and **Checks**, compare against the acceptance
   checklist, and request changes if needed. Merge only after review and passing
   checks. GitHub closes the linked issue when the PR merges into the default branch.

## Starting a Codex task remotely

An issue is a specification; creating one does not automatically start Codex.
Configure access to this repository and an execution environment before using it
from mobile. Cloud tasks use their own checkout and do not inherit your local
PostgreSQL volume, uncommitted edits, `.env`, or certificates.

Example instruction:

> Work on eric99r/RosterIQ issue #1. Read its acceptance criteria and dependencies.
> Start from current main on a feature branch. Preserve existing IDs and data.
> Run the applicable checks in README, report any environment limitations, and
> open a PR with Closes #1. Do not merge. Explain the major Python design decisions.

See [Codex Cloud setup](https://help.openai.com/en/articles/20001545-using-codex-cloud)
for current account, repository, and environment requirements.
