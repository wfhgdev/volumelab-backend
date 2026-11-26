from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from app.core.permissions import ensure_owner_or_admin, is_admin, resolve_owner_id
from app.core.security import create_access_token
from app.models.workout_model import ExerciseType, WorkoutModel


@pytest.mark.parametrize("role, expected", [("ADMIN", True), ("CLIENTE", False)])
def test_is_admin_matches_persisted_role(role, expected):
    assert is_admin(SimpleNamespace(role=role)) is expected


@pytest.mark.parametrize("role, requested_id, expected_id", [
    ("ADMIN", None, 10), ("ADMIN", 20, 20),
    ("CLIENTE", None, 10), ("CLIENTE", 10, 10),
])
def test_resolve_owner_id_accepts_authorized_ownership(role, requested_id, expected_id):
    user = SimpleNamespace(id=10, role=role)
    assert resolve_owner_id(user, requested_id) == expected_id


def test_resolve_owner_id_rejects_client_impersonation():
    with pytest.raises(HTTPException) as error:
        resolve_owner_id(SimpleNamespace(id=10, role="CLIENTE"), 20)
    assert error.value.status_code == 403


@pytest.mark.parametrize("role, owner_id, is_private", [
    ("ADMIN", 20, True), ("ADMIN", None, True), ("ADMIN", 20, False),
    ("CLIENTE", 10, True), ("CLIENTE", 10, False),
])
def test_owner_or_admin_accepts_authorized_access(role, owner_id, is_private):
    ensure_owner_or_admin(SimpleNamespace(id=10, role=role), owner_id, is_private)


@pytest.mark.parametrize("owner_id", [20, None])
@pytest.mark.parametrize("is_private, expected_status", [(True, 404), (False, 403)])
def test_owner_or_admin_hides_private_resources(owner_id, is_private, expected_status):
    with pytest.raises(HTTPException) as error:
        ensure_owner_or_admin(SimpleNamespace(id=10, role="CLIENTE"), owner_id, is_private)
    assert error.value.status_code == expected_status


@pytest.mark.parametrize("path", [
    "/auth/me", "/app-users/", "/audits/", "/workouts/", "/muscle-groups/",
    "/muscle-workouts/", "/mesocycles/", "/training-weeks/", "/weight-history/",
    "/workout-sessions/", "/workout-sets/", "/workout-rates/", "/session-rates/",
])
def test_protected_routes_require_authentication(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/app-users/", "/audits/"])
def test_client_cannot_read_admin_resources(user_client, path):
    assert user_client.get(path).status_code == 403


@pytest.mark.parametrize("path", ["/app-users/", "/audits/"])
def test_admin_can_read_admin_resources(admin_client, path):
    assert admin_client.get(path).status_code == 200


def test_authenticated_clients_keep_independent_identities(admin_client, user_client, admin_user, client_user):
    assert admin_client is not user_client
    admin_response = admin_client.get("/auth/me")
    user_response = user_client.get("/auth/me")
    assert admin_response.status_code == user_response.status_code == 200
    assert admin_response.json()["id"] == admin_user.id
    assert admin_response.json()["role"] == "ADMIN"
    assert user_response.json()["id"] == client_user.id
    assert user_response.json()["role"] == "CLIENTE"


def test_client_cannot_escalate_privileges_through_token_claims(client, client_user):
    token = create_access_token(client_user.id, "ADMIN")
    response = client.get("/app-users/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_demotion_takes_effect_for_existing_token(admin_client, admin_user, db_session):
    admin_user.role = "CLIENTE"
    db_session.commit()
    assert admin_client.get("/app-users/").status_code == 403


def test_blocking_user_revokes_access_with_existing_token(user_client, client_user, db_session):
    client_user.status = "BLOQUEADO"
    db_session.commit()
    response = user_client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_deleted_user_cannot_reuse_existing_token(user_client, client_user, db_session):
    db_session.delete(client_user)
    db_session.commit()
    assert user_client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("method, path, payload", [
    ("POST", "/muscle-groups/", {"name": "Protected group"}),
    ("PUT", "/muscle-groups/999999999", {"description": "Updated group"}),
    ("DELETE", "/muscle-groups/999999999", None),
])
def test_client_cannot_modify_admin_catalog(user_client, method, path, payload):
    response = user_client.request(method, path, json=payload)
    assert response.status_code == 403


@pytest.fixture
def private_workout(db_session, other_client_user):
    workout = WorkoutModel(name="Private exercise", type=ExerciseType.DYNAMIC, created_by=other_client_user.id)
    db_session.add(workout)
    db_session.commit()
    return workout


def test_client_cannot_read_other_private_workout(user_client, private_workout):
    assert user_client.get(f"/workouts/{private_workout.id}").status_code == 404


def test_client_lists_only_owned_and_public_workouts(user_client, client_user, private_workout, db_session):
    owned = WorkoutModel(name="Owned exercise", type=ExerciseType.DYNAMIC, created_by=client_user.id)
    public = WorkoutModel(
        name="Public exercise", type=ExerciseType.DYNAMIC, public=True, created_by=private_workout.created_by,
    )
    db_session.add_all([owned, public])
    db_session.commit()
    response = user_client.get("/workouts/")
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {owned.id, public.id}


def test_client_cannot_modify_other_public_workout(user_client, private_workout, db_session):
    private_workout.public = True
    db_session.commit()
    assert user_client.get(f"/workouts/{private_workout.id}").status_code == 200
    response = user_client.put(f"/workouts/{private_workout.id}", json={"name": "Unauthorized change"})
    assert response.status_code == 403


def test_admin_can_manage_other_private_workout(admin_client, private_workout):
    assert admin_client.get(f"/workouts/{private_workout.id}").status_code == 200
    response = admin_client.put(f"/workouts/{private_workout.id}", json={"name": "Reviewed exercise"})
    assert response.status_code == 200
    assert response.json()["name"] == "Reviewed exercise"


def test_client_cannot_create_workout_for_another_user(user_client, other_client_user):
    response = user_client.post("/workouts/", json={
        "name": "Impersonated exercise", "type": "DINAMICO", "created_by": other_client_user.id,
    })
    assert response.status_code == 403
