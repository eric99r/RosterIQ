# RosterIQ

An NFL/NBA fantasy analytics learning project: a React/TypeScript player catalog,
FastAPI modular monolith, and PostgreSQL. Frontend and backend live in one repository
but remain separate applications, dependencies, images, and check suites.

**MVP 1** is the player catalog, Sleeper player import, and React UI baseline.
See [MVP 1 scope](docs/releases/MVP-1.md) and [how to review and work on issues](CONTRIBUTING.md).

## Product direction and tasks

The next phase adds multi-platform team imports and explainable NBA/NFL research.
See the [prioritized implementation backlog](docs/BACKLOG.md) for task status,
acceptance criteria, and dependencies, and the [research/design notes](docs/research/fantasy-analytics.md)
for metric priorities, source constraints, scoring considerations, and open questions.
Confirmed platforms are Yahoo NBA, ESPN NFL, and Sleeper NFL. Planned features in
these documents are not yet implemented.

## Run the full stack

Install Docker Desktop (Linux containers) or Docker Engine with Compose 2.24.4+.
From the repository root, on Windows, macOS, or Linux:

```sh
docker compose up --build -d --wait
```

- UI: http://localhost:3000
- API docs through the UI proxy: http://localhost:3000/docs
- Direct API docs: http://localhost:8000/docs
- Database: localhost:5432, database/user/password `rosteriq` (local development only)

Compose waits for PostgreSQL, runs Alembic migrations, starts the API, then serves
React's production build from unprivileged nginx. Ports bind only to localhost.
The browser uses relative `/api` and `/health` URLs; nginx proxies to the API.
CORS settings and browser-facing backend environment variables are unnecessary.

```sh
docker compose ps -a
docker compose logs api frontend migrate
docker compose down
```

The existing `postgres_data` volume is retained after the folder move. Keep running
Compose from this root under the same project name. `down --volumes` deletes the
app's data; ordinary `down` retains it. An empty database shows an import prompt.

## Develop with live reload

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

Open http://localhost:5173. Edit `frontend/src/` or `backend/app/`; Vite and Uvicorn
reload automatically. Node dependencies live in the Linux image, avoiding platform
conflicts with Windows node_modules. Rebuild when package manifests or container
configuration changes. Vite proxies API requests to `api:8000` inside Compose.

To return to the production-style UI at port 3000:

```sh
docker compose down
docker compose up --build -d --wait
```

Optional native development: use Python 3.12+ and Node 22.12+ (host Node 16 is too old).
From the root install Python dependencies with
`python -m pip install -e './backend[dev]'`, then run Alembic/Uvicorn from `backend/`.
Copy `backend/.env.example` to `backend/.env`; environment variables override it.
From `frontend/`, run `npm ci` and `npm run dev`. Vite defaults to proxying
`http://127.0.0.1:8000`; set `API_PROXY_TARGET` to change that server-side address.
After moving the backend, reinstall any old editable Python installation that
still points to the former root-level `app/` folder.

## Linux container checks

These same commands run in CI; no host Python or Node installation is required:

```sh
docker compose -p rosteriq-checks -f compose.test.yaml run --build --rm checks
docker compose -p rosteriq-checks -f compose.test.yaml run --build --rm frontend-checks
docker compose -p rosteriq-checks -f compose.test.yaml down --volumes
```

Backend checks: Ruff lint/format, SQLite tests, migration upgrade, schema drift,
PostgreSQL tests, migration downgrade/upgrade, and another drift check. The temporary
test database exposes no host ports and is separate from the app database.

Frontend checks: ESLint, Vitest/React Testing Library, TypeScript, and production build.
Component tests cover live counts, search, sport filtering, pagination reset, details,
and connection errors/retry using mocked API responses. No external provider requests
are made during tests. The committed npm lockfile is consumed with `npm ci`.

Full-stack Chromium smoke test (runs in its own isolated Compose project):

```sh
docker compose -p rosteriq-e2e -f compose.yaml -f compose.e2e.yaml run --build --rm browser
docker compose -p rosteriq-e2e -f compose.yaml -f compose.e2e.yaml down --volumes
```

This checks the served UI, API proxy, readiness, desktop layout, and mobile overflow.
When the database contains players, it also checks search and details. The clean CI
stack starts empty; component tests independently cover populated states. Test screenshots
and traces are written inside the browser container's `test-results/`. To retain them,
mount an output directory or copy from a named test container before removing it.
Always run cleanup after checks, including failures. Never reuse the main app's
project name for the e2e commands, because their cleanup removes that project's data.

## Custom certificate authorities

If package downloads fail with `CERTIFICATE_VERIFY_FAILED` on your network, supply
an approved PEM CA bundle as a build secret. On this Windows machine the public
certificates were exported from trusted Windows stores to `.local/build-ca.pem`.
This local file is not committed or copied into images. TLS verification stays enabled.

```sh
docker build --secret id=custom_ca,src=.local/build-ca.pem -t rosteriq-api -t rosteriq-migrate ./backend
docker build --secret id=custom_ca,src=.local/build-ca.pem -t rosteriq-frontend ./frontend
docker compose up -d --no-build --wait

docker build --target checks --secret id=custom_ca,src=.local/build-ca.pem -t rosteriq-checks ./backend
docker build --target checks --secret id=custom_ca,src=.local/build-ca.pem -t rosteriq-frontend-checks ./frontend
docker compose -p rosteriq-checks -f compose.test.yaml run --rm checks
docker compose -p rosteriq-checks -f compose.test.yaml run --rm frontend-checks
docker compose -p rosteriq-checks -f compose.test.yaml down --volumes
```

For live reload build the frontend with `--target development -t rosteriq-frontend-dev`
using the same secret, then run the development Compose command without `--build`.
For browser checks build `--target browser -t rosteriq-browser` from `./frontend`
with the secret, then run the browser Compose command without `--build`.
Rebuild after changing source; these images contain a snapshot of the files.

## Player API and UI

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/players` | Create; 201 and Location, or 409 for duplicate provider identity |
| GET | `/api/v1/players?q=mahomes&sport=NFL&limit=20&offset=0` | Search, filter, paginate |
| GET | `/api/v1/players/{uuid}` | Player details or 404 |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Database connectivity; 503 when unavailable |

Create example (PowerShell):

```powershell
$body = @{ provider = 'example'; provider_player_id = '123'; name = 'Example Player'; sport = 'NFL'; team = 'KC'; position = 'QB' } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/api/v1/players -Method Post -ContentType 'application/json' -Body $body
```

The UI displays real catalog counts, literal name search, sport selection, pagination,
player details, and backend readiness checked every 30 seconds. Refresh rereads the
local database; it does not trigger a provider import. NBA's count can legitimately
be zero because the first provider import covers NFL. No projections or simulated
fantasy statistics are displayed. Provider import history is not persisted yet.

`sport` accepts `NFL` or `NBA`; limits are 1–100, offsets nonnegative. Invalid inputs
return 422. Team and position are optional free text. Input is trimmed; blank values
and unknown body fields are rejected. Provider names are lowercased; provider IDs
are case-sensitive strings. Search is a case-insensitive literal substring of 1–150
characters: SQL wildcards `%` and `_` are escaped and values are parameterized.
Counts apply to the combined filters. Simple scans are sufficient for this catalog;
trigram indexing can follow measured performance needs.

The internal UUID and unique `(provider, sport, provider_player_id)` tuple serve different
purposes. Different providers retain separate catalog records for the same real
player; identity mappings can link them to one canonical fantasy asset. Pages sort
by immutable UUID on a fixed dataset; concurrent inserts can shift offset pages.
Count/page queries use PostgreSQL's default isolation, so concurrent writes can
briefly make their snapshots differ. Cursor pagination remains future work.

## Canonical identities (RIQ-01)

The `identities` module adds canonical athletes and NFL team defenses, sport-scoped
provider mappings, trusted-ID resolution, and explicit manual review. Existing
player UUIDs, URLs, and JSON fields remain unchanged. The same provider ID can now
exist once per sport. Names never trigger automatic cross-provider links.

- `GET /api/v1/identities?unresolved_only=true&limit=20&offset=0` lists unresolved
  identities, their source IDs, reasons, and trusted references for review.
- `GET /api/v1/identities?player_id={uuid}` finds a catalog record's mapping.
- Optional `sport=NFL` or `sport=NBA` filters either view.

After building the updated API image and applying migrations, CLI operations run
in Linux on any supported host:

```sh
docker compose run --rm api python -m app.identities.cli review
docker compose run --rm api python -m app.identities.cli backfill
docker compose run --rm api python -m app.identities.cli link --identity-id ID --asset-id ID --reason "Verified source IDs"
# Only after review confirms there is no existing canonical asset:
docker compose run --rm api python -m app.identities.cli create --identity-id ID --reason "Reviewed; no existing match"
```

Replace `ID` with the respective UUID. Backfill is repeatable; upgrade `0002`
already backfills existing catalog rows. Manual linking requires a compatible
asset and an evidence note; it cannot reassign an existing link. No public write
endpoint accepts claims that a source ID is trusted.

See [identity design and migration notes](docs/architecture/identities.md) for the
data model, Python/SQLAlchemy decisions, and rollback limitations. League adapters
will supply vetted cross-provider IDs in later tasks; this change does not fetch
Yahoo/ESPN rosters. The existing player-only Sleeper import still skips defenses;
future roster adapters can preserve them as `TEAM_DEFENSE` assets.

## Sleeper NFL import

The first adapter uses [Sleeper's documented player catalog](https://docs.sleeper.com/).
No API key is required for this non-commercial learning project. From the repository
root, keep the cached snapshot on the host between one-off container runs:

```powershell
New-Item -ItemType Directory -Force .local | Out-Null
docker compose run --rm -v "${PWD}/.local:/data" api python -m app.providers.import_players --cache /data/sleeper-nfl.json
# Repeat offline without downloading:
docker compose run --rm -v "${PWD}/.local:/data" api python -m app.providers.import_players --file /data/sleeper-nfl.json
```

On macOS/Linux use `mkdir -p .local` and `-v "$(pwd)/.local:/data"`. Ensure the mounted
cache directory is writable by the container's appuser. On custom-CA networks,
export `SSL_CERT_FILE=/data/build-ca.pem` into the one-off container with
`-e SSL_CERT_FILE=/data/build-ca.pem` when fetching; offline imports need no CA file.
Existing root-level `.local/sleeper-nfl.json` snapshots survive the folder refactor.

Sleeper asks callers to fetch at most once per day. The cache is reused for 24 hours;
keep it between runs and run one importer at a time. It is a local cache, not a
shared rate limiter. `--file` never uses HTTP. Fetches have a 30-second socket timeout,
a 50 MiB response limit, and no automatic retries. Invalid downloads do not replace
an older cache. Failed commands exit with code 1.

Provider data is validated before writes; defenses are skipped and other malformed
records reject the snapshot. The namespace is `sleeper:nfl`. PostgreSQL upsert updates
name, team, and position while preserving UUID/creation time. One transaction covers
all batches; database failures roll back. Players missing from a newer snapshot are
retained. `processed` counts inserted plus updated records; defenses are counted
separately. Reimporting does not duplicate identities. There is no public import endpoint.

## Structure and design

```text
backend/
  app/
    core/config.py       environment settings
    db.py                ORM base, engine, request-scoped sessions
    main.py              application factory and lifecycle
    health.py            operational probes
    players/             models, DTOs, HTTP routes, use cases
    identities/          canonical assets, provider mappings, resolution and review CLI
    providers/           Sleeper adapter and explicit import CLI
  migrations/            Alembic schema versions
  tests/                 HTTP and provider tests
  scripts/check.py       portable check runner
  pyproject.toml
  Dockerfile
frontend/
  src/
    App.tsx              catalog, filters, status, and page state
    PlayerDetails.tsx    accessible native dialog and get-player request
    api.ts               typed API contracts and request helpers
    styles.css           responsive layout and visual styles
  e2e/                   Chromium smoke test
  package-lock.json
  Dockerfile             development, checks, browser, and runtime targets
compose*.yaml             full stack, reload, isolated checks, browser checks
.github/workflows/        CI for backend, frontend, and full-stack browser checks
```

For a Java/AWS developer:

- **Modular monolith:** one backend process/database grouped by capability. React is
  a separate client in the same repository, so API/UI changes can share a commit.
- **FastAPI/Pydantic:** routers resemble Spring MVC controllers; schemas are runtime-
  validated DTOs. Type hints feed validation and OpenAPI. SQLAlchemy models resemble
  JPA entities. A pooled engine is shared; a Session is a request-scoped unit of work.
  A yield dependency closes it like try-with-resources. The service owns commits and
  rollback; expected unique errors become HTTP 409. Synchronous handlers keep learning
  the ORM straightforward. Alembic is analogous to Flyway/Liquibase; serving the API
  never creates tables implicitly.
- **React/TypeScript/Vite:** components compose the view; state drives render output.
  Small effects load data and cancel stale requests. Search is debounced by 300ms,
  filter changes reset pagination, and the native dialog provides keyboard focus
  containment. Typed API contracts live in one module; no global state library or
  client router is needed for one screen. See [React's Vite guidance](https://react.dev/learn/build-a-react-app-from-scratch)
  and [Vite's development proxy](https://vite.dev/config/server-options).
- **One origin:** production nginx serves static React assets and proxies API/docs
  requests; Vite performs the same role during development. Database credentials stay
  in the backend environment. Both runtime images run as non-root users.
- **Portability:** Linux images define Python/Node environments; host tools are optional.
  Source mounts enable fast iteration, while separate image targets keep test tools
  out of runtime images. Frontend installs are locked; backend dependency ranges are
  constrained but do not yet have a reproducible deployment lockfile.

Authentication, production secrets/TLS/deployment, Redis, queues, projections, and
NBA provider ingestion remain outside this starter's current scope.
