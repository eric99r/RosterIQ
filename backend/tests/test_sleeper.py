import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_session
from app.players.models import Player
from app.providers import import_players
from app.providers.sleeper import CatalogError, import_catalog, load_catalog, parse_catalog


def catalog(name="Example Player", team="KC"):
    return {
        "123": {
            "player_id": "123",
            "first_name": "Example",
            "last_name": "Player",
            "full_name": name,
            "sport": "nfl",
            "team": team,
            "position": "QB",
        },
        "KC": {"player_id": "KC", "position": "DEF"},
    }


def test_repeat_import_updates_without_changing_identity(client):
    session_context = contextmanager(client.app.dependency_overrides[get_session])
    with session_context() as session:
        assert import_catalog(session, catalog()) == {"processed": 1, "skipped_defenses": 1}
    original = client.get("/api/v1/players").json()["items"][0]
    with session_context() as session:
        import_catalog(session, catalog("Changed Name", None))
        import_catalog(session, catalog("Changed Name", None))
    page = client.get("/api/v1/players?q=changed&sport=NFL").json()
    assert page["total"] == 1
    updated = page["items"][0]
    assert updated["id"] == original["id"]
    assert updated["created_at"] == original["created_at"]
    assert updated["team"] is None
    assert updated["provider"] == "sleeper:nfl"


def test_invalid_catalog_does_not_partially_import(client):
    payload = catalog()
    payload["456"] = {"player_id": "different"}
    with contextmanager(client.app.dependency_overrides[get_session])() as session:
        with pytest.raises(CatalogError):
            import_catalog(session, payload)
        assert session.scalar(select(func.count()).select_from(Player)) == 0


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"123": None},
        {"KC": {"position": "DEF"}},
        {"123": {"player_id": "123", "sport": "nba"}},
    ],
)
def test_reject_invalid_catalog(payload):
    with pytest.raises(CatalogError):
        parse_catalog(payload)


def test_database_failure_rolls_back(client):
    with contextmanager(client.app.dependency_overrides[get_session])() as session:
        with patch.object(session, "commit", side_effect=SQLAlchemyError("failure")):
            with pytest.raises(SQLAlchemyError):
                import_catalog(session, catalog())
        assert session.scalar(select(func.count()).select_from(Player)) == 0


def test_cached_and_offline_files_do_not_fetch(tmp_path):
    path = tmp_path / "players.json"
    path.write_text(json.dumps(catalog()), encoding="utf-8")
    with patch("app.providers.sleeper.urlopen") as request:
        assert load_catalog(path) == catalog()
        assert load_catalog(path, offline=True) == catalog()
        request.assert_not_called()


def test_download_validates_before_replacing_cache(tmp_path):
    path = tmp_path / "players.json"
    path.write_text(json.dumps(catalog()), encoding="utf-8")
    with patch("app.providers.sleeper.time.time", return_value=path.stat().st_mtime + 86401):
        with patch("app.providers.sleeper.urlopen") as request:
            request.return_value.__enter__.return_value.read.return_value = b"[]"
            with pytest.raises(CatalogError):
                load_catalog(path)
    assert json.loads(path.read_text()) == catalog()


def test_cli_missing_snapshot_returns_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["import_players", "--file", str(tmp_path / "missing.json")])
    assert import_players.main() == 1
    assert "Import failed" in capsys.readouterr().err
