from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.models.workout_session_model import SessionStatus, WorkoutSessionModel


def create_session(db_session, user_id: int, public: bool = True) -> WorkoutSessionModel:
    session = WorkoutSessionModel(
        user_id=user_id,
        title=f"Session {uuid4().hex}",
        session_date=date(2026, 1, 1),
        current_bodyweight_kg=Decimal("70.00"),
        public=public,
        status=SessionStatus.ABIERTO,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def test_list_session_rates_rejects_negative_skip(client):
    response = client.get("/session-rates/?skip=-1")
    assert response.status_code == 422


def test_create_session_rate_duplicate_returns_409(client, db_session, test_user):
    session = create_session(db_session, test_user.id)
    payload = {"id_workout_session": session.id, "user_id": test_user.id, "rate": 5}

    assert client.post("/session-rates/", json=payload).status_code == 201

    response = client.post("/session-rates/", json={**payload, "rate": 4})

    assert response.status_code == 409


def test_create_session_rate_missing_session_returns_400(
    client, db_session, test_user
):
    response = client.post(
        "/session-rates/",
        json={
            "id_workout_session": 2_000_000_000,
            "user_id": test_user.id,
            "rate": 5,
        },
    )

    assert response.status_code == 400
    assert "no es pública" in response.json()["detail"]


def test_create_session_rate_private_session_returns_400(client, db_session, test_user):
    session = create_session(db_session, test_user.id, public=False)

    response = client.post(
        "/session-rates/",
        json={
            "id_workout_session": session.id,
            "user_id": test_user.id,
            "rate": 5,
        },
    )

    assert response.status_code == 400
    assert "no es pública" in response.json()["detail"]


def test_create_session_rate_validation_error_returns_422(client, db_session, test_user):
    session = create_session(db_session, test_user.id)

    response = client.post(
        "/session-rates/",
        json={
            "id_workout_session": session.id,
            "user_id": test_user.id,
            "rate": 7,
        },
    )

    assert response.status_code == 422
