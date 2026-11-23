# Testing and delivery workflow

## What takes time

RIQ-01's GitHub PR run 45102113022 measured 59 seconds for backend, 29 seconds
for frontend, and 90 seconds for browser, including job setup/build/cleanup.
These jobs run concurrently, so their durations should not be added together.
Queue time and checking for completion can add user-visible delay.

The local SQLite suite took about 1.5 seconds and PostgreSQL about 10 seconds,
including the populated migration test. Image builds, dependency downloads,
Docker startup, and full-stack browser setup account for additional time. These
are observations from one run, not performance guarantees. Backend checks now
print elapsed time for each command, including failures.

## Edit loop

1. Read the issue, acceptance criteria, and affected code. Work on a feature branch.
2. Run the relevant tests while editing. Reuse the Linux check image and mount
   current backend source to avoid rebuilding for each source-only change:

   ```powershell
   docker run --rm --mount "type=bind,source=${PWD}/backend,target=/app,readonly" rosteriq-checks python -m pytest tests/test_identities.py -q -p no:cacheprovider
   ```

   Run from the repository root. On Linux/macOS replace `${PWD}` with `$(pwd)`.
   This is a fast SQLite check, not PostgreSQL or migration validation. Build
   `rosteriq-checks` first using README instructions. Rebuild whenever dependency
   manifests, Python version, or Docker configuration change. The source mount
   covers `/app`; it does not update installed dependencies.
3. Run Ruff against changed Python files. A prose-only change needs link/content
   review, not a repeated local database or browser suite.

## Before publishing

Run the README's full backend Linux check command once for the final backend
implementation. It includes SQLite, PostgreSQL, schema drift, and migration
round trips. Schema/data changes must include populated migration evidence.
Use only the disposable `rosteriq-checks` database; never run downgrade tests on
the development volume.

For frontend changes, run frontend checks. For UI/API integration or proxy changes,
run browser checks. After a passing final check, repeat only affected checks when
code changes, a failure occurs, or a specific concern remains. Do not rerun unchanged
tests just to wait for CI.

Commit, push, and open/update the PR with scope, test results, and limitations.
GitHub runs all three jobs for PRs and pushes to main. Feature-branch pushes no
longer trigger a duplicate workflow alongside the PR event. Branches without a PR
have no automatic run; open a draft PR for early remote validation. Manual dispatch
is also available once the workflow is on the default branch. Superseded runs for
the same PR/ref are cancelled. Review Files changed and Checks before merging.

## Current optimizations and next measurements

- Backend BuildKit pip cache mounts reuse downloads on the same builder, even
  when source changes invalidate an image layer. The first cache-populating build
  is still cold. Cache files are not copied into runtime images.
- Existing frontend layers already install dependencies before copying source.
- GitHub jobs remain parallel and retain all test coverage. Local pip caches do
  not automatically persist between fresh GitHub runners.
- Record cold versus warm build time before adding cross-run CI image caches or
  changing dependency-layer layout. A cache hit is not a reproducible dependency
  lock; a backend lockfile remains separate work.
- Consider selective CI jobs only if measured cost justifies the complexity;
  preserve stable required-check behavior and coverage for shared configuration.

References: [Docker cache guidance](https://docs.docker.com/build/cache/optimize/),
[GitHub workflow/concurrency syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
