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


def test_list_app_users_rejects_negative_skip(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get("/app-users/?skip=-1")
    assert response.status_code == 422


def test_integrity_error_unique_returns_409(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("duplicate key value violates unique constraint", "23505")
    )

    response = client.post(
        "/app-users/",
        json={"name": "Ana", "email": "ana@example.com", "password_hash": "hash"},
    )
    assert response.status_code == 409


def test_integrity_error_check_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("new row violates check constraint chk_user_height", "23514")
    )

    response = client.post(
        "/app-users/",
        json={"name": "Ana", "email": "ana@example.com", "password_hash": "hash"},
    )
    assert response.status_code == 422


def test_dbapi_error_returns_500(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError("SELECT", {}, _FakePgError("connection closed", "08006"))

    response = client.get("/app-users/")
    assert response.status_code == 500
