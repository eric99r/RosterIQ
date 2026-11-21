import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Sport(enum.StrEnum):
    NFL = "NFL"
    NBA = "NBA"


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("provider", "provider_player_id", name="uq_players_provider_identity"),
        Index("ix_players_sport_id", "sport", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50))
    provider_player_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(150))
    sport: Mapped[Sport] = mapped_column(
        Enum(Sport, native_enum=False, create_constraint=True, name="sport")
    )
    team: Mapped[str | None] = mapped_column(String(50))
    position: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
