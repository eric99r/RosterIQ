import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.players.models import Sport


class AssetType(enum.StrEnum):
    ATHLETE = "ATHLETE"
    TEAM_DEFENSE = "TEAM_DEFENSE"


class FantasyAsset(Base):
    """A canonical athlete or team defense, independent of provider records."""

    __tablename__ = "fantasy_assets"
    __table_args__ = (
        UniqueConstraint("id", "sport", "asset_type", name="uq_assets_identity_type"),
        CheckConstraint("asset_type != 'TEAM_DEFENSE' OR sport = 'NFL'", name="defense_is_nfl"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sport: Mapped[Sport] = mapped_column(
        Enum(Sport, native_enum=False, create_constraint=True, name="asset_sport")
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, native_enum=False, create_constraint=True, name="asset_type")
    )
    name: Mapped[str] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProviderIdentity(Base):
    __tablename__ = "provider_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider", "sport", "provider_player_id", name="uq_identities_provider_sport_id"
        ),
        ForeignKeyConstraint(
            ["asset_id", "sport", "asset_type"],
            ["fantasy_assets.id", "fantasy_assets.sport", "fantasy_assets.asset_type"],
            name="fk_identities_asset_type",
        ),
        CheckConstraint("asset_type != 'TEAM_DEFENSE' OR sport = 'NFL'", name="defense_is_nfl"),
        CheckConstraint(
            "(asset_id IS NULL AND match_method IS NULL AND review_reason IS NOT NULL) OR "
            "(asset_id IS NOT NULL AND match_method IS NOT NULL AND review_reason IS NULL)",
            name="resolution_state",
        ),
        Index("ix_identities_asset_id", "asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50))
    sport: Mapped[Sport] = mapped_column(
        Enum(Sport, native_enum=False, create_constraint=True, name="identity_sport")
    )
    provider_player_id: Mapped[str] = mapped_column(String(100))
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, native_enum=False, create_constraint=True, name="identity_asset_type")
    )
    source_name: Mapped[str] = mapped_column(String(150))
    asset_id: Mapped[uuid.UUID | None]
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", name="fk_identities_player"), unique=True
    )
    provenance: Mapped[str] = mapped_column(String(250))
    match_method: Mapped[str | None] = mapped_column(String(30))
    review_reason: Mapped[str | None] = mapped_column(String(100))
    resolution_evidence: Mapped[str | None] = mapped_column(String(500))
    trusted_references: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
