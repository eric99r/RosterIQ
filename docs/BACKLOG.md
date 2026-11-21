# RosterIQ implementation backlog

Created November 20, 2026. Research and constraints live in
[fantasy analytics notes](research/fantasy-analytics.md). These items are published as
[GitHub issues](https://github.com/eric99r/RosterIQ/issues). Issues are the source of
truth for current status; this document preserves the initial scope and delivery order.

Statuses: **Ready** = can start now; **Planned** = depends on named work;
**Needs input** = requires user configuration/access. Update status and attach check
results when work completes. A task is not complete merely because code is written.

## Existing baseline

MVP 1 includes player create/list/get, literal name search, sport filtering,
pagination, unique provider IDs, health, migrations, repeatable Sleeper NFL import,
React catalog/details, Linux container checks, and live reload. Last verification:
34 backend tests on SQLite and PostgreSQL, 5 frontend tests, migration checks, and
Chromium desktop/mobile smoke tests. The imported local catalog contains 12,197
players; this local data is not included in Git. See [MVP 1 scope](releases/MVP-1.md)
and [GitHub Actions](https://github.com/eric99r/RosterIQ/actions) for remote checks.

No league import, historical game logs, trend engine, or pickup recommendations exist yet.

## Delivery order

| ID | Task | Status | Depends on |
| --- | --- | --- | --- |
| [RIQ-01](https://github.com/eric99r/RosterIQ/issues/1) | Canonical athlete identities and provider mappings | Ready | — |
| [RIQ-02](https://github.com/eric99r/RosterIQ/issues/2) | League-season and fantasy-team profiles | Ready | — |
| [RIQ-03](https://github.com/eric99r/RosterIQ/issues/3) | Import-run history and freshness API | Ready | — |
| [RIQ-04](https://github.com/eric99r/RosterIQ/issues/4) | Validate statistical source coverage | Ready | — |
| [RIQ-05](https://github.com/eric99r/RosterIQ/issues/5) | Manual roster snapshot import | Planned | 01, 02, 03 |
| [RIQ-06](https://github.com/eric99r/RosterIQ/issues/6) | My Teams UI and team selection | Planned | 02, 05 |
| [RIQ-07](https://github.com/eric99r/RosterIQ/issues/7) | Sleeper league synchronization | Planned | 01, 02, 03, 05 |
| [RIQ-08](https://github.com/eric99r/RosterIQ/issues/8) | Yahoo NBA connection and synchronization | Planned | 01, 02, 03, 05; Yahoo setup |
| [RIQ-09](https://github.com/eric99r/RosterIQ/issues/9) | ESPN NFL synchronization and fallback | Planned | 01, 02, 03, 05; access validation |
| [RIQ-10](https://github.com/eric99r/RosterIQ/issues/10) | NBA game-log and schedule ingestion | Planned | 01, 03, 04 |
| [RIQ-11](https://github.com/eric99r/RosterIQ/issues/11) | NFL weekly-stat and schedule ingestion | Planned | 01, 03, 04 |
| [RIQ-12](https://github.com/eric99r/RosterIQ/issues/12) | Historical summaries and scoring calculations | Planned | 02, 10, 11 |
| [RIQ-13](https://github.com/eric99r/RosterIQ/issues/13) | Explainable trend calculation and API | Planned | 12 |
| [RIQ-14](https://github.com/eric99r/RosterIQ/issues/14) | Research UI with rising/falling evidence | Planned | 06, 13 |
| [RIQ-15](https://github.com/eric99r/RosterIQ/issues/15) | League-specific add/drop comparison | Planned | 05, 06, 12, 13 |
| [RIQ-16](https://github.com/eric99r/RosterIQ/issues/16) | Trend evaluation and historical validation | Planned | 13; sufficient history |
| [RIQ-17](https://github.com/eric99r/RosterIQ/issues/17) | Complete the user's three league profiles | Needs input | 02; league settings/access |

Recommended first implementation slice: RIQ-01, RIQ-02, RIQ-03, then RIQ-05/06.
RIQ-04 can be researched independently. This yields usable team import/selection
before advanced statistics are available. Implement incremental migrations; preserve
existing catalog UUIDs, API behavior, and the populated development volume.

## Work items

### RIQ-01 — Canonical athlete identities and provider mappings

Outcome: Yahoo, ESPN, Sleeper, and statistical feeds can refer to the same athlete.

Acceptance:
- Add canonical athlete/provider mapping models with sport-aware unique source IDs.
- Backfill current catalog records without changing externally visible player UUIDs
  or deleting provider records; preserve raw source IDs and provenance.
- Match trusted cross-provider IDs first. Ambiguous/name-only matches stay unresolved
  and are reportable for manual review; never silently merge them.
- Define a separate fantasy asset type for D/ST so roster imports preserve defenses.
- Verify migration round trip on disposable data, ID collisions across sports,
  ambiguous matches, and repeat backfills. Document the API compatibility strategy.

### RIQ-02 — League-season and fantasy-team profiles

Outcome: each team has its own rules and league context.

Acceptance:
- Create models/migrations and create/list/get APIs for league seasons and managed
  teams, identified by platform, sport, external league/team IDs, and season.
- Store league size, scoring format, scoring modifiers/categories, roster slots,
  locks, waiver/transaction settings, and configuration completeness.
- Support unknown fields explicitly and expose missing required settings. Do not
  calculate team-fit rankings for incompletely configured leagues.
- Cover three teams across Yahoo NBA, ESPN NFL, and Sleeper NFL with synthetic
  fixtures, including different league sizes and two accounts on one platform.
- Test duplicate imports, new seasons, and invalid/incompatible settings.

### RIQ-03 — Import-run history and freshness API

Outcome: users can see what data was refreshed and whether it succeeded.

Acceptance:
- Persist run ID, source, dataset/scope, start/end, status, source-as-of/fetch times,
  row counts, and a sanitized error summary; distinguish cache reuse from a new fetch.
- Record failed runs independently of rolled-back catalog/snapshot writes.
- Instrument the existing Sleeper player importer and provide paginated read APIs.
- Preserve last successful data on failure; expose stale/partial/interrupted states.
- Test successful, failed, repeated, and cached imports with no credentials in logs.

### RIQ-04 — Validate statistical source coverage

Outcome: ingestion tasks have a concrete, verified data contract.

Acceptance:
- Compare NBA box-score/schedule candidates and NFL weekly/PBP/snap candidates with
  sample payloads, provider IDs, historical depth, correction behavior, refresh
  cadence, field availability, access costs, and permitted usage documented.
- Select a usable baseline for each sport or identify the exact access decision
  required. Do not introduce subscriptions without user authorization.
- Explicitly mark routes, tracking stats, injuries, and ownership data as supported,
  delayed, unavailable, or requiring another source; missing values never become zeros.
- Save sanitized representative fixtures and a decision record with source links.

### RIQ-05 — Manual roster snapshot import

Outcome: teams can be imported before all platform connectors are available.

Acceptance:
- Define a versioned JSON import format with league/team IDs, scoring settings,
  roster entries, eligible positions, status, timestamp, and completeness scope.
- Provide a sample file and CLI validation/preview; report unresolved identities
  and validation errors with row context before applying changes.
- Apply a complete snapshot atomically and idempotently. Preserve roster slots,
  bench/IR, D/ST, and membership history without losing unresolved entries.
- Distinguish a user's roster-only snapshot from a complete league snapshot. Only
  complete data can establish free-agent availability; otherwise report unknown.
- Test invalid/partial files, duplicate players/slots, replay, and rollback. CSV
  conversion is optional follow-up, not required for this first import contract.

### RIQ-06 — My Teams UI and selection

Outcome: users can navigate their teams and inspect imported rosters.

Acceptance:
- Add My Teams overview and active-team selector, persisted locally by internal ID.
- Show platform, sport, season, league size, configuration gaps, roster slots,
  unresolved players, and last successful sync with stale/failure indicators.
- Distinguish imported roster data from catalog data. An unavailable connection
  must not look like an empty roster.
- Cover three teams, empty/import-needed state, stale snapshots, switching teams,
  and responsive keyboard-accessible navigation in frontend/browser checks.

### RIQ-07 — Sleeper league synchronization

Outcome: a Sleeper league can refresh profiles and full-league rosters on demand.

Acceptance:
- Accept a username/user ID or league ID and season; discover/select the managed team.
- Normalize settings, all rosters, identities, eligibility where provided, and waiver
  state where available through the same snapshot contract as manual import.
- Keep network failures/rate limiting from replacing the last complete snapshot;
  log scoped import runs and sanitize errors. Never assume unprovided fields.
- Use recorded fixtures in tests; perform live read-only verification once a real
  league is selected. Do not make provider calls from ordinary CI tests.

### RIQ-08 — Yahoo NBA connection and synchronization

Outcome: authorized Yahoo data powers the NBA team profile.

Acceptance:
- Verify app registration/access requirements and implement OAuth with state checking,
  backend-only credential storage, token refresh, disconnect, and expired-access UX.
- Discover league seasons/teams and normalize settings, rosters, positions, and
  league player availability where supported. Preserve provider-specific eligibility.
- Use import history and atomic snapshots; handle partial/rate-limited responses.
- Test callback validation, expiration, mapping, and snapshot failures with mocked
  responses. Live account verification depends on user-provided setup, not pasted secrets.

### RIQ-09 — ESPN NFL synchronization and fallback

Outcome: the ESPN team can use read-only sync or the established file import.

Acceptance:
- Validate the community adapter against the intended league type before committing
  to field support; document unsupported fields and upstream compatibility assumptions.
- Isolate adapter code and private-league credentials behind backend configuration;
  keep secrets out of browser storage, logs, repository, and fixtures.
- Import settings, full-league rosters, and supported availability through the common
  contract; expose authentication/partial-sync errors without erasing the last snapshot.
- Verify fixtures for public/private access behavior and preserve manual import
  usability when the connector cannot read the league.

### RIQ-10 — NBA game-log and schedule ingestion

Outcome: basketball research can compare actual performances over time.

Acceptance:
- Ingest game IDs/dates/status, athlete IDs, team/opponent, minutes, starts, core
  box-score counts, makes/attempts, and schedule from RIQ-04's selected source.
- Persist source provenance/as-of times; distinguish DNP, missing data, and zero stats.
- Upsert by source game/player identity; replay and stat corrections do not duplicate
  records. Keep postponed/cancelled/final games distinguishable.
- Verify identities, duplicates, missing fields, corrections, and import failures;
  do not require advanced tracking fields for baseline completion.

### RIQ-11 — NFL weekly-stat and schedule ingestion

Outcome: football research has position-appropriate historical opportunity data.

Acceptance:
- Ingest season/type/week/game identity, opponent, schedule, passing/rushing/receiving
  counts, supported opportunity fields, and snapshots of relevant team denominators.
- Preserve byes, DNPs, partial appearances, missing metrics, and stat corrections.
- Support regular/postseason distinctions and asset IDs for D/ST when provided.
- Prove idempotency and corrections with fixtures. Exclude in-season route promises
  unless RIQ-04 verified that feed; expose coverage metadata to downstream calculations.

### RIQ-12 — Historical summaries and scoring calculations

Outcome: the API returns comparable windows and league-specific historical values.

Acceptance:
- Return NBA and NFL totals/per-appearance averages, period boundaries, sample counts,
  and metric coverage. Include denominator definitions for shares and percentages.
- Aggregate shooting makes/attempts; return null for zero-denominator metrics.
- Compute historical points only for supported, complete scoring rules; report
  unsupported modifiers. Version settings and label which rules were applied.
- Test known scoring examples, byes/DNPs, zero attempts, corrections, and date bounds.
- Use fixtures to verify numerical results rather than mirroring implementation code.

### RIQ-13 — Explainable trend calculation and API

Outcome: rising/falling labels have inspectable supporting evidence.

Acceptance:
- Implement non-overlapping recent/baseline windows and configurable minimum samples.
- Return role and production changes separately, absolute/relative deltas, percentage
  point share changes, evidence completeness, timestamps, and rule version.
- Emit insufficient-evidence results for missing/short samples; avoid division-by-zero
  growth and unsupported route-based labels. Injury explanations require dated evidence.
- Provide sortable/filterable read endpoints. Test steady role/hot scoring, rising
  role/flat scoring, declining role, and partial-data examples.

### RIQ-14 — Research UI with rising/falling evidence

Outcome: users can inspect trends in the context of an active team.

Acceptance:
- Add sport/position/window filters and rising/falling/insufficient-evidence views.
- Show recent versus baseline values, sample size, data age, source, reason, and
  a game-log detail view. Distinguish unavailable metrics from zeros.
- Make league availability a separate filter with explicit unknown/stale states.
- Test filters, insufficient history, source errors, team switching, and mobile layout.

### RIQ-15 — League-specific add/drop comparison

Outcome: users can compare an available player with a candidate to drop.

Acceptance:
- Evaluate actual league availability, scoring completeness, position eligibility,
  roster slots, waiver state, and transaction constraints before showing a comparison.
- Show historical category/points contributions gained and lost, sample periods,
  usable schedule dates, and NBA percentage impact using combined makes/attempts.
- Show configurable category preferences explicitly; do not label them league rules.
- Compare different outputs for 10/12-team fixtures and PPR/non-PPR/category formats.
- Label results as historical comparison rather than a forecast or win probability.
  External adds/drops and projected future performance are excluded.

### RIQ-16 — Trend evaluation and historical validation

Outcome: trend usefulness is measured before adding predictive claims.

Acceptance:
- Define future role-change outcomes and evaluation windows before measuring results.
- Evaluate chronological holdouts using only information available at each decision
  time; use time-stamped roster snapshots for availability claims or omit those claims.
- Compare rules with simple recent-production/opportunity baselines; report sample
  sizes, coverage, false positives, and sport/position differences.
- Save reproducible inputs/rule versions/results. Small samples or absent historical
  snapshots must be documented, not converted into misleading confidence percentages.

### RIQ-17 — Complete the user's three league profiles

Outcome: live personalization has verified inputs.

Acceptance:
- Identify each league/team/season and its 10- or 12-team size.
- Capture Yahoo categories/points and categories/weights; ESPN/Sleeper reception,
  passing-TD, bonus, QB/superflex, and other custom rules.
- Capture roster slots, IR, lineup lock timing, waiver/budget/priority, acquisition
  limits, and any user category preferences separately from official scoring settings.
- Mark fields confirmed by import versus entered manually; show unresolved fields.
- Never ask the user to paste passwords, session cookies, or tokens into task notes.

## Definition of done

- Acceptance criteria are met and limitations recorded in the relevant task.
- Meaningful backend/frontend tests and applicable Linux checks pass. Database changes
  include reviewed migrations and disposable upgrade/downgrade/schema-drift checks.
- Existing player IDs/data remain intact, provider fixtures contain no credentials,
  and API/UI docs describe the final behavior.
- New source behavior is validated with fixtures; live checks are explicit and dated.
- Record implementation/check evidence here. Commit/push/remote CI status is reported
  separately; local completion must not imply publication.
