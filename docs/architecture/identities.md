# Canonical identities — RIQ-01

## Data model

`players` remains the provider catalog and public API compatibility boundary.
`fantasy_assets` represents canonical entities with a discriminator: `ATHLETE`
for a person, `TEAM_DEFENSE` for an NFL defense. A single typed table keeps both
rosterable without inventing people for D/ST or adding a second copy of shared
identity logic. An athlete is a fantasy asset with type `ATHLETE`.

`provider_identities` has one row per `(provider, sport, provider_player_id)`.
Raw IDs are opaque strings: leading zeros, case, and prefixes are meaningful.
Existing catalog namespaces such as `sleeper:nfl` remain unchanged. New adapters
must deliberately reuse the established namespace rather than silently alias it.

Each mapping records its source name, initial provenance, creation time, optional
legacy player UUID, optional canonical asset UUID, match method, review reason,
trusted references, and resolution evidence. A null asset ID means unresolved.
The source name is the name recorded when the identity was first observed, not
a live display-name feed. Catalog name/team/position changes do not rewrite it
or override a canonical name from another source.

A composite foreign key enforces matching sport and asset type between a mapping
and its asset. Check constraints disallow NBA defenses and inconsistent resolution
states. A unique player foreign key attaches at most one mapping to each legacy
catalog row. PostgreSQL enforces these rules independently of API validation.

## Resolution rules

1. Look up the exact provider/sport/source-ID tuple.
2. Vetted adapters can call `resolve_identity` with trusted source-ID references.
   All supplied references must already link to the same compatible asset.
3. Without trusted matches, preserve an unresolved row. One matching name is as
   insufficient as several matching names. Missing references and conflicting
   canonical targets have distinct review reasons.
4. An operator can inspect the paginated identities API or CLI report and link an
   unresolved record to a compatible asset with an evidence note. If no canonical
   asset exists, the explicit `create` CLI action creates and links a typed asset
   atomically, with a required evidence note. Trusted/manual
   resolution updates the existing mapping instead of creating another one.
5. Existing links cannot be reassigned. Conflicting evidence raises an explicit
   domain error; canonical merges and reassignment audits require separate work.

There is no public trusted-ID write API. An adapter must validate its crosswalk's
source before passing references; the generic service cannot certify an external
feed. Unknown references are not automatically asserted as new aliases. Future
roster/statistics adapters own that source-specific validation and ingestion.

Existing catalog rows seed independent canonical athletes with `catalog_seed` as
their method. This preserves known records without asserting that same-name rows
from different sources are the same person. It is not corroborated cross-provider
matching. The backfill never merges them. New external identities can subsequently
link to these anchors through trusted evidence or manual review. Catalog creation
attaches to an already observed mapping, including an unresolved one, without
overriding its resolution state. Separate pre-seeded anchors require a future
audited merge workflow if later evidence establishes they are the same athlete.

## Transactions and Python design

SQLAlchemy's typed `Mapped[...]` fields are similar to JPA entity fields, while
Pydantic schemas validate adapter/API data. The string enums keep database and
JSON values readable. Explicit service functions keep transaction ownership
visible instead of hiding it in ORM lifecycle callbacks.

Identity operations call `flush()` to validate writes but do not commit. The player
service, importer, or CLI owns the transaction, much like a Spring transactional
application-service boundary. A failed import rolls back both catalog and identity
writes. Existing mappings are locked when resolved to serialize competing decisions
on PostgreSQL. Database uniqueness prevents concurrent creation of duplicate source
IDs; a losing concurrent insert may need a transaction retry by its caller. Run
manual backfills/imports one at a time, as with the existing importer.

The catalog importer batches upserts and mapping creation for the returned player
IDs. Repeated imports preserve canonical IDs and manually resolved links. It does
not read cross-provider IDs from Sleeper's payload yet; a later adapter must verify
which fields provide trustworthy crosswalks.

## Migration and compatibility

Revision `0002` adds the new tables and widens catalog uniqueness to include sport.
The backfill uses migration-local SQL, not mutable application models. Every
existing row keeps its original UUID, raw source ID, provider, name, team, position,
and creation time. Its initial asset/mapping UUIDs equal its catalog UUID in their
respective tables. This makes the backfill deterministic without changing API IDs.

The player create/list/get JSON contract remains unchanged. The behavioral change
is deliberate: an existing provider/source ID in NFL no longer blocks the same
ID in NBA; a duplicate within a sport still returns 409. The new identities API
exposes canonical associations separately, so the current React client needs no
change. Catalog totals continue to count source records, not distinct athletes.

Upgrade via the normal Compose migration service after building the updated images.
Validation runs against disposable PostgreSQL data and never deletes or migrates
the populated development volume as part of tests.

Downgrading to `0001` preserves catalog rows but **drops canonical mappings,
resolution evidence, and defense assets**; export/back up those tables first if
they contain useful work. It refuses to run when two sports reuse a provider ID,
because the old constraint could not represent them. Resolve the compatibility
decision explicitly rather than deleting rows to force a downgrade. Re-upgrading
reconstructs original catalog anchors, not discarded manual/trusted links.

Tests exercise populated upgrade/downgrade/re-upgrade, repeated backfills, cross-sport
collisions, ambiguous names, conflicting references, manual resolution, database
foreign keys, defense typing, and unchanged player responses. SQLite enables foreign
keys for the fast suite; PostgreSQL is authoritative for migrations and locking.

References: [SQLAlchemy composite constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html),
[Alembic data migration guidance](https://alembic.sqlalchemy.org/en/latest/cookbook.html#data-migrations-general-techniques).
