from sqlalchemy.exc import OperationalError

from app.db import get_session


def test_health(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


def test_database_unavailable(client):
    class UnavailableSession:
        def execute(self, statement):
            raise OperationalError("SELECT 1", {}, Exception("private connection details"))

    def unavailable_session():
        yield UnavailableSession()

    client.app.dependency_overrides[get_session] = unavailable_session
    assert client.get("/health/live").status_code == 200
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
