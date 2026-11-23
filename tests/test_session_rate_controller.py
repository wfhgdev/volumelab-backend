from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.controllers.session_rate_controller import (
    create_session_rate,
    delete_session_rate,
    get_session_rate_by_id,
    get_session_rate_by_session_and_user,
    get_session_score,
    update_session_rate,
    upsert_session_rate,
)
from app.models.app_user_model import AppUserModel, RoleUser, UserStatus
from app.models.workout_session_model import SessionStatus, WorkoutSessionModel
from app.schemas.session_rate_schema import SessionRateCreate, SessionRateUpdate


def create_user(db_session) -> AppUserModel:
    user = AppUserModel(
        email=f"session_rate_user_{uuid4().hex}@example.com",
        password_hash="hash",
        name="Rate",
        role=RoleUser.CLIENTE,
        status=UserStatus.ACTIVO,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


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


def create_rate(db_session, session_id: int, user_id: int, rate: int = 5):
    return create_session_rate(
        db_session,
        SessionRateCreate(
            id_workout_session=session_id,
            user_id=user_id,
            rate=rate,
        ),
    )


def test_create_session_rate_persists(db_session, test_user):
    session = create_session(db_session, test_user.id)

    result = create_rate(db_session, session.id, test_user.id)

    assert result.id >= 1
    assert result.id_workout_session == session.id
    assert result.user_id == test_user.id
    assert result.rate == 5


def test_create_session_rate_rejects_duplicate(db_session, test_user):
    session = create_session(db_session, test_user.id)
    create_rate(db_session, session.id, test_user.id, rate=5)

    with pytest.raises(HTTPException) as exc:
        create_rate(db_session, session.id, test_user.id, rate=4)

    assert exc.value.status_code == 409
    assert "ya ha valorado" in exc.value.detail


def test_create_session_rate_catches_private_trigger(db_session, test_user):
    session = create_session(db_session, test_user.id, public=False)

    with pytest.raises(HTTPException) as exc:
        create_rate(db_session, session.id, test_user.id)

    assert exc.value.status_code == 400
    assert "no es pública" in exc.value.detail


def test_get_session_rate_by_id_found(db_session, test_user):
    session = create_session(db_session, test_user.id)
    expected = create_rate(db_session, session.id, test_user.id)

    result = get_session_rate_by_id(db_session, expected.id)

    assert result.id == expected.id


def test_get_session_rate_by_id_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        get_session_rate_by_id(db_session, 2_000_000_000)

    assert exc.value.status_code == 404


def test_get_session_rate_by_session_and_user(db_session, test_user):
    session = create_session(db_session, test_user.id)
    expected = create_rate(db_session, session.id, test_user.id)

    result = get_session_rate_by_session_and_user(
        db_session, session.id, test_user.id
    )

    assert result.id == expected.id
    assert result.id_workout_session == session.id
    assert result.user_id == test_user.id


def test_update_session_rate(db_session, test_user):
    session = create_session(db_session, test_user.id)
    existing = create_rate(db_session, session.id, test_user.id, rate=2)

    result = update_session_rate(
        db_session, existing.id, SessionRateUpdate(rate=5)
    )

    assert result.rate == 5


def test_upsert_session_rate_updates_if_exists(db_session, test_user):
    session = create_session(db_session, test_user.id)
    existing = create_rate(db_session, session.id, test_user.id, rate=2)

    result = upsert_session_rate(
        db_session,
        SessionRateCreate(
            id_workout_session=session.id,
            user_id=test_user.id,
            rate=4,
        ),
    )

    assert result.id == existing.id
    assert result.rate == 4


def test_upsert_session_rate_creates_if_missing(db_session, test_user):
    session = create_session(db_session, test_user.id)

    result = upsert_session_rate(
        db_session,
        SessionRateCreate(
            id_workout_session=session.id,
            user_id=test_user.id,
            rate=4,
        ),
    )

    assert result.id >= 1
    assert result.rate == 4


def test_delete_session_rate(db_session, test_user):
    session = create_session(db_session, test_user.id)
    existing = create_rate(db_session, session.id, test_user.id)

    delete_session_rate(db_session, existing.id)

    with pytest.raises(HTTPException) as exc:
        get_session_rate_by_id(db_session, existing.id)
    assert exc.value.status_code == 404


def test_get_session_score(db_session, test_user):
    other = create_user(db_session)
    session = create_session(db_session, test_user.id)
    create_rate(db_session, session.id, test_user.id, rate=4)
    create_rate(db_session, session.id, other.id, rate=5)

    score = get_session_score(db_session, session.id)

    assert score["id_workout_session"] == session.id
    assert score["avg_rate"] == 4.5
    assert score["total_rates"] == 2
