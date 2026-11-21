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


def test_list_session_rates_rejects_negative_skip(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get("/session-rates/?skip=-1")
    assert response.status_code == 422


def test_create_session_rate_integrity_unique_returns_409(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("duplicate key value violates unique constraint uq_session_rate_user", "23505")
    )

    response = client.post(
        "/session-rates/",
        json={"id_workout_session": 10, "user_id": 1, "rate": 5},
    )
    assert response.status_code == 409


def test_create_session_rate_foreign_key_session_returns_404(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("violates foreign key constraint fk_session_rate_session", "23503")
    )

    response = client.post(
        "/session-rates/",
        json={"id_workout_session": 999, "user_id": 1, "rate": 5},
    )
    assert response.status_code == 404


def test_create_session_rate_private_session_returns_400(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = DBAPIError(
        "INSERT", {}, _FakePgError("La sesión 10 no es pública y no se puede valorar", "P0001")
    )

    response = client.post(
        "/session-rates/",
        json={"id_workout_session": 10, "user_id": 1, "rate": 5},
    )
    assert response.status_code == 400
    assert "no es pública" in response.json()["detail"]


def test_create_session_rate_validation_error_returns_422(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.post(
        "/session-rates/",
        json={"id_workout_session": 10, "user_id": 1, "rate": 7},
    )
    assert response.status_code == 422
