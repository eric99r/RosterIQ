from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import StringConstraints
from sqlalchemy.orm import Session

from app.db import get_session
from app.identities.service import IdentityConflictError
from app.players import service
from app.players.models import Sport
from app.players.schemas import PlayerCreate, PlayerPage, PlayerRead

router = APIRouter(prefix="/players", tags=["players"])
Database = Annotated[Session, Depends(get_session)]


@router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(data: PlayerCreate, response: Response, session: Database):
    try:
        player = service.create_player(session, data)
    except service.DuplicatePlayerError as exc:
        raise HTTPException(
            409, "Player already exists for this provider, sport, and provider_player_id"
        ) from exc
    except IdentityConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    response.headers["Location"] = f"/api/v1/players/{player.id}"
    return player


@router.get("", response_model=PlayerPage)
def list_players(
    session: Database,
    sport: Sport | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
        Query(description="Case-insensitive literal substring of the player name"),
    ] = None,
):
    return service.list_players(session, sport, limit, offset, q)


@router.get("/{player_id}", response_model=PlayerRead)
def get_player(player_id: UUID, session: Database):
    player = service.get_player(session, player_id)
    if player is None:
        raise HTTPException(404, "Player not found")
    return player
