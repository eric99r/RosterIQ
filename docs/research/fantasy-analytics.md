# Fantasy research and product notes

Recorded November 20, 2026. This is a design reference, not a current pickup list.
Implementation work is tracked in [the backlog](../BACKLOG.md).

## Product objective

Answer: **Who is improving, why, and would adding them help this particular team?**
Show underlying evidence, period, sample size, source, and freshness. An improvement
in recent results is not automatically an improvement in future value.

Confirmed user context:

- Three teams across three platforms: Yahoo NBA, ESPN NFL, and Sleeper NFL.
- League sizes include 10 and 12 teams; the size for each team is not yet confirmed.
- Support additional accounts, leagues, teams, and seasons without schema redesign.
- Keep the modular monolith, React client, PostgreSQL, and portable Linux checks.
- Continue explaining significant implementation decisions for a Java/AWS developer
  learning Python.

Still unknown: each league's scoring rules, size, roster slots, lineup locks, waiver
rules, transaction limits, and season identifiers. In particular, confirm NBA
categories versus points, NFL standard/half-PPR/PPR, passing-TD values, and
one-QB versus superflex. Store incomplete configuration explicitly; do not infer
scoring from a platform name or silently default to a popular format.

## NBA metrics

| Priority | Metrics | Purpose |
| --- | --- | --- |
| First | Minutes, starts, games played, recent minutes changes | Identify opportunity changes |
| First | PTS, REB, AST, STL, BLK, 3PM, TO | Show category contributions |
| First | FGM/FGA, FTM/FTA, 3PA | Preserve volume and derive percentages correctly |
| First | Schedule, remaining games, lineup eligibility | Find games that can fit into the user's lineup |
| First | Injury designation and timestamp | Explain missed games and availability |
| Later, source-dependent | Usage, touches, potential assists, rebound chances | Explain underlying opportunity |

Offer totals and per-appearance averages with clearly labeled denominators. Keep
missed games visible separately. Calculate FG% as total FGM / total FGA and FT%
as total FTM / total FTA; never average percentages. Zero attempts means unavailable,
not 0%. Evaluate team percentage impact by recomputing combined makes and attempts.

For category leagues, preserve category-level contributions and configurable
priorities/punts. A generic rank does not measure fit for every roster. For points
leagues, use the imported scoring weights. Do not label hypothetical future points
as actual historical production.

Streaming considers usable lineup days, eligibility, transaction limits, and locks.
Four scheduled games are not necessarily four usable starts. Injuries, rotations,
blowouts, overtime, and returning teammates can explain temporary opportunity changes.

## NFL metrics

| Position | Priority metrics |
| --- | --- |
| QB | Passing attempts/yards/TDs/INTs, rushing attempts/yards/TDs, scoring-area rushing |
| RB | Carries, targets, receptions, snap/carry shares, inside-the-5 opportunities |
| WR | Targets, target share, receiving production, air yards, scoring-area targets |
| TE | Targets, target share, receiving production; routes when available |
| D/ST | Sacks, turnovers, allowed points/yards under league rules, opponent context |
| K | Makes/attempts and distance bands, league scoring, weather/dome context |

Route participation and targets per route are useful later additions if a reliable
in-season feed is verified. Snap share alone does not show how often someone ran a
route. Define denominators explicitly: team attempts, dropbacks, offensive snaps,
and routes are not interchangeable. Keep actual fantasy points tied to the league's
scoring-rule version. Raw rank, roster percentage, and add/drop activity are context,
not sufficient evidence of a role change or league availability.

The current player importer excludes NFL team defenses. Supporting D/ST analysis
requires an explicit fantasy-asset representation; do not invent person records
for defenses or silently omit them from imported rosters.

## Trend design

Initial comparisons to evaluate, not validated prediction rules:

- NBA: last five appearances versus preceding ten; optional 7/14/30-day displays.
- NFL: last three appearances versus preceding three; individual weeks and season context.
- Comparison windows must not overlap. Show dates, counts, denominators, and missing data.
- A bye, DNP, injury-shortened appearance, and a full game with zero production
  represent different situations. Preserve their distinctions.
- Require configurable minimum samples per metric. Show insufficient evidence when
  data is missing. New players should not receive infinite percentage growth.
- Show share changes in percentage points, and distinguish them from relative growth.

| Label | Evidence to expose |
| --- | --- |
| Role rising / falling | Sustained opportunity change in minutes, targets, carries, or verified routes |
| Production rising / falling | Result changes, independently of role changes |
| Temporary opportunity | Opportunity with dated injury/rotation context |
| Efficiency spike | Results rose without corresponding opportunity growth |
| Cold results, stable role | Poor results while opportunities remain comparable |
| Schedule opportunity | Additional usable games or a near-term roster gap |

Start with transparent rules and evidence completeness labels. A label such as
"moderate evidence" describes sample support, not a calibrated success probability.
Backtest on data available at the historical decision time, split by sport/position,
and compare against simple baselines. Report false positives and coverage before
claiming predictive power. Preserve rule versions so results can be reproduced.

## Multiple teams and imports

Separate platform connections, league seasons, fantasy teams, roster snapshots,
scoring settings, and player identities. Use one canonical athlete with explicit
provider-ID mappings; retain existing catalog UUIDs and provider provenance.
Avoid name-only automatic merges. Provide a review path for unresolved matches.

Import all relevant league rosters or a provider availability feed, not just the
user's team. Availability belongs to a league and timestamp. Partial syncs must not
make missing players appear available. Eligibility and injury-slot rules can differ
across platforms. A completed snapshot should replace the active snapshot atomically.

Team-fit comparison should show an add/drop pair, lost contributions, lineup fit,
scoring rules, and availability freshness. A 10-team or 12-team label alone does not
determine replacement value. Begin with historical comparisons and schedule facts;
projections and automated roster transactions remain deferred.

Suggested UI progression: team selector -> My Teams -> team roster and sync status ->
Research with rising/falling evidence -> available-player comparison for selected team.
An all-teams overview can show the same player as owned, unavailable, or available in
different leagues. Readiness, data freshness, and last import success are distinct states.

## Source findings and limitations

These are research references, not promises that every field can be ingested.
Verify access, current field coverage, refresh cadence, and usage conditions for
each source before implementation. Recheck time-sensitive findings when starting
the corresponding adapter task.

- [NBA glossary](https://www.nba.com/stats/help/glossary): authoritative definitions
  for advanced basketball metrics.
- [Hashtag Basketball user guide](https://hashtagbasketball.com/user-guide): per-game
  versus total rankings and category weighting support format-specific views.
- [Hashtag streaming guide](https://hashtagbasketball.com/fantasy-basketball/content/how-to-stream-fantasy-basketball):
  category needs, schedules, and transaction limits inform streaming.
- [PFF usage report](https://www.pff.com/news/fantasy-football-usage-production-report)
  and [Fantasy Life utilization](https://www.fantasylife.com/nfl/utilization-report/season-stats):
  examples of opportunity-based football research; public articles are not ingestion licenses.
- [nflverse data schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html):
  player stats, snaps, and schedules have different refresh schedules. As reviewed,
  participation from 2023 onward arrives after the postseason, not during the season.
  Do not promise current routes from that dataset. Handle official stat corrections.
- [Yahoo developer portal](https://sports.yahoo.com/developer/) and
  [resource documentation](https://sports.yahoo.com/developer/docs/): official OAuth
  and league/team/settings resources. App setup and authorized account access are needed.
- [Sleeper documentation](https://docs.sleeper.com/): read-only league/settings/roster
  endpoints; cache the large player catalog and respect its once-daily guidance.
- [Community ESPN adapter](https://github.com/cwendt94/espn-api): supports football and
  basketball. Private-league authentication requires sensitive session information.
  It is not an ESPN-supported OAuth contract; retain a manual file import fallback.

Platform access and statistics access are separate concerns. A roster connection
does not guarantee access to advanced historical statistics. Credential material
must stay out of repository files, browser storage, logs, and fixture data.

## Scope boundaries

Now: identities, teams/leagues, historical stats, imports, freshness, explainable trends,
and historical team-fit comparisons. Later: calibrated projections, automated pickups,
notifications, Redis, queues, multi-user hosted authentication, and paid feeds unless
explicitly selected. Read-only provider sync can start as a CLI/manual action using
the existing stack.
