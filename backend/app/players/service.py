from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.players.models import Player, Sport
from app.players.schemas import PlayerCreate


class DuplicatePlayerError(Exception):
    pass


def create_player(session: Session, data: PlayerCreate) -> Player:
    player = Player(**data.model_dump())
    session.add(player)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # PostgreSQL identifies the exact constraint; don't hide unrelated database errors.
        diag = getattr(exc.orig, "diag", None)
        if getattr(diag, "constraint_name", None) == "uq_players_provider_identity":
            raise DuplicatePlayerError from exc
        # SQLite supports fast local tests using the same compound uniqueness rule.
        if "UNIQUE constraint failed: players.provider, players.provider_player_id" in str(
            exc.orig
        ):
            raise DuplicatePlayerError from exc
        raise
    return player


def list_players(
    session: Session, sport: Sport | None, limit: int, offset: int, q: str | None = None
):
    filters = [Player.sport == sport] if sport else []
    if q:
        # Escape SQL LIKE wildcards: user input is a literal substring.
        filters.append(Player.name.icontains(q, autoescape=True))
    total = session.scalar(select(func.count()).select_from(Player).where(*filters))
    items = session.scalars(
        select(Player).where(*filters).order_by(Player.id).limit(limit).offset(offset)
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_player(session: Session, player_id: UUID) -> Player | None:
    return session.get(Player, player_id)
