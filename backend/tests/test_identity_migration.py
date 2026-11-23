"""Exercise real migrations with populated data in an isolated PostgreSQL schema."""

import os
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.identities.service import seed_catalog_identities


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires disposable PostgreSQL")
def test_populated_upgrade_downgrade_and_repeat_backfill():
    schema = f"identity_test_{uuid4().hex}"
    admin = create_engine(os.environ["TEST_DATABASE_URL"])
    url = make_url(os.environ["TEST_DATABASE_URL"]).update_query_dict(
        {"options": f"-csearch_path={schema}"}
    )
    engine = create_engine(url)
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False)}

    def migrate(direction, revision, *, success=True):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", direction, revision],
            env=env,
            capture_output=True,
            text=True,
        )
        assert (result.returncode == 0) == success, result.stderr
        return result

    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        migrate("upgrade", "0001")
        player_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO players (id, provider, provider_player_id, name, sport, team, position)
                VALUES (:id, 'legacy', '00042', 'Original Name', 'NFL', 'KC', 'QB')
            """),
                {"id": player_id},
            )
            original = dict(connection.execute(text("SELECT * FROM players")).mappings().one())
        for _ in range(2):
            migrate("upgrade", "head")
            with Session(engine) as session, session.begin():
                assert seed_catalog_identities(session, provenance="repeat") == 0
                assert seed_catalog_identities(session, provenance="repeat again") == 0
            with engine.connect() as connection:
                assert (
                    dict(connection.execute(text("SELECT * FROM players")).mappings().one())
                    == original
                )
                mapping = (
                    connection.execute(text("SELECT * FROM provider_identities")).mappings().one()
                )
                assert mapping["id"] == mapping["player_id"] == mapping["asset_id"] == player_id
                assert mapping["provider_player_id"] == "00042"
                assert mapping["provenance"] == "migration:0002 catalog backfill"
            migrate("downgrade", "0001")
            with engine.connect() as connection:
                assert (
                    dict(connection.execute(text("SELECT * FROM players")).mappings().one())
                    == original
                )
        migrate("upgrade", "head")
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO players (id, provider, provider_player_id, name, sport)
                VALUES (:id, 'legacy', '00042', 'Another Athlete', 'NBA')
            """),
                {"id": uuid4()},
            )
        result = migrate("downgrade", "0001", success=False)
        assert "cross-sport source IDs conflict" in result.stderr
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM players")) == 2
            assert connection.scalar(text("SELECT COUNT(*) FROM provider_identities")) == 1
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002"
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        admin.dispose()
