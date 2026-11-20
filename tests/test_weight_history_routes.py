from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.database_connection import get_db
from app.main import app


class _FakePgError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None):
        super().__init__(message)
        self.sqlstate = sqlstate


@pytest.fixture
def client_with_mock_db():
    db = MagicMock()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, db
    finally:
        app.dependency_overrides.clear()


def test_list_weight_history_rejects_negative_skip(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get("/weight-history/?skip=-1")
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 501])
def test_list_weight_history_rejects_invalid_limit(client_with_mock_db, limit):
    client, _ = client_with_mock_db
    response = client.get(f"/weight-history/?limit={limit}")
    assert response.status_code == 422


def test_list_weight_history_rejects_non_positive_user_id(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get("/weight-history/?user_id=0")
    assert response.status_code == 422


def test_integrity_error_foreign_key_returns_409(client_with_mock_db):
    client, db = client_with_mock_db
    db.execute.return_value.first.return_value = (1,)
    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        _FakePgError("insert or update on table weight_history violates foreign key constraint", "23503"),
    )

    response = client.post(
        "/weight-history/",
        json={"user_id": 1, "weight_kg": 75.5},
    )
    assert response.status_code == 409


def test_integrity_error_check_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.execute.return_value.first.return_value = (1,)
    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        _FakePgError("new row violates check constraint chk_weight_kg", "23514"),
    )

    response = client.post(
        "/weight-history/",
        json={"user_id": 1, "weight_kg": 75.5},
    )
    assert response.status_code == 422


def test_integrity_error_not_null_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.execute.return_value.first.return_value = (1,)
    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        _FakePgError("null value in column weight_kg violates not-null constraint", "23502"),
    )

    response = client.post(
        "/weight-history/",
        json={"user_id": 1, "weight_kg": 75.5},
    )
    assert response.status_code == 422


def test_dbapi_error_invalid_type_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError(
        "SELECT", {}, _FakePgError("invalid input syntax", "22P02")
    )

    response = client.get("/weight-history/")
    assert response.status_code == 422


def test_dbapi_error_returns_500(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError(
        "SELECT", {}, _FakePgError("connection closed", "08006")
    )

    response = client.get("/weight-history/")
    assert response.status_code == 500
