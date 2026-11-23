from uuid import uuid4

import pytest

PLAYER = {
    "provider": "espn",
    "provider_player_id": "123",
    "name": "Example Player",
    "sport": "NFL",
    "team": "KC",
    "position": "QB",
}


def test_create_and_get(client):
    response = client.post("/api/v1/players", json=PLAYER)
    assert response.status_code == 201
    data = response.json()
    assert data.items() >= PLAYER.items()
    assert data["created_at"]
    fetched = client.get(response.headers["location"])
    assert fetched.status_code == 200
    assert fetched.json() == data


def test_provider_identity_and_recovery(client):
    assert client.post("/api/v1/players", json=PLAYER).status_code == 201
    duplicate = {**PLAYER, "provider": " ESPN "}
    assert client.post("/api/v1/players", json=duplicate).status_code == 409
    assert client.post("/api/v1/players", json={**PLAYER, "provider": "other"}).status_code == 201
    # The same raw source ID can identify different athletes in different sports.
    assert client.post("/api/v1/players", json={**PLAYER, "sport": "NBA"}).status_code == 201
    assert client.get("/api/v1/players").json()["total"] == 3


def test_filter_and_pagination(client):
    for index, sport in enumerate(["NFL", "NBA", "NFL"]):
        client.post(
            "/api/v1/players", json={**PLAYER, "provider_player_id": str(index), "sport": sport}
        )
    first = client.get("/api/v1/players?sport=NFL&limit=1").json()
    second = client.get("/api/v1/players?sport=NFL&limit=1&offset=1").json()
    assert first["total"] == second["total"] == 2
    assert first["limit"] == 1 and second["offset"] == 1
    assert first["items"][0]["sport"] == "NFL"
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get("/api/v1/players?offset=100").json()["items"] == []


@pytest.mark.parametrize("query", ["sport=MLB", "limit=0", "limit=101", "offset=-1", "limit=x"])
def test_invalid_query(client, query):
    assert client.get(f"/api/v1/players?{query}").status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "   "},
        {"provider": ""},
        {"provider_player_id": " "},
        {"sport": "MLB"},
        {"name": "x" * 151},
        {"unexpected": True},
        {"team": " "},
    ],
)
def test_invalid_payload(client, changes):
    assert client.post("/api/v1/players", json={**PLAYER, **changes}).status_code == 422


def test_missing_and_invalid_id(client):
    assert client.get(f"/api/v1/players/{uuid4()}").status_code == 404
    assert client.get("/api/v1/players/not-a-uuid").status_code == 422


def test_empty_catalog(client):
    assert client.get("/api/v1/players").json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }
