import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

import app.controllers.weight_history_controller as weight_history_controller
from app.core.exception_handlers import db_error_handler, integrity_error_handler
from tests.conftest import create_auth_headers


@pytest.fixture(autouse=True)
def authenticate_client(client, admin_user):
    client.headers.update(create_auth_headers(admin_user))


class FakePgError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None):
        super().__init__(message)
        self.sqlstate = sqlstate


def test_list_weight_history_rejects_negative_skip(client):
    response = client.get("/weight-history/?skip=-1")
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 501])
def test_list_weight_history_rejects_invalid_limit(client, limit):
    response = client.get(f"/weight-history/?limit={limit}")
    assert response.status_code == 422


def test_list_weight_history_rejects_non_positive_user_id(client):
    response = client.get("/weight-history/?user_id=0")
    assert response.status_code == 422


def test_create_weight_history_returns_201(client, test_user):
    response = client.post(
        "/weight-history/",
        json={"user_id": test_user.id, "weight_kg": 75.5},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == test_user.id


def test_create_weight_history_missing_user_returns_404(client):
    response = client.post(
        "/weight-history/",
        json={"user_id": 2_000_000_000, "weight_kg": 75.5},
    )

    assert response.status_code == 404


def test_integrity_error_foreign_key_returns_409(client, monkeypatch):
    monkeypatch.setattr(
        weight_history_controller, "_ensure_user_exists", lambda db, user_id: None
    )

    response = client.post(
        "/weight-history/",
        json={"user_id": 2_000_000_000, "weight_kg": 75.5},
    )

    assert response.status_code == 409


def test_integrity_error_check_returns_422(db_session, test_user):
    with pytest.raises(IntegrityError) as exc:
        db_session.execute(
            text(
                "INSERT INTO weight_history (user_id, weight_kg) "
                "VALUES (:user_id, 0)"
            ),
            {"user_id": test_user.id},
        )

    response = asyncio.run(integrity_error_handler(None, exc.value))

    assert response.status_code == 422
    db_session.rollback()


def test_integrity_error_not_null_returns_422(db_session, test_user):
    with pytest.raises(IntegrityError) as exc:
        db_session.execute(
            text(
                "INSERT INTO weight_history (user_id, weight_kg) "
                "VALUES (:user_id, NULL)"
            ),
            {"user_id": test_user.id},
        )

    response = asyncio.run(integrity_error_handler(None, exc.value))

    assert response.status_code == 422
    db_session.rollback()


def test_dbapi_error_invalid_type_returns_422():
    exc = DBAPIError("SELECT", {}, FakePgError("invalid input syntax", "22P02"))

    response = asyncio.run(db_error_handler(None, exc))

    assert response.status_code == 422


def test_dbapi_error_returns_500(client, db_session, monkeypatch):
    def broken_query(*args, **kwargs):
        raise DBAPIError("SELECT", {}, FakePgError("connection closed", "08006"))

    monkeypatch.setattr(db_session, "query", broken_query)

    response = client.get("/weight-history/")

    assert response.status_code == 500
