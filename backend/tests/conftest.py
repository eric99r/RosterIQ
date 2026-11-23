import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import create_app


@pytest.fixture
def client():
    # TEST_DATABASE_URL must point to a disposable, already migrated PostgreSQL DB.
    url = os.getenv("TEST_DATABASE_URL")
    engine = (
        create_engine(url)
        if url
        else create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    )
    if not url:

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )

    def override_session():
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()
