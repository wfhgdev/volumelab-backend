from uuid import uuid4

from sqlalchemy.exc import DBAPIError


class FakePgError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None):
        super().__init__(message)
        self.sqlstate = sqlstate


def test_list_app_users_rejects_negative_skip(client):
    response = client.get("/app-users/?skip=-1")
    assert response.status_code == 422


def test_duplicate_email_returns_409(client):
    email = f"app_user_{uuid4().hex}@example.com"
    payload = {"name": "Ana", "email": email, "password_hash": "hash"}

    assert client.post("/app-users/", json=payload).status_code == 201

    response = client.post("/app-users/", json={**payload, "email": email.upper()})

    assert response.status_code == 409


def test_invalid_height_returns_422(client):
    response = client.post(
        "/app-users/",
        json={
            "name": "Ana",
            "email": f"app_user_{uuid4().hex}@example.com",
            "password_hash": "hash",
            "height_cm": 10,
        },
    )

    assert response.status_code == 422


def test_dbapi_error_returns_500(client, db_session, monkeypatch):
    def broken_query(*args, **kwargs):
        raise DBAPIError("SELECT", {}, FakePgError("connection closed", "08006"))

    monkeypatch.setattr(db_session, "query", broken_query)

    response = client.get("/app-users/")

    assert response.status_code == 500
