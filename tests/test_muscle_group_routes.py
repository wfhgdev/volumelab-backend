from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.database_connection import get_db
from app.main import app
from app.models.app_user_model import AppUserModel
from app.models.muscle_group_model import MuscleGroupModel
from tests.catalog_support import associate_group


def payload(creator, **changes):
    return {"name": "Chest", "created_by": creator.id} | changes


class _FakePgError(Exception):
    def __init__(self, message: str, sqlstate: str | None = None, diag: object = None):
        super().__init__(message)
        self.sqlstate = sqlstate
        self.diag = diag


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


def test_crud_lifecycle_and_physical_deletion(muscle_group_api):
    client, db, admin = muscle_group_api
    response = client.post("/muscle-groups/", json=payload(admin, description="Original"))
    assert response.status_code == 201
    record = response.json()
    assert set(record) == {"id", "name", "description", "created_by"}
    resource = f"/muscle-groups/{record['id']}"
    assert client.get(resource).json() == record
    response = client.put(resource, json={"name": "Pectorals", "description": None})
    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["created_by"] == admin.id
    response = client.delete(resource)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(resource).status_code == 404
    assert client.delete(resource).status_code == 404
    assert db.get(MuscleGroupModel, record["id"]) is None


def test_creation_by_client_is_forbidden(muscle_group_api):
    client, db, admin = muscle_group_api
    admin.role = "CLIENTE"
    db.commit()
    assert client.post("/muscle-groups/", json=payload(admin)).status_code == 403


def test_creation_requires_existing_administrator(muscle_group_api):
    client, _, admin = muscle_group_api
    assert client.post("/muscle-groups/", json=payload(admin, created_by=999)).status_code == 404
    assert client.post("/muscle-groups/", json={"name": "Chest"}).status_code == 422


def test_duplicates_are_rejected_on_create_and_update(muscle_group_api):
    client, _, admin = muscle_group_api
    first = client.post("/muscle-groups/", json=payload(admin)).json()
    assert client.post("/muscle-groups/", json=payload(admin, name="  Chest  ")).status_code == 409
    second = client.post("/muscle-groups/", json=payload(admin, name="Back")).json()
    assert client.put(f"/muscle-groups/{second['id']}", json={"name": "Chest"}).status_code == 409
    assert client.put(f"/muscle-groups/{first['id']}", json={"name": "Chest"}).status_code == 200


def test_name_uniqueness_keeps_database_case_sensitivity(muscle_group_api):
    client, _, admin = muscle_group_api
    assert client.post("/muscle-groups/", json=payload(admin)).status_code == 201
    assert client.post("/muscle-groups/", json=payload(admin, name="chest")).status_code == 201


def test_deletion_protects_all_associations(muscle_group_api):
    client, db, admin = muscle_group_api
    record = client.post("/muscle-groups/", json=payload(admin)).json()
    associate_group(db, record["id"], admin.id, count=2)
    resource = f"/muscle-groups/{record['id']}"
    assert client.delete(resource).status_code == 409
    assert client.get(resource).json() == record
    assert db.execute(text("SELECT COUNT(*) FROM muscle_workout")).scalar_one() == 2


def test_deletion_supports_schema_without_association_table(muscle_group_api):
    client, db, admin = muscle_group_api
    record = client.post("/muscle-groups/", json=payload(admin)).json()
    db.execute(text("DROP TABLE muscle_workout"))
    db.commit()
    assert client.delete(f"/muscle-groups/{record['id']}").status_code == 204


def test_creator_reassignment_requires_an_administrator(muscle_group_api):
    client, db, admin = muscle_group_api
    record = client.post("/muscle-groups/", json=payload(admin)).json()
    other = AppUserModel(name="Other", email="other@example.com", password_hash="test", role="CLIENTE", status="ACTIVO")
    db.add(other)
    db.commit()
    resource = f"/muscle-groups/{record['id']}"
    assert client.put(resource, json={"created_by": other.id}).status_code == 403
    assert client.put(resource, json={"created_by": 999}).status_code == 404
    other.role = "ADMIN"
    db.commit()
    assert client.put(resource, json={"created_by": other.id}).json()["created_by"] == other.id


def test_list_pagination_filters_and_empty_result(muscle_group_api):
    client, db, admin = muscle_group_api
    assert client.get("/muscle-groups/").json() == []
    records = [MuscleGroupModel(name=name, created_by=admin.id) for name in ("Chest", "Back", "Legs")]
    db.add_all(records)
    db.commit()
    response = client.get("/muscle-groups/?skip=1&limit=1")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [records[1].id]
    assert len(client.get(f"/muscle-groups/?created_by={admin.id}").json()) == 3
    assert client.get("/muscle-groups/?created_by=999").json() == []


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=501", "created_by=0"])
def test_invalid_query_returns_validation_error(muscle_group_api, query):
    client, _, _ = muscle_group_api
    assert client.get(f"/muscle-groups/?{query}").status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete"])
@pytest.mark.parametrize(("identifier", "status"), [(999, 404), (0, 422)])
def test_invalid_and_unknown_identifiers(muscle_group_api, method, identifier, status):
    client, _, _ = muscle_group_api
    options = {"json": {"description": "Updated"}} if method == "put" else {}
    assert getattr(client, method)(f"/muscle-groups/{identifier}", **options).status_code == status


def test_anonymized_group_can_be_read_and_updated(muscle_group_api):
    client, db, _ = muscle_group_api
    record = MuscleGroupModel(name="Chest", created_by=None)
    db.add(record)
    db.commit()
    resource = f"/muscle-groups/{record.id}"
    assert client.get(resource).json()["created_by"] is None
    response = client.put(resource, json={"description": "Preserved"})
    assert response.status_code == 200
    assert response.json()["created_by"] is None


@pytest.mark.parametrize("changes", [{"name": None}, {"created_by": None}, {"name": " "}, {"state": True}])
def test_invalid_update_keeps_existing_record(muscle_group_api, changes):
    client, _, admin = muscle_group_api
    record = client.post("/muscle-groups/", json=payload(admin)).json()
    resource = f"/muscle-groups/{record['id']}"
    assert client.put(resource, json=changes).status_code == 422
    assert client.get(resource).json() == record


def test_integrity_error_unique_returns_409(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="ADMIN")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("duplicate key value violates unique constraint", "23505")
    )

    response = client.post("/muscle-groups/", json={"name": "Chest", "created_by": 1})
    assert response.status_code == 409
    assert "registro ya existe" in response.json().get("detail", "") or "ya existe un grupo muscular" in response.json().get("detail", "")


def test_integrity_error_foreign_key_returns_409(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="ADMIN")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("violates foreign key constraint", "23503")
    )

    response = client.post("/muscle-groups/", json={"name": "Chest", "created_by": 1})
    assert response.status_code == 409


def test_integrity_error_check_returns_422(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="ADMIN")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, _FakePgError("violates check constraint", "23514")
    )

    response = client.post("/muscle-groups/", json={"name": "Chest", "created_by": 1})
    assert response.status_code == 422


@pytest.mark.parametrize("diagnostic", [
    SimpleNamespace(constraint_name="muscle_group_admin_only", context=None),
    SimpleNamespace(constraint_name=None, context="PL/pgSQL function fn_muscle_group_admin_only()"),
])
def test_trigger_admin_only_returns_403(client_with_mock_db, diagnostic):
    client, db = client_with_mock_db
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = AppUserModel(id=1, role="ADMIN")
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = DBAPIError("INSERT", {}, _FakePgError("admin trigger", "P0001", diagnostic))

    response = client.post("/muscle-groups/", json={"name": "Chest", "created_by": 1})
    assert response.status_code == 403


def test_dbapi_error_returns_500(client_with_mock_db):
    client, db = client_with_mock_db
    db.query.side_effect = DBAPIError("SELECT", {}, _FakePgError("connection failure", "08006"))

    response = client.get("/muscle-groups/")
    assert response.status_code == 500
    assert "Private" not in response.json().get("detail", "")
