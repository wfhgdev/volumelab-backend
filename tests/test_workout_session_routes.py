from datetime import date
from decimal import Decimal
import pytest
from app.models.app_user_model import AppUserModel, RoleUser
from app.models.mesocycle_model import MesocycleModel
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import WorkoutSessionModel
from tests.conftest import create_auth_headers


@pytest.fixture(autouse=True)
def authenticate_client(client, test_user):
    client.headers.update(create_auth_headers(test_user))


@pytest.fixture
def test_week(db_session, test_mesocycle):
    week = TrainingWeekModel(
        mesocycle_id=test_mesocycle.id,
        week_order=1,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 7),
    )
    db_session.add(week)
    db_session.commit()
    db_session.refresh(week)
    return week


@pytest.fixture
def other_user(db_session):
    user = AppUserModel(
        email="other_user@volumelab.com",
        password_hash="hashed_secret_password",
        name="Otro",
        role=RoleUser.CLIENTE,
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_week(db_session, other_user):
    mesocycle = MesocycleModel(
        user_id=other_user.id,
        name="Mesociclo Ajeno",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
    )
    db_session.add(mesocycle)
    db_session.commit()
    db_session.refresh(mesocycle)

    week = TrainingWeekModel(
        mesocycle_id=mesocycle.id,
        week_order=1,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 7),
    )
    db_session.add(week)
    db_session.commit()
    db_session.refresh(week)
    return week


def session_payload(user_id: int, week_id: int | None = None, public: bool = False) -> dict:
    payload = {
        "user_id": user_id,
        "title": "POWERRR",
        "session_date": "2026-11-21",
        "current_bodyweight_kg": 60.5,
        "observation": "sigue adelante",
        "public": public,
        "status": "ABIERTO",
    }
    if week_id is not None:
        payload["week_id"] = week_id
    return payload


def add_public_sessions(db_session, user_id: int, count: int) -> None:
    for index in range(count):
        db_session.add(
            WorkoutSessionModel(
                user_id=user_id,
                session_date=date(2026, 11, 20),
                public=True,
            )
        )
    db_session.commit()


def test_create_workout_session(client, test_user, test_week):
    response = client.post("/workout-sessions/", json=session_payload(test_user.id, test_week.id))

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == test_user.id
    assert data["week_id"] == test_week.id
    assert data["title"] == "POWERRR"
    assert Decimal(data["current_bodyweight_kg"]) == Decimal("60.50")
    assert data["status"] == "ABIERTO"
    assert data["closed_at"] is None
    assert data["created_at"] is not None


def test_create_with_missing_user_returns_404(client, test_week, admin_user):
    client.headers.update(create_auth_headers(admin_user))
    response = client.post("/workout-sessions/", json=session_payload(999, test_week.id))

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_with_missing_week_returns_404(client, test_user):
    response = client.post("/workout-sessions/", json=session_payload(test_user.id, 999))

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_rejects_week_from_another_user(client, test_user, other_week):
    response = client.post(
        "/workout-sessions/",
        json=session_payload(test_user.id, other_week.id),
    )

    assert response.status_code == 422
    assert "does not belong" in response.json()["detail"]


def test_create_rejects_invalid_payload(client, test_user):
    payload = session_payload(test_user.id)
    payload.pop("session_date")

    response = client.post("/workout-sessions/", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "session_date"]


def test_list_and_get_workout_sessions(client, test_user, test_week):
    created = client.post("/workout-sessions/", json=session_payload(test_user.id, test_week.id))
    session_id = created.json()["id"]

    listed = client.get("/workout-sessions/")
    assert listed.status_code == 200
    assert any(item["id"] == session_id for item in listed.json())

    detail = client.get(f"/workout-sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == session_id


def test_get_unknown_workout_session_returns_404(client):
    response = client.get("/workout-sessions/999")

    assert response.status_code == 404


def test_update_and_close_workout_session(client, test_user):
    created = client.post("/workout-sessions/", json=session_payload(test_user.id))
    session_id = created.json()["id"]

    updated = client.put(
        f"/workout-sessions/{session_id}",
        json={"title": "Cambiado"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Cambiado"

    closed = client.put(
        f"/workout-sessions/{session_id}",
        json={
            "status": "CERRADO",
            "closed_at": "2026-11-21T22:00:00",
        },
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CERRADO"
    assert closed.json()["closed_at"] is not None


def test_update_rejects_explicit_null(client, test_user):
    created = client.post("/workout-sessions/", json=session_payload(test_user.id))
    session_id = created.json()["id"]

    response = client.put(f"/workout-sessions/{session_id}", json={"user_id": None})

    assert response.status_code == 422
    assert "user_id" in str(response.json()["detail"])


def test_update_rejects_week_from_another_user(client, test_user, other_week):
    created = client.post("/workout-sessions/", json=session_payload(test_user.id))
    session_id = created.json()["id"]

    response = client.put(f"/workout-sessions/{session_id}", json={"week_id": other_week.id})

    assert response.status_code == 422


def test_delete_workout_session(client, test_user):
    created = client.post("/workout-sessions/", json=session_payload(test_user.id))
    session_id = created.json()["id"]

    deleted = client.delete(f"/workout-sessions/{session_id}")
    assert deleted.status_code == 204

    detail = client.get(f"/workout-sessions/{session_id}")
    assert detail.status_code == 404


def test_create_rejects_21st_public_session_for_cliente(client, db_session, test_user):
    add_public_sessions(db_session, test_user.id, 20)

    response = client.post(
        "/workout-sessions/",
        json=session_payload(test_user.id, public=True),
    )

    assert response.status_code == 422
    assert "20 public workout sessions" in response.json()["detail"]


def test_create_allows_public_session_for_admin(client, db_session):
    admin = AppUserModel(
        email="admin@volumelab.com",
        password_hash="hashed_secret_password",
        name="Admin",
        role=RoleUser.ADMIN,
        status="ACTIVO",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    client.headers.update(create_auth_headers(admin))
    add_public_sessions(db_session, admin.id, 20)

    response = client.post(
        "/workout-sessions/",
        json=session_payload(admin.id, public=True),
    )

    assert response.status_code == 201


def test_update_rejects_publishing_over_cliente_quota(client, db_session, test_user):
    add_public_sessions(db_session, test_user.id, 20)
    created = client.post("/workout-sessions/", json=session_payload(test_user.id))
    session_id = created.json()["id"]

    response = client.put(f"/workout-sessions/{session_id}", json={"public": True})

    assert response.status_code == 422
    assert "20 public workout sessions" in response.json()["detail"]


def test_update_rejects_reassigning_user_over_public_quota(client, db_session, test_user, other_user, admin_user):
    add_public_sessions(db_session, test_user.id, 20)
    client.headers.update(create_auth_headers(other_user))
    created = client.post(
        "/workout-sessions/",
        json=session_payload(other_user.id, public=True),
    )
    session_id = created.json()["id"]

    client.headers.update(create_auth_headers(admin_user))
    response = client.put(f"/workout-sessions/{session_id}", json={"user_id": test_user.id})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "query",
    ["skip=-1", "limit=0", "limit=501"],
)
def test_list_rejects_invalid_pagination(client, query):
    response = client.get(f"/workout-sessions/?{query}")

    assert response.status_code == 422


@pytest.mark.parametrize("query", ["user_id=0", "week_id=0"])
def test_list_accepts_zero_id_filters(client, query, admin_user):
    client.headers.update(create_auth_headers(admin_user))
    response = client.get(f"/workout-sessions/?{query}")

    assert response.status_code == 200
    assert response.json() == []
