from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.database_connection import get_db
from app.main import app
from app.models.app_user_model import AppUserModel
from app.models.workout_model import WorkoutModel


def create_payload(user, **changes):
    return {"name": "Squat", "type": "DINAMICO", "created_by": user.id} | changes


def seed_workouts(db, user, count, **changes):
    records = [WorkoutModel(name=f"Exercise {index}", type="DINAMICO", created_by=user.id, **changes) for index in
               range(count)]
    db.add_all(records)
    db.commit()
    return records


class _FakePgError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None, diag: object = None):
        super().__init__(message)
        self.sqlstate = sqlstate
        self.diag = diag


@pytest.fixture
def client_with_mock_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 0

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, db
    finally:
        app.dependency_overrides.clear()


def test_crud_lifecycle_preserves_deactivated_record(workout_api):
    client, db, user = workout_api
    response = client.post("/workouts/", json=create_payload(user, description="Original"))
    assert response.status_code == 201
    workout_id = response.json()["id"]
    db.execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": workout_id})
    db.commit()
    assert client.get(f"/workouts/{workout_id}").status_code == 200
    updated = client.put(f"/workouts/{workout_id}", json={"name": "Back squat", "description": None})
    assert updated.status_code == 200
    assert updated.json()["description"] is None
    assert updated.json()["type"] == "DINAMICO"
    for _ in range(2):
        response = client.delete(f"/workouts/{workout_id}")
        assert response.status_code == 204
        assert response.content == b""
    assert client.get(f"/workouts/{workout_id}").json()["state"] is False
    assert len(client.get("/workouts/").json()) == 1
    assert client.get("/workouts/?state=true").json() == []
    assert db.execute(text("SELECT COUNT(*) FROM workout_set")).scalar_one() == 1
    assert client.put(f"/workouts/{workout_id}", json={"state": True}).json()["state"] is True


def test_list_filters_and_pagination(workout_api):
    client, db, user = workout_api
    records = seed_workouts(db, user, 3)
    records[1].public = True
    records[2].type = "ISOMETRICO"
    records[2].state = False
    db.commit()
    response = client.get("/workouts/?skip=1&limit=1")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [records[1].id]
    assert len(client.get(f"/workouts/?created_by={user.id}&public=true&type=DINAMICO&state=true").json()) == 1
    assert client.get("/workouts/?state=false&type=ISOMETRICO").json()[0]["id"] == records[2].id
    assert client.get("/workouts/?created_by=999").json() == []


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=501", "created_by=0", "type=INVALID", "state=invalid"])
def test_invalid_query_is_rejected(workout_api, query):
    client, _, _ = workout_api
    assert client.get(f"/workouts/?{query}").status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_unknown_workout_returns_not_found(workout_api, method):
    client, _, _ = workout_api
    options = {"json": {"name": "Missing"}} if method == "put" else {}
    assert getattr(client, method)("/workouts/999", **options).status_code == 404


def test_duplicate_create_and_update_return_conflict(workout_api):
    client, _, user = workout_api
    first = client.post("/workouts/", json=create_payload(user)).json()
    assert client.post("/workouts/", json=create_payload(user)).status_code == 409
    second = client.post("/workouts/", json=create_payload(user, name="Plank")).json()
    assert client.put(f"/workouts/{second['id']}", json={"name": first["name"]}).status_code == 409
    assert client.put(f"/workouts/{first['id']}", json={"name": first["name"]}).status_code == 200


def test_missing_creator_and_invalid_payload(workout_api):
    client, _, user = workout_api
    assert client.post("/workouts/", json=create_payload(user, created_by=999)).status_code == 404
    assert client.post("/workouts/", json=create_payload(user, allow_negative_ballast=True)).status_code == 422
    assert client.post("/workouts/", json=create_payload(user, name=" ")).status_code == 422


def test_partial_flag_update_checks_existing_values(workout_api):
    client, _, user = workout_api
    created = client.post("/workouts/",
                          json=create_payload(user, is_bodyweight=True, allow_negative_ballast=True)).json()
    workout_id = created["id"]
    assert client.put(f"/workouts/{workout_id}", json={"is_bodyweight": False}).status_code == 422
    assert client.get(f"/workouts/{workout_id}").json()["is_bodyweight"] is True
    assert client.put(f"/workouts/{workout_id}",
                      json={"is_bodyweight": False, "allow_negative_ballast": False}).status_code == 200


def test_client_limit_counts_inactive_workouts_and_allows_private_creation(workout_api):
    client, db, user = workout_api
    seed_workouts(db, user, 20, public=True, state=False)
    assert client.post("/workouts/", json=create_payload(user, public=True)).status_code == 409
    assert client.post("/workouts/", json=create_payload(user)).status_code == 201


def test_admin_can_exceed_public_limit(workout_api):
    client, db, user = workout_api
    user.role = "ADMIN"
    db.commit()
    seed_workouts(db, user, 20, public=True)
    assert client.post("/workouts/", json=create_payload(user, public=True)).status_code == 201


def test_publication_reassignment_and_unchanged_visibility(workout_api):
    client, db, user = workout_api
    records = seed_workouts(db, user, 20, public=True)
    assert client.put(f"/workouts/{records[0].id}", json={"public": True}).status_code == 200
    private = client.post("/workouts/", json=create_payload(user)).json()
    assert client.put(f"/workouts/{private['id']}", json={"public": True}).status_code == 409
    other = AppUserModel(name="Other", email="other@example.com", password_hash="test", role="ADMIN", status="ACTIVO")
    db.add(other)
    db.commit()
    foreign = client.post("/workouts/", json=create_payload(other, name="Other exercise", public=True)).json()
    assert client.put(f"/workouts/{foreign['id']}", json={"created_by": user.id}).status_code == 409
    assert client.put(f"/workouts/{foreign['id']}", json={"created_by": 999}).status_code == 404


def test_type_change_requires_no_recorded_sets(workout_api):
    client, db, user = workout_api
    created = client.post("/workouts/", json=create_payload(user)).json()
    workout_id = created["id"]
    assert client.put(f"/workouts/{workout_id}", json={"type": "ISOMETRICO"}).status_code == 200
    db.execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": workout_id})
    db.commit()
    assert client.put(f"/workouts/{workout_id}", json={"type": "DINAMICO"}).status_code == 409


def test_anonymized_workout_can_be_read_and_edited(workout_api):
    client, db, user = workout_api
    record = seed_workouts(db, user, 1)[0]
    record.created_by = None
    db.commit()
    assert client.get(f"/workouts/{record.id}").json()["created_by"] is None
    assert client.put(f"/workouts/{record.id}", json={"description": "Updated"}).status_code == 200


def test_integrity_error_unique_returns_409(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="CLIENTE")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("duplicate key value violates unique constraint", "23505")
    )

    response = client.post("/workouts/", json={"name": "Squat", "type": "DINAMICO", "created_by": 1})
    assert response.status_code == 409
    assert "registro ya existe" in response.json().get("detail", "") or "ya existe un ejercicio" in response.json().get("detail", "")


def test_integrity_error_foreign_key_returns_409(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="CLIENTE")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("violates foreign key constraint", "23503")
    )

    response = client.post("/workouts/", json={"name": "Squat", "type": "DINAMICO", "created_by": 1})
    assert response.status_code == 409


def test_integrity_error_check_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="CLIENTE")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("violates check constraint", "23514")
    )

    response = client.post("/workouts/", json={"name": "Squat", "type": "DINAMICO", "created_by": 1})
    assert response.status_code == 422


@pytest.mark.parametrize("diagnostic", [
    SimpleNamespace(constraint_name="workout_public_limit", context=None),
    SimpleNamespace(constraint_name=None, context="PL/pgSQL function fn_workout_client_limit()"),
])
def test_trigger_public_limit_returns_409(client_with_mock_db, diagnostic):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="CLIENTE")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = DBAPIError("INSERT", {}, _FakePgError("limit reached", "P0001", diagnostic))

    response = client.post("/workouts/", json={"name": "Squat", "type": "DINAMICO", "created_by": 1, "public": True})
    assert response.status_code == 409


def test_dbapi_error_returns_500(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError("SELECT", {}, _FakePgError("connection failure", "08006"))

    response = client.get("/workouts/")
    assert response.status_code == 500
    assert "private" not in response.json().get("detail", "").lower()
