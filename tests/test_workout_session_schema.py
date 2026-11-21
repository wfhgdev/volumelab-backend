from datetime import date, datetime
from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.schemas.workout_session_schema import (
    SessionStatusEnum,
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
)


def test_create_accepts_valid_payload():
    payload = WorkoutSessionCreate(
        user_id=1,
        week_id=1,
        title="Sesion",
        session_date=date(2026, 11, 21),
        current_bodyweight_kg=Decimal("60.50"),
        observation="Prueba",
        public=False,
        status=SessionStatusEnum.ABIERTO,
    )
    assert payload.user_id == 1
    assert payload.week_id == 1
    assert payload.current_bodyweight_kg == Decimal("60.50")
    assert payload.status == SessionStatusEnum.ABIERTO


@pytest.mark.parametrize("field", ["user_id", "session_date"])
def test_create_requires_user_id_and_session_date(field):
    data = {"user_id": 1, "session_date": date(2026, 11, 21)}
    data.pop(field)
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(**data)


@pytest.mark.parametrize("user_id", [0, -1])
def test_create_rejects_invalid_user_id(user_id):
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(user_id=user_id, session_date=date(2026, 11, 21))


@pytest.mark.parametrize("week_id", [0, -1])
def test_create_rejects_invalid_week_id(week_id):
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(
            user_id=1,
            week_id=week_id,
            session_date=date(2026, 11, 21),
        )


@pytest.mark.parametrize("weight", [0, -0.01, "60,5", "75.555", Decimal("10000.00")])
def test_create_rejects_invalid_bodyweight(weight):
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(
            user_id=1,
            session_date=date(2026, 11, 21),
            current_bodyweight_kg=weight,
        )


def test_create_rejects_long_title():
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(user_id=1, session_date=date(2026, 11, 21), title="x" * 201)


def test_create_rejects_unknown_status():
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(user_id=1, session_date=date(2026, 11, 21), status="abierto")


def test_create_rejects_closed_at_when_open():
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(
            user_id=1,
            session_date=date(2026, 11, 21),
            closed_at=datetime(2026, 11, 21, 22, 0, 0),
            status=SessionStatusEnum.ABIERTO,
        )


def test_create_requires_closed_at_when_closed():
    with pytest.raises(ValidationError):
        WorkoutSessionCreate(
            user_id=1,
            session_date=date(2026, 11, 21),
            status=SessionStatusEnum.CERRADO,
        )


def test_create_accepts_closed_session():
    payload = WorkoutSessionCreate(
        user_id=1,
        session_date=date(2026, 11, 21),
        closed_at=datetime(2026, 11, 21, 22, 0, 0),
        status=SessionStatusEnum.CERRADO,
    )
    assert payload.status == SessionStatusEnum.CERRADO
    assert payload.closed_at == datetime(2026, 11, 21, 22, 0, 0)


def test_update_accepts_partial_payload():
    payload = WorkoutSessionUpdate(title="Nuevo titulo")
    assert payload.title == "Nuevo titulo"
    assert payload.user_id is None
