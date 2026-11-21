from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.players.models import Sport

Provider = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=50)
]
ProviderID = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Team = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Position = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class PlayerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Provider
    provider_player_id: ProviderID
    name: Name
    sport: Sport
    team: Team | None = None
    position: Position | None = None


class PlayerRead(PlayerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class PlayerPage(BaseModel):
    items: list[PlayerRead]
    total: int
    limit: int
    offset: int
