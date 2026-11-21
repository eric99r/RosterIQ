"""Create the player catalog."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_player_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column(
            "sport",
            sa.Enum("NFL", "NBA", native_enum=False, create_constraint=True, name="sport"),
            nullable=False,
        ),
        sa.Column("team", sa.String(50), nullable=True),
        sa.Column("position", sa.String(30), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_players"),
        sa.UniqueConstraint("provider", "provider_player_id", name="uq_players_provider_identity"),
    )
    op.create_index("ix_players_sport_id", "players", ["sport", "id"])


def downgrade() -> None:
    op.drop_index("ix_players_sport_id", table_name="players")
    op.drop_table("players")
