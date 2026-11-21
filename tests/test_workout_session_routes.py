from datetime import date
from decimal import Decimal
import pytest
from app.models.training_week_model import TrainingWeekModel


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


def session_payload(user_id: int, week_id: int | None = None) -> dict:
    payload = {
        "user_id": user_id,
        "title": "POWERRR",
        "session_date": "2026-11-21",
        "current_bodyweight_kg": 60.5,
        "observation": "sigue adelante",
        "public": False,
        "status": "ABIERTO",
    }
    if week_id is not None:
        payload["week_id"] = week_id
    return payload


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


def test_create_with_missing_user_returns_404(client, test_week):
    response = client.post("/workout-sessions/", json=session_payload(999, test_week.id))

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_with_missing_week_returns_404(client, test_user):
    response = client.post("/workout-sessions/", json=session_payload(test_user.id, 999))

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_rejects_invalid_payload(client, test_user):
    payload = session_payload(test_user.id)
    payload.pop("user_id")

    response = client.post("/workout-sessions/", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "user_id"]


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


def test_delete_workout_session(client, test_user):
    created = client.post("/workout-sessions/", json=session_payload(test_user.id))
    session_id = created.json()["id"]

    deleted = client.delete(f"/workout-sessions/{session_id}")
    assert deleted.status_code == 204

    detail = client.get(f"/workout-sessions/{session_id}")
    assert detail.status_code == 404


@pytest.mark.parametrize(
    "query",
    ["skip=-1", "limit=0", "limit=501"],
)
def test_list_rejects_invalid_pagination(client, query):
    response = client.get(f"/workout-sessions/?{query}")

    assert response.status_code == 422


@pytest.mark.parametrize("query", ["user_id=0", "week_id=0"])
def test_list_accepts_zero_id_filters(client, query):
    response = client.get(f"/workout-sessions/?{query}")

    assert response.status_code == 200
    assert response.json() == []
