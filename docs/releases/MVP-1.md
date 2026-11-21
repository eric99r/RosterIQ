# MVP 1 — player catalog foundation

Baseline designated November 20, 2026.

## Delivered

- Python/FastAPI modular monolith with SQLAlchemy, PostgreSQL, and Alembic.
- Player create/list/get APIs, sport filtering, pagination, literal name search,
  provider-scoped identifiers, and health checks.
- Repeatable Sleeper NFL player catalog import.
- React/TypeScript catalog with player details, search, filters, pagination,
  loading/error/empty states, and responsive desktop/mobile views.
- Linux Docker Compose runtime, live reload, and backend/frontend/browser checks.
- Research notes and 17 follow-up issues with acceptance criteria and dependencies.

## Validation

Local Linux checks passed: 34 backend tests on SQLite and PostgreSQL, migration
checks, 5 frontend tests, lint/type/build checks, and Chromium desktop/mobile smoke
tests. Remote results are recorded in [GitHub Actions](https://github.com/eric99r/RosterIQ/actions).

The development database contains imported NFL players. Database volumes, cached
provider responses, certificates, and credentials are not release artifacts. A
fresh checkout starts with an empty database; follow the README to import players.

## Next phase

League/team profiles and roster imports for Yahoo NBA, ESPN NFL, and Sleeper NFL,
historical statistics, explainable trends, and league-specific comparisons are
backlog work. This MVP does not yet provide pickup recommendations or projections.
Redis and queues remain deferred.

Start with [RIQ-01](https://github.com/eric99r/RosterIQ/issues/1),
[RIQ-02](https://github.com/eric99r/RosterIQ/issues/2), and
[RIQ-03](https://github.com/eric99r/RosterIQ/issues/3).
[RIQ-04](https://github.com/eric99r/RosterIQ/issues/4) can be researched independently.
