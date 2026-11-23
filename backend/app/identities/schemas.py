from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.identities.models import AssetType
from app.players.models import Sport


class SourceIdentity(BaseModel):
    """Provider adapters supply exact opaque IDs; never cast them to integers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=50, pattern=r".*\S.*")
    sport: Sport
    provider_player_id: str = Field(min_length=1, max_length=100, pattern=r".*\S.*")


class IdentityInput(SourceIdentity):
    source_name: str = Field(min_length=1, max_length=150)
    asset_type: AssetType = AssetType.ATHLETE
    provenance: str = Field(min_length=1, max_length=250)


class IdentityRead(SourceIdentity):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_type: AssetType
    source_name: str
    asset_id: UUID | None
    player_id: UUID | None
    provenance: str
    match_method: str | None
    review_reason: str | None
    resolution_evidence: str | None
    trusted_references: list[SourceIdentity]
    created_at: datetime


class IdentityPage(BaseModel):
    items: list[IdentityRead]
    total: int
    limit: int
    offset: int
