"""Sleeper NFL catalog adapter and transactional import."""

import json
import os
import time
from pathlib import Path
from urllib.request import urlopen

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.identities.service import seed_catalog_identities
from app.players.models import Player, Sport
from app.players.schemas import PlayerCreate

URL = "https://api.sleeper.app/v1/players/nfl"
MAX_BYTES = 50 * 1024 * 1024


class CatalogError(ValueError):
    """The catalog cannot safely be imported."""


def parse_catalog(payload: object) -> tuple[list[PlayerCreate], int]:
    if not isinstance(payload, dict) or not payload:
        raise CatalogError("Expected a nonempty Sleeper player map")
    players = []
    skipped = 0
    for provider_id, row in payload.items():
        if not isinstance(row, dict):
            raise CatalogError(f"Invalid record for {provider_id}")
        # Sleeper also includes team defenses; they are not individual players.
        if row.get("position") == "DEF":
            skipped += 1
            continue
        if row.get("sport", "nfl") != "nfl":
            raise CatalogError(f"Unexpected sport for {provider_id}")
        if row.get("player_id") != provider_id:
            raise CatalogError(f"Player ID does not match catalog key {provider_id}")
        name = row.get("full_name")
        if not name:
            name = " ".join(
                value
                for value in (row.get("first_name"), row.get("last_name"))
                if isinstance(value, str) and value.strip()
            )
        try:
            players.append(
                PlayerCreate(
                    provider="sleeper:nfl",
                    provider_player_id=provider_id,
                    name=name,
                    sport=Sport.NFL,
                    team=row.get("team") or None,
                    position=row.get("position") or None,
                )
            )
        except ValidationError as exc:
            raise CatalogError(f"Invalid player fields for {provider_id}") from exc
    if not players:
        raise CatalogError("Catalog contains no individual players")
    return players, skipped


def load_catalog(path: Path, *, offline: bool = False) -> object:
    """Reuse the snapshot for 24 hours; never retry a provider request automatically."""
    if offline or (path.exists() and time.time() - path.stat().st_mtime < 86400):
        if path.stat().st_size > MAX_BYTES:
            raise CatalogError("Catalog exceeds 50 MiB")
        return json.loads(path.read_text(encoding="utf-8"))
    with urlopen(URL, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise CatalogError("Catalog exceeds 50 MiB")
    payload = json.loads(raw)
    parse_catalog(payload)  # Do not overwrite a usable cache with invalid provider data.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_bytes(raw)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return payload


def import_catalog(session: Session, payload: object) -> dict[str, int]:
    players, skipped = parse_catalog(payload)
    dialect = session.get_bind().dialect.name
    insert = {"postgresql": pg_insert, "sqlite": sqlite_insert}.get(dialect)
    if insert is None:
        raise CatalogError(f"Unsupported database dialect: {dialect}")
    try:
        # Detect corrupted/manual cross-sport identities before applying any updates.
        mismatch = session.scalar(
            select(Player.id)
            .where(Player.provider == "sleeper:nfl", Player.sport != Sport.NFL)
            .limit(1)
        )
        if mismatch is not None:
            raise CatalogError("Existing sleeper:nfl identity has the wrong sport")
        for start in range(0, len(players), 500):
            statement = insert(Player).values(
                [player.model_dump() for player in players[start : start + 500]]
            )
            statement = statement.on_conflict_do_update(
                index_elements=[Player.provider, Player.sport, Player.provider_player_id],
                set_={
                    field: getattr(statement.excluded, field)
                    for field in ("name", "team", "position")
                },
            )
            player_ids = session.scalars(statement.returning(Player.id)).all()
            seed_catalog_identities(
                session, provenance="Sleeper NFL catalog", player_ids=player_ids
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"processed": len(players), "skipped_defenses": skipped}
