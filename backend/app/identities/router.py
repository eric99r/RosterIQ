from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.identities.schemas import IdentityPage
from app.identities.service import list_identities
from app.players.models import Sport

router = APIRouter(prefix="/identities", tags=["identities"])


@router.get("", response_model=IdentityPage)
def identities(
    session: Annotated[Session, Depends(get_session)],
    unresolved_only: bool = False,
    sport: Sport | None = None,
    player_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return list_identities(
        session,
        unresolved_only=unresolved_only,
        sport=sport,
        player_id=player_id,
        limit=limit,
        offset=offset,
    )
