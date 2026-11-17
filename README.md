# RosterIQ backend

A small NFL/NBA player catalog for learning Python backend development. Python 3.12+,
FastAPI, SQLAlchemy 2, PostgreSQL, and Alembic, deployed as one modular monolith.
Frontend, Redis, queues, provider ingestion, and projections are deferred.

## Start with Docker

Install Docker Desktop and start its Linux container engine, then run:

```sh
docker compose up --build -d
docker compose ps -a
```

Compose waits for PostgreSQL, runs `alembic upgrade head` in a one-off migration
container, then starts the API. Open http://localhost:8000/docs for interactive
OpenAPI documentation. PostgreSQL and the API bind only to localhost.

```sh
docker compose logs api migrate
docker compose down
```

The named volume keeps data across restarts. `docker compose down --volumes`
deletes that development data. Credentials in Compose are for local development.

## Run Python locally (PowerShell)

```powershell
python --version  # 3.12 or newer
python -m venv .venv
.venv\Scripts\python -m pip install -e '.[dev]'
Copy-Item .env.example .env
docker compose up -d db
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --reload
```

On macOS/Linux use `.venv/bin/` instead of `.venv\Scripts\`. No shell activation
is required when invoking these executables directly. Environment variables override
`.env`; `DATABASE_URL` uses SQLAlchemy's `postgresql+psycopg://` URL scheme.

## API

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/players` | Create, return 201 and Location; duplicate identity returns 409 |
| GET | `/api/v1/players?sport=NFL&limit=20&offset=0` | Filtered page with items, total, limit, offset |
| GET | `/api/v1/players/{uuid}` | Player or 404 |
| GET | `/health/live` | Process liveness, independent of the database |
| GET | `/health/ready` | Database connectivity; 503 when unavailable |

Example in PowerShell:

```powershell
$body = @{
  provider = 'espn'
  provider_player_id = '12345'
  name = 'Example Player'
  sport = 'NFL'
  team = 'KC'
  position = 'QB'
} | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/players -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod 'http://localhost:8000/api/v1/players?sport=NFL&limit=10&offset=0'
```

`sport` accepts uppercase `NFL` or `NBA`. Limits range from 1 to 100; offsets
must be nonnegative. Invalid bodies, UUIDs, and query parameters return 422.
Team and position are optional free text for now; they are not sport-specific enums.
Names and identifiers are trimmed, blank values rejected, and unknown input fields
rejected. Provider names are lowercased; provider player IDs remain case-sensitive
strings so leading zeros and alphanumeric IDs survive.

Each record has an internal UUID and a unique `(provider, provider_player_id)` pair.
This contract assumes a provider's IDs span sports. If a source reuses IDs by league,
use explicit namespaces such as `source:nfl` and `source:nba`. The same real player
from two providers currently creates two records; cross-provider identity resolution
is future work. Database uniqueness handles concurrent inserts safely.

Pages sort by immutable UUID for deterministic ordering on a fixed dataset. Offset
pagination is easy to inspect, but concurrent inserts can shift page boundaries;
cursor pagination can follow if the catalog grows. `total` counts matching players,
not the whole catalog. Count and page queries use PostgreSQL's default isolation,
so simultaneous writes may make the count briefly differ from the page snapshot.

## Design for a Java/AWS developer

```text
app/
  main.py          application factory, lifecycle, router assembly
  core/config.py   environment-based settings
  db.py            ORM base, engine, request-scoped sessions
  health.py        operational endpoints
  players/
    router.py      HTTP controller and dependency injection
    schemas.py     validated request/response DTOs
    models.py      SQLAlchemy entity and constraints
    service.py     use cases, queries, transaction ownership
migrations/        versioned database changes
tests/             HTTP tests with database dependency overrides
```

- **Modular monolith:** one process and database, with code grouped by business
  capability. Future analytics modules can sit alongside `players` without splitting
  services or adding distributed infrastructure.
- **FastAPI + Pydantic:** routers resemble Spring MVC controllers. Python type hints
  describe input/output shapes; Pydantic performs runtime validation and FastAPI
  generates OpenAPI. `Annotated` attaches validation or dependency metadata to types.
- **SQLAlchemy:** mapped models resemble JPA entities. An engine owns the connection
  pool; a `Session` is a unit of work, not a global singleton. `Depends` supplies one
  session per request and a `yield` dependency closes it, much like try-with-resources.
  The create service commits before returning, rolls back failed writes, and translates
  only the expected unique constraint into a domain error. The router maps that to 409.
- **Synchronous first:** regular `def` handlers let FastAPI run blocking database work
  in its thread pool. This avoids teaching async I/O at the same time as the ORM.
  No repository interface is needed yet; the service can express SQLAlchemy queries
  directly. A process-local settings cache avoids rebuilding configuration each request.
- **Explicit schema lifecycle:** Alembic plays the role of Flyway/Liquibase. The app
  never calls `create_all` in production. Migrations run separately before serving.
  UUIDs are generated by Python; timestamps come from the database.
- **Operations:** liveness and readiness map to container/ECS/Kubernetes probes.
  Readiness checks connectivity only; migrations are enforced by deployment order.
  The image runs as a non-root user. Authentication, production secrets, TLS, and
  deployment configuration are outside this local learning starter's scope.

References: [FastAPI dependency cleanup](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
and [SQLAlchemy session lifecycle](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

## Tests and code checks

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
```

Default tests use isolated in-memory SQLite databases for quick feedback, covering
HTTP contracts, filtering, pagination, validation, unique identities, and health
failures. SQLite is a test convenience; production always uses PostgreSQL.

To test the actual PostgreSQL dialect and migrations, create a **disposable** test DB:

```powershell
docker compose up -d db
docker compose exec db createdb -U rosteriq rosteriq_test
$env:DATABASE_URL = 'postgresql+psycopg://rosteriq:rosteriq@localhost:5432/rosteriq_test'
.venv\Scripts\alembic upgrade head
.venv\Scripts\alembic check
$env:TEST_DATABASE_URL = $env:DATABASE_URL
.venv\Scripts\python -m pytest -q
.venv\Scripts\alembic downgrade base
.venv\Scripts\alembic upgrade head
Remove-Item Env:TEST_DATABASE_URL
Remove-Item Env:DATABASE_URL
```

PostgreSQL tests use an outer transaction with per-session savepoints and roll back
each test. Never point these commands at a database you need to preserve. Downgrade
drops the player table. To change the schema, update models, run
`alembic revision --autogenerate -m "describe change"`, review the generated migration,
then run `alembic upgrade head`. Dependency ranges are constrained in `pyproject.toml`;
this starter does not yet include a reproducible deployment lock file.
