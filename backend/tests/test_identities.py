from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db import get_session
from app.identities.models import AssetType, FantasyAsset, ProviderIdentity
from app.identities.schemas import IdentityInput, SourceIdentity
from app.identities.service import (
    IdentityConflictError,
    create_asset_for_identity,
    manually_link,
    resolve_identity,
    seed_catalog_identities,
)
from app.players.models import Player, Sport
from app.providers.sleeper import import_catalog

PLAYER = {"provider": "espn", "provider_player_id": "00123", "name": "Same Name", "sport": "NFL"}


@pytest.fixture
def session(client):
    with contextmanager(client.app.dependency_overrides[get_session])() as session:
        yield session


def incoming(provider="yahoo", source_id="nba.p.00123", **kwargs):
    return IdentityInput(
        provider=provider,
        provider_player_id=source_id,
        sport=kwargs.pop("sport", Sport.NFL),
        source_name="Same Name",
        provenance="synthetic trusted feed",
        **kwargs,
    )


def reference(provider="espn", source_id="00123", sport=Sport.NFL):
    return SourceIdentity(provider=provider, sport=sport, provider_player_id=source_id)


def test_catalog_backfill_is_repeatable_and_preserves_raw_records(client, session):
    player = Player(**PLAYER)
    session.add(player)
    session.flush()
    original_id, original_created = player.id, player.created_at
    assert seed_catalog_identities(session, provenance="test backfill") == 1
    assert seed_catalog_identities(session, provenance="second backfill") == 0
    identity = session.scalar(select(ProviderIdentity))
    assert identity.player_id == identity.asset_id == original_id
    assert identity.provider_player_id == "00123"
    assert identity.provenance == "test backfill"
    assert player.id == original_id and player.created_at == original_created
    assert session.scalar(select(func.count()).select_from(FantasyAsset)) == 1


def test_existing_player_api_and_new_identity_read(client):
    response = client.post("/api/v1/players", json=PLAYER)
    assert response.status_code == 201
    player = response.json()
    assert set(player) == {"id", "created_at", "team", "position", *PLAYER}
    page = client.get(f"/api/v1/identities?player_id={player['id']}").json()
    assert page["total"] == 1
    assert page["items"][0]["player_id"] == player["id"]
    assert page["items"][0]["match_method"] == "catalog_seed"
    assert client.get(response.headers["location"]).json() == player


def test_trusted_reference_links_two_providers_and_repeats(client, session):
    player = client.post("/api/v1/players", json=PLAYER).json()
    identity = resolve_identity(session, incoming(), trusted_references=(reference(),))
    session.commit()
    repeated = resolve_identity(session, incoming(), trusted_references=(reference(),))
    assert repeated.id == identity.id
    assert identity.asset_id == UUID(player["id"])
    assert identity.match_method == "trusted_id"
    assert identity.resolution_evidence == "synthetic trusted feed"
    assert identity.provider_player_id == "nba.p.00123"
    assert identity.trusted_references[0]["provider_player_id"] == "00123"
    assert session.scalar(select(func.count()).select_from(FantasyAsset)) == 1


@pytest.mark.parametrize("catalog_matches", [1, 2])
def test_name_only_matches_stay_unresolved_and_reportable(client, session, catalog_matches):
    for index in range(catalog_matches):
        client.post("/api/v1/players", json={**PLAYER, "provider_player_id": str(index)})
    identity = resolve_identity(session, incoming())
    session.commit()
    assert identity.asset_id is None
    assert identity.review_reason == "no_trusted_match"
    page = client.get("/api/v1/identities?unresolved_only=true&sport=NFL&limit=1").json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == str(identity.id)
    assert page["items"][0]["source_name"] == "Same Name"
    assert client.get("/api/v1/identities?unresolved_only=true&sport=NBA").json()["total"] == 0
    assert client.get("/api/v1/identities?unresolved_only=true&offset=1").json()["items"] == []


def test_conflicting_trusted_ids_stay_unresolved(client, session):
    for source_id in ("00123", "456"):
        client.post("/api/v1/players", json={**PLAYER, "provider_player_id": source_id})
    refs = (reference(), reference(source_id="456"))
    identity = resolve_identity(session, incoming(), trusted_references=refs)
    assert identity.asset_id is None
    assert identity.review_reason == "conflicting_trusted_ids"
    assert len(identity.trusted_references) == 2
    assert session.scalar(select(func.count()).select_from(FantasyAsset)) == 2


def test_unknown_reference_does_not_override_conflicting_evidence(client, session):
    client.post("/api/v1/players", json=PLAYER)
    refs = (reference(), reference(provider="unknown"))
    identity = resolve_identity(session, incoming(), trusted_references=refs)
    assert identity.asset_id is None
    assert identity.review_reason == "unresolved_trusted_id"
    resolved = resolve_identity(session, incoming(), trusted_references=(reference(),))
    assert resolved.id == identity.id
    assert resolved.asset_id is not None


def test_existing_mapping_is_never_reassigned(client, session):
    for source_id in ("00123", "456"):
        client.post("/api/v1/players", json={**PLAYER, "provider_player_id": source_id})
    identity = resolve_identity(session, incoming(), trusted_references=(reference(),))
    original = identity.asset_id
    with pytest.raises(IdentityConflictError):
        resolve_identity(session, incoming(), trusted_references=(reference(source_id="456"),))
    assert identity.asset_id == original


def test_sport_scoped_source_ids_and_cross_sport_references(client, session):
    nfl = client.post("/api/v1/players", json=PLAYER).json()
    nba = client.post("/api/v1/players", json={**PLAYER, "sport": "NBA"}).json()
    nfl_identity = resolve_identity(session, incoming(), trusted_references=(reference(),))
    nba_identity = resolve_identity(
        session, incoming(sport=Sport.NBA), trusted_references=(reference(sport=Sport.NBA),)
    )
    assert nfl_identity.asset_id == UUID(nfl["id"])
    assert nba_identity.asset_id == UUID(nba["id"])
    assert nfl_identity.asset_id != nba_identity.asset_id
    with pytest.raises(IdentityConflictError, match="sport"):
        resolve_identity(session, incoming(), trusted_references=(reference(sport=Sport.NBA),))


def test_manual_resolution_retains_source_and_evidence(client, session):
    player = client.post("/api/v1/players", json=PLAYER).json()
    identity = resolve_identity(session, incoming())
    result = manually_link(session, identity.id, UUID(player["id"]), reason="Verified source IDs")
    assert result.match_method == "manual"
    assert result.resolution_evidence == "Verified source IDs"
    assert result.provenance == "synthetic trusted feed"
    assert result.review_reason is None
    assert manually_link(session, identity.id, result.asset_id, reason="Retry").id == identity.id
    with pytest.raises(ValueError, match="evidence"):
        manually_link(session, identity.id, result.asset_id, reason=" ")


def test_defenses_are_not_athletes(client, session):
    defense = FantasyAsset(name="Example D/ST", sport=Sport.NFL, asset_type=AssetType.TEAM_DEFENSE)
    session.add(defense)
    session.flush()
    identity = resolve_identity(
        session, incoming(source_id="KC", asset_type=AssetType.TEAM_DEFENSE)
    )
    manually_link(session, identity.id, defense.id, reason="Verified team code")
    second = resolve_identity(
        session,
        incoming(provider="sleeper:nfl", source_id="KC", asset_type=AssetType.TEAM_DEFENSE),
        trusted_references=(reference(provider="yahoo", source_id="KC"),),
    )
    assert second.asset_id == defense.id
    assert second.player_id is None
    assert client.get("/api/v1/players").json()["total"] == 0
    athlete = resolve_identity(session, incoming(provider="other"))
    with pytest.raises(IdentityConflictError, match="type"):
        manually_link(session, athlete.id, defense.id, reason="Wrong type")
    with pytest.raises(IdentityConflictError, match="type"):
        resolve_identity(session, incoming(), trusted_references=(reference("yahoo", "KC"),))


def test_database_rejects_mismatched_asset_and_duplicate_source(client, session):
    player = client.post("/api/v1/players", json=PLAYER).json()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            ProviderIdentity(
                id=uuid4(),
                provider="other",
                provider_player_id="00123",
                sport=Sport.NBA,
                asset_type=AssetType.ATHLETE,
                source_name="Same Name",
                asset_id=UUID(player["id"]),
                provenance="invalid",
                match_method="manual",
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            ProviderIdentity(
                id=uuid4(),
                provider="espn",
                provider_player_id="00123",
                sport=Sport.NFL,
                asset_type=AssetType.ATHLETE,
                source_name="Same Name",
                provenance="duplicate",
                review_reason="no_trusted_match",
            )
        )
        session.flush()


def test_catalog_create_attaches_existing_unresolved_mapping(client, session):
    identity = resolve_identity(session, incoming(provider="espn", source_id="00123"))
    session.commit()
    player = client.post("/api/v1/players", json=PLAYER).json()
    session.refresh(identity)
    assert identity.player_id == UUID(player["id"])
    assert identity.asset_id is None
    assert identity.match_method is None


def test_repeat_sleeper_import_preserves_mapping(client, session):
    payload = {"00123": {"player_id": "00123", "full_name": "First Name", "position": "QB"}}
    import_catalog(session, payload)
    identity = session.scalar(select(ProviderIdentity))
    original = (identity.id, identity.asset_id, identity.player_id, identity.provenance)
    payload["00123"]["full_name"] = "Changed Name"
    import_catalog(session, payload)
    session.refresh(identity)
    assert (identity.id, identity.asset_id, identity.player_id, identity.provenance) == original
    assert session.scalar(select(func.count()).select_from(FantasyAsset)) == 1


@pytest.mark.parametrize("asset_type", [AssetType.ATHLETE, AssetType.TEAM_DEFENSE])
def test_create_asset_after_review_is_explicit_and_repeatable(session, asset_type):
    identity = resolve_identity(session, incoming(asset_type=asset_type))
    assert session.scalar(select(func.count()).select_from(FantasyAsset)) == 0
    created = create_asset_for_identity(session, identity.id, reason="Reviewed; no existing match")
    asset_id = created.asset_id
    assert session.get(FantasyAsset, asset_id).asset_type == asset_type
    assert created.match_method == "manual"
    assert create_asset_for_identity(session, identity.id, reason="Retry").asset_id == asset_id
    assert session.scalar(select(func.count()).select_from(FantasyAsset)) == 1


def test_player_create_cannot_reuse_defense_identity(client, session):
    resolve_identity(
        session, incoming(provider="espn", source_id="00123", asset_type=AssetType.TEAM_DEFENSE)
    )
    session.commit()
    assert client.post("/api/v1/players", json=PLAYER).status_code == 409
    assert client.get("/api/v1/players").json()["total"] == 0
    assert client.get("/api/v1/identities?unresolved_only=true").json()["total"] == 1


def test_identity_write_failure_rolls_back_catalog_import(session, monkeypatch):
    def fail(*args, **kwargs):
        raise IdentityConflictError("Simulated mapping conflict")

    monkeypatch.setattr("app.providers.sleeper.seed_catalog_identities", fail)
    with pytest.raises(IdentityConflictError):
        import_catalog(session, {"42": {"player_id": "42", "full_name": "Example"}})
    assert session.scalar(select(func.count()).select_from(Player)) == 0
    assert session.scalar(select(func.count()).select_from(ProviderIdentity)) == 0


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "sport=MLB", "player_id=x"])
def test_identity_query_validation(client, query):
    assert client.get(f"/api/v1/identities?{query}").status_code == 422
