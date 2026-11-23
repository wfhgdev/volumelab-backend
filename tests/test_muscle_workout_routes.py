from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.database_connection import get_db
from app.main import app
from app.models.muscle_group_model import MuscleGroupModel
from app.models.muscle_workout_model import MuscleWorkoutModel
from app.models.workout_model import WorkoutModel


def request_payload(workout, group, **changes):
    return {"workout_id": workout.id, "muscle_group_id": group.id, "muscle_role": "PRIMARIO"} | changes


class _FakePgError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None, diag: object = None):
        super().__init__(message)
        self.sqlstate = sqlstate
        self.diag = diag


@pytest.fixture
def client_with_mock_db():
    db = MagicMock()
    # Mock workout and muscle group exist for create validations
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    inspector = MagicMock()
    inspector.has_table.return_value = False

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, db, inspector
    finally:
        app.dependency_overrides.clear()


def test_crud_uses_composite_key_and_preserves_parents(association_api):
    client, db, workout, group = association_api
    response = client.post("/muscle-workouts/", json=request_payload(workout, group))
    assert response.status_code == 201
    assert response.json() == request_payload(workout, group, weighing=100)
    resource = f"/muscle-workouts/{workout.id}/{group.id}"
    assert client.get(resource).status_code == 200
    response = client.put(resource, json={"muscle_role": "SECUNDARIO"})
    assert response.status_code == 200
    assert response.json()["weighing"] == 50
    assert client.put(resource, json={"weighing": 50}).status_code == 200
    assert client.put(resource, json={"weighing": 100}).status_code == 422
    assert client.get(resource).json()["weighing"] == 50
    response = client.delete(resource)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(resource).status_code == 404
    assert client.delete(resource).status_code == 404
    assert db.get(WorkoutModel, workout.id) is not None
    assert db.get(MuscleGroupModel, group.id) is not None


@pytest.mark.parametrize(("role", "weight"), [("PRIMARIO", 100), ("SECUNDARIO", 50), ("TERCIARIO", 10)])
def test_creation_calculates_each_weight(association_api, role, weight):
    client, _, workout, group = association_api
    response = client.post("/muscle-workouts/", json=request_payload(workout, group, muscle_role=role))
    assert response.status_code == 201
    assert response.json()["weighing"] == weight


def test_creation_rejects_duplicate_pair_and_missing_references(association_api):
    client, _, workout, group = association_api
    assert client.post("/muscle-workouts/", json=request_payload(workout, group, workout_id=999)).status_code == 404
    assert client.post("/muscle-workouts/", json=request_payload(workout, group, muscle_group_id=999)).status_code == 404
    assert client.post("/muscle-workouts/", json=request_payload(workout, group)).status_code == 201
    assert client.post("/muscle-workouts/", json=request_payload(workout, group)).status_code == 409


@pytest.mark.parametrize("changes", [
    {"workout_id": 0}, {"muscle_group_id": 0}, {"muscle_role": "INVALID"},
    {"weighing": 50}, {"weighing": None}, {"weighing": "100"}, {"id": 1},
])
def test_invalid_creation_is_rejected(association_api, changes):
    client, _, workout, group = association_api
    assert client.post("/muscle-workouts/", json=request_payload(workout, group, **changes)).status_code == 422


@pytest.mark.parametrize("operation", ["post", "put", "delete"])
def test_recorded_sets_block_writes_and_keep_association(association_api, operation):
    client, db, workout, group = association_api
    original = client.post("/muscle-workouts/", json=request_payload(workout, group)).json()
    db.execute(text("INSERT INTO workout_set (exercise_id) VALUES (:id)"), {"id": workout.id})
    db.commit()
    resource = f"/muscle-workouts/{workout.id}/{group.id}"
    if operation == "post":
        other = MuscleGroupModel(name="Other", created_by=group.created_by)
        db.add(other)
        db.commit()
        response = client.post("/muscle-workouts/", json=request_payload(workout, other))
    elif operation == "put":
        response = client.put(resource, json={"muscle_role": "TERCIARIO"})
    else:
        response = client.delete(resource)
    assert response.status_code == 409
    assert client.get(resource).json() == original
    assert db.query(MuscleWorkoutModel).count() == 1
    assert db.execute(text("SELECT COUNT(*) FROM workout_set")).scalar_one() == 1


def test_creation_works_without_series_table(association_api):
    client, db, workout, group = association_api
    db.execute(text("DROP TABLE workout_set"))
    db.commit()
    assert client.post("/muscle-workouts/", json=request_payload(workout, group)).status_code == 201
    db.execute(text("CREATE TEMP TABLE workout_set (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, exercise_id INTEGER NOT NULL)"))
    db.commit()


def test_filters_order_and_weights_do_not_require_total_of_one_hundred(association_api):
    client, db, workout, group = association_api
    assert client.get("/muscle-workouts/").json() == []
    other = MuscleGroupModel(name="Other", created_by=group.created_by)
    db.add(other)
    db.commit()
    assert client.post("/muscle-workouts/", json=request_payload(workout, group)).status_code == 201
    assert client.post("/muscle-workouts/", json=request_payload(workout, other)).status_code == 201
    response = client.get(f"/muscle-workouts/?workout_id={workout.id}&muscle_role=PRIMARIO")
    assert len(response.json()) == 2
    assert sum(item["weighing"] for item in response.json()) == 200
    assert client.get("/muscle-workouts/?skip=1&limit=1").json()[0]["muscle_group_id"] == other.id
    assert len(client.get(f"/muscle-workouts/?muscle_group_id={group.id}").json()) == 1
    assert client.get("/muscle-workouts/?muscle_role=TERCIARIO").json() == []


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=501", "workout_id=0", "muscle_group_id=0", "muscle_role=INVALID"])
def test_invalid_query_is_rejected(association_api, query):
    client, _, _, _ = association_api
    assert client.get(f"/muscle-workouts/?{query}").status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_association_and_invalid_path(association_api, method):
    client, _, workout, _ = association_api
    options = {"json": {"muscle_role": "PRIMARIO"}} if method == "put" else {}
    assert getattr(client, method)(f"/muscle-workouts/{workout.id}/999", **options).status_code == 404
    assert getattr(client, method)("/muscle-workouts/0/1", **options).status_code == 422


def test_update_rejects_key_changes_and_inconsistent_weight(association_api):
    client, _, workout, group = association_api
    original = client.post("/muscle-workouts/", json=request_payload(workout, group)).json()
    resource = f"/muscle-workouts/{workout.id}/{group.id}"
    for changes in ({"workout_id": 2}, {"muscle_group_id": 2}, {"muscle_role": None}, {"muscle_role": "SECUNDARIO", "weighing": 100}):
        assert client.put(resource, json=changes).status_code == 422
        assert client.get(resource).json() == original


def test_integrity_error_unique_returns_409(client_with_mock_db, monkeypatch):
    client, db, inspector = client_with_mock_db
    monkeypatch.setattr("app.controllers.muscle_workout_controller.inspect", lambda bind: inspector)
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("duplicate key value violates unique constraint", "23505")
    )

    response = client.post("/muscle-workouts/", json={"workout_id": 1, "muscle_group_id": 2, "muscle_role": "PRIMARIO"})
    assert response.status_code == 409


def test_integrity_error_foreign_key_returns_409(client_with_mock_db, monkeypatch):
    client, db, inspector = client_with_mock_db
    monkeypatch.setattr("app.controllers.muscle_workout_controller.inspect", lambda bind: inspector)
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("violates foreign key constraint", "23503")
    )

    response = client.post("/muscle-workouts/", json={"workout_id": 1, "muscle_group_id": 2, "muscle_role": "PRIMARIO"})
    assert response.status_code == 409


def test_integrity_error_check_returns_422(client_with_mock_db, monkeypatch):
    client, db, inspector = client_with_mock_db
    monkeypatch.setattr("app.controllers.muscle_workout_controller.inspect", lambda bind: inspector)
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("violates check constraint", "23514")
    )

    response = client.post("/muscle-workouts/", json={"workout_id": 1, "muscle_group_id": 2, "muscle_role": "PRIMARIO"})
    assert response.status_code == 422


def test_dbapi_error_returns_500(client_with_mock_db):
    client, db, _ = client_with_mock_db
    db.query.side_effect = DBAPIError("SELECT", {}, _FakePgError("connection failure", "08006"))

    response = client.get("/muscle-workouts/")
    assert response.status_code == 500
    assert "private" not in response.json().get("detail", "").lower()
