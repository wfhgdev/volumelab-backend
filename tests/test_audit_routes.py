from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from app.core.database_connection import get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.models.app_user_model import AppUserModel


class _FakePgError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None):
        super().__init__(message)
        self.sqlstate = sqlstate


@pytest.fixture
def client_with_mock_db():
    db = MagicMock()

    admin = AppUserModel(
        id=1,
        email="admin@volumelab.com",
        name="Admin",
        lastname="System",
        password_hash="...",
        role="ADMIN",
        status="ACTIVO",
    )

    def override_get_db():
        yield db

    def override_current_user():
        return admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, db
    finally:
        app.dependency_overrides.clear()


def test_list_audits_rejects_negative_skip(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get("/audits/?skip=-1")
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 501])
def test_list_audits_rejects_invalid_limit(client_with_mock_db, limit):
    client, _ = client_with_mock_db
    response = client.get(f"/audits/?limit={limit}")
    assert response.status_code == 422


def test_list_audits_rejects_invalid_action_query(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get("/audits/?action=SELECT")
    assert response.status_code == 422


def test_list_audits_rejects_inverted_date_range_with_400(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get(
        "/audits/?date_from=2026-11-22T00:00:00&date_to=2026-11-20T00:00:00"
    )
    assert response.status_code == 400


def test_get_audit_rejects_non_positive_id(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.get("/audits/0")
    assert response.status_code == 422


def test_post_audit_not_allowed(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.post("/audits/", json={})
    assert response.status_code == 405


def test_put_audit_not_allowed(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.put("/audits/1", json={})
    assert response.status_code == 405


def test_delete_audit_not_allowed(client_with_mock_db):
    client, _ = client_with_mock_db
    response = client.delete("/audits/1")
    assert response.status_code == 405


def test_dbapi_error_invalid_enum_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError(
        "SELECT",
        {},
        _FakePgError("invalid input value for enum audit_action", "22P02"),
    )

    response = client.get("/audits/")
    assert response.status_code == 422


def test_dbapi_error_returns_500(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError(
        "SELECT", {}, _FakePgError("connection closed", "08006")
    )

    response = client.get("/audits/")
    assert response.status_code == 500
