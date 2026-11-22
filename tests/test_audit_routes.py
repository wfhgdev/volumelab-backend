import logging
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


def test_integrity_error_foreign_key_returns_409_and_logs_warning(client_with_mock_db, caplog):
    client, db = client_with_mock_db
    db.execute.return_value.first.return_value = (1,)
    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        _FakePgError(
            "insert or update on table audit violates foreign key constraint fk_audit_user",
            "23503",
        ),
    )

    with caplog.at_level(logging.WARNING, logger="volumelab.audit"):
        response = client.post(
            "/audits/",
            json={
                "user_id": 1,
                "entity": "workout_session",
                "record_id": "10",
                "action": "INSERT",
            },
        )
    assert response.status_code == 409
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_integrity_error_not_null_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        _FakePgError("null value in column entity violates not-null constraint", "23502"),
    )

    response = client.post(
        "/audits/",
        json={
            "entity": "workout_session",
            "record_id": "10",
            "action": "INSERT",
        },
    )
    assert response.status_code == 422


def test_dbapi_error_invalid_enum_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError(
        "SELECT",
        {},
        _FakePgError("invalid input value for enum audit_action", "22P02"),
    )

    response = client.get("/audits/")
    assert response.status_code == 422


def test_dbapi_error_returns_500_and_logs_error(client_with_mock_db, caplog):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError(
        "SELECT", {}, _FakePgError("connection closed", "08006")
    )

    with caplog.at_level(logging.ERROR, logger="volumelab.audit"):
        response = client.get("/audits/")
    assert response.status_code == 500
    assert any(r.levelno == logging.ERROR for r in caplog.records)
