"""Add canonical assets and sport-scoped source mappings; preserve catalog UUIDs."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_players_provider_identity", "players", type_="unique")
    op.create_unique_constraint(
        "uq_players_provider_identity", "players", ["provider", "sport", "provider_player_id"]
    )
    op.create_table(
        "fantasy_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "sport",
            sa.Enum("NFL", "NBA", native_enum=False, create_constraint=True, name="asset_sport"),
            nullable=False,
        ),
        sa.Column(
            "asset_type",
            sa.Enum(
                "ATHLETE",
                "TEAM_DEFENSE",
                native_enum=False,
                create_constraint=True,
                name="asset_type",
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fantasy_assets"),
        sa.UniqueConstraint("id", "sport", "asset_type", name="uq_assets_identity_type"),
        sa.CheckConstraint("asset_type != 'TEAM_DEFENSE' OR sport = 'NFL'", name="defense_is_nfl"),
    )
    op.create_table(
        "provider_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column(
            "sport",
            sa.Enum("NFL", "NBA", native_enum=False, create_constraint=True, name="identity_sport"),
            nullable=False,
        ),
        sa.Column("provider_player_id", sa.String(100), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "ATHLETE",
                "TEAM_DEFENSE",
                native_enum=False,
                create_constraint=True,
                name="identity_asset_type",
            ),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(150), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("player_id", sa.Uuid(), nullable=True),
        sa.Column("provenance", sa.String(250), nullable=False),
        sa.Column("match_method", sa.String(30), nullable=True),
        sa.Column("review_reason", sa.String(100), nullable=True),
        sa.Column("resolution_evidence", sa.String(500), nullable=True),
        sa.Column("trusted_references", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_provider_identities"),
        sa.UniqueConstraint(
            "provider", "sport", "provider_player_id", name="uq_identities_provider_sport_id"
        ),
        sa.UniqueConstraint("player_id", name="uq_provider_identities_player_id"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name="fk_identities_player"),
        sa.ForeignKeyConstraint(
            ["asset_id", "sport", "asset_type"],
            ["fantasy_assets.id", "fantasy_assets.sport", "fantasy_assets.asset_type"],
            name="fk_identities_asset_type",
        ),
        sa.CheckConstraint("asset_type != 'TEAM_DEFENSE' OR sport = 'NFL'", name="defense_is_nfl"),
        sa.CheckConstraint(
            "(asset_id IS NULL AND match_method IS NULL AND review_reason IS NOT NULL) OR "
            "(asset_id IS NOT NULL AND match_method IS NOT NULL AND review_reason IS NULL)",
            name="resolution_state",
        ),
    )
    op.create_index("ix_identities_asset_id", "provider_identities", ["asset_id"])
    # Migration-local SQL stays independent of future application model changes.
    op.execute("""
        INSERT INTO fantasy_assets (id, sport, asset_type, name, created_at)
        SELECT id, sport, 'ATHLETE', name, created_at FROM players
    """)
    op.execute("""
        INSERT INTO provider_identities
            (id, provider, sport, provider_player_id, asset_type, source_name,
             asset_id, player_id, provenance, match_method, trusted_references, created_at)
        SELECT id, provider, sport, provider_player_id, 'ATHLETE', name,
               id, id, 'migration:0002 catalog backfill', 'catalog_seed', '[]', created_at
        FROM players
    """)


def downgrade() -> None:
    # Never remove data to make the old, narrower uniqueness rule fit.
    collision = (
        op.get_bind()
        .execute(
            sa.text("""
        SELECT provider, provider_player_id FROM players
        GROUP BY provider, provider_player_id HAVING COUNT(*) > 1 LIMIT 1
    """)
        )
        .first()
    )
    if collision is not None:
        raise RuntimeError("Cannot downgrade: cross-sport source IDs conflict with revision 0001")
    op.drop_table("provider_identities")
    op.drop_table("fantasy_assets")
    op.drop_constraint("uq_players_provider_identity", "players", type_="unique")
    op.create_unique_constraint(
        "uq_players_provider_identity", "players", ["provider", "provider_player_id"]
    )
