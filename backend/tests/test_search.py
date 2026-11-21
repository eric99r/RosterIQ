import pytest


def test_name_search(client):
    for index, (name, sport) in enumerate(
        [
            ("Patrick Mahomes", "NFL"),
            ("Patrick Example", "NBA"),
            ("Someone Else", "NFL"),
            ("Literal %_ Player", "NFL"),
        ]
    ):
        assert (
            client.post(
                "/api/v1/players",
                json={
                    "provider": "test",
                    "provider_player_id": str(index),
                    "name": name,
                    "sport": sport,
                },
            ).status_code
            == 201
        )
    page = client.get("/api/v1/players", params={"q": "  PATRICK  ", "limit": 1}).json()
    assert page["total"] == 2 and len(page["items"]) == 1
    filtered = client.get("/api/v1/players", params={"q": "patrick", "sport": "NFL"}).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["name"] == "Patrick Mahomes"
    literal = client.get("/api/v1/players", params={"q": "%_"}).json()
    assert literal["total"] == 1
    assert client.get("/api/v1/players?q=nobody").json()["total"] == 0


@pytest.mark.parametrize("q", ["", "   ", "x" * 151])
def test_invalid_search(client, q):
    assert client.get("/api/v1/players", params={"q": q}).status_code == 422
