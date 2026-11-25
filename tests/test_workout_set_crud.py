from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text, update

from app.controllers import workout_set_controller
from app.core.database_connection import Base
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import SessionStatus, WorkoutSessionModel
from app.schemas.workout_set_schema import WorkoutSetCreate, WorkoutSetUpdate
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
def workouts(db_session, test_user):
    db_session.execute(
        text("""
            INSERT INTO workout (
                id, name, type, is_bodyweight, allow_positive_ballast,
                allow_negative_ballast, state, created_by
            )
            OVERRIDING SYSTEM VALUE
            VALUES
                (1, 'Press banca', 'DINAMICO', false, true, false, true, :creator_id),
                (2, 'Dominadas', 'DINAMICO', true, true, true, true, :creator_id),
                (3, 'Plancha', 'ISOMETRICO', false, true, false, true, :creator_id)
        """),
        {"creator_id": test_user.id},
    )
    db_session.commit()


@pytest.fixture
def open_session(db_session, test_user, test_week):
    session = WorkoutSessionModel(
        user_id=test_user.id,
        week_id=test_week.id,
        title="Sesion",
        session_date=date(2026, 11, 21),
        current_bodyweight_kg=Decimal("80.00"),
        observation=None,
        public=False,
        status=SessionStatus.ABIERTO,
        closed_at=None,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def make_payload(**overrides) -> dict:
    payload = {
        "session_id": 1,
        "exercise_id": 1,
        "exercise_order": 1,
        "set_number": 1,
        "added_weight_kg": 50,
        "reps": 10,
        "rir": 0,
    }
    payload.update(overrides)
    return payload


def decimal_equal(value, expected: str, places: str = "0.01") -> bool:
    quantum = Decimal(places)
    return Decimal(str(value)).quantize(quantum) == Decimal(expected).quantize(quantum)


def test_schema_requires_exactly_one_of_reps_or_duration():
    with pytest.raises(ValidationError):
        WorkoutSetCreate(session_id=1, exercise_id=1, exercise_order=1, set_number=1)
    with pytest.raises(ValidationError):
        WorkoutSetCreate(
            session_id=1,
            exercise_id=1,
            exercise_order=1,
            set_number=1,
            reps=10,
            duration_second=40,
            rir=2,
        )


def test_schema_requires_rir_for_dynamic_set():
    with pytest.raises(ValidationError):
        WorkoutSetCreate(
            session_id=1,
            exercise_id=1,
            exercise_order=1,
            set_number=1,
            reps=10,
        )


def test_schema_rejects_bool_in_integer_fields():
    with pytest.raises(ValidationError):
        WorkoutSetCreate(
            session_id=1,
            exercise_id=True,
            exercise_order=1,
            set_number=1,
            reps=10,
            rir=2,
        )


def test_schema_accepts_negative_added_weight_for_assistance():
    payload = WorkoutSetCreate(**make_payload(added_weight_kg=Decimal("-25.00")))
    assert payload.added_weight_kg == Decimal("-25.00")


def test_update_rejects_null_non_nullable_field():
    with pytest.raises(ValidationError):
        WorkoutSetUpdate(set_number=None)


def test_external_weight_formula(db_session, workouts, open_session):
    record = workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(
            **make_payload(session_id=open_session.id, exercise_id=1)
        ),
    )

    assert decimal_equal(record.effective_weight_kg, "50")
    assert decimal_equal(record.volume_load, "500", "0.001")
    assert decimal_equal(record.one_rm_kg, "66.67")
    assert decimal_equal(record.one_rm_percentage, "75")


def test_bodyweight_positive_ballast_formula(db_session, workouts, open_session):
    record = workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(
            **make_payload(
                session_id=open_session.id,
                exercise_id=2,
                added_weight_kg=Decimal("20.00"),
                reps=5,
                rir=5,
            )
        ),
    )

    assert decimal_equal(record.effective_weight_kg, "100")
    assert decimal_equal(record.volume_load, "500", "0.001")
    assert decimal_equal(record.one_rm_kg, "133.33")
    assert decimal_equal(record.one_rm_percentage, "75")


def test_bodyweight_assistance_formula(db_session, workouts, open_session):
    record = workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(
            **make_payload(
                session_id=open_session.id,
                exercise_id=2,
                added_weight_kg=Decimal("-25.00"),
                reps=4,
                rir=2,
            )
        ),
    )

    assert decimal_equal(record.effective_weight_kg, "55")
    assert decimal_equal(record.volume_load, "220", "0.001")
    assert decimal_equal(record.one_rm_kg, "66")
    assert decimal_equal(record.one_rm_percentage, "83.33")


def test_isometric_set_has_no_dynamic_values(db_session, workouts, open_session):
    record = workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(
            session_id=open_session.id,
            exercise_id=3,
            exercise_order=1,
            set_number=1,
            added_weight_kg=Decimal("20.00"),
            duration_second=40,
        ),
    )

    assert decimal_equal(record.effective_weight_kg, "20")
    assert decimal_equal(record.volume_load, "800", "0.001")
    assert record.one_rm_kg is None
    assert record.one_rm_percentage is None


def test_disabled_exercise_rejects_set(db_session, workouts, open_session):
    workout_table = Base.metadata.tables["workout"]
    db_session.execute(
        update(workout_table).where(workout_table.c.id == 1).values(state=False)
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(
            db_session,
            WorkoutSetCreate(**make_payload(session_id=open_session.id)),
        )

    assert exc.value.status_code == 422


def test_positive_ballast_rejected_when_not_allowed(db_session, workouts, open_session):
    workout_table = Base.metadata.tables["workout"]
    db_session.execute(
        update(workout_table)
        .where(workout_table.c.id == 2)
        .values(allow_positive_ballast=False)
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(
            db_session,
            WorkoutSetCreate(
                **make_payload(
                    session_id=open_session.id,
                    exercise_id=2,
                    added_weight_kg=Decimal("20.00"),
                    reps=5,
                    rir=5,
                )
            ),
        )

    assert exc.value.status_code == 422


def test_negative_ballast_rejected_when_not_allowed(db_session, workouts, open_session):
    workout_table = Base.metadata.tables["workout"]
    db_session.execute(
        update(workout_table)
        .where(workout_table.c.id == 2)
        .values(allow_negative_ballast=False)
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(
            db_session,
            WorkoutSetCreate(
                **make_payload(
                    session_id=open_session.id,
                    exercise_id=2,
                    added_weight_kg=Decimal("-25.00"),
                    reps=4,
                    rir=2,
                )
            ),
        )

    assert exc.value.status_code == 422


def test_closed_session_rejects_new_set(db_session, workouts, open_session):
    open_session.status = SessionStatus.CERRADO
    open_session.closed_at = date(2026, 11, 21)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(
            db_session,
            WorkoutSetCreate(**make_payload(session_id=open_session.id)),
        )

    assert exc.value.status_code == 409


def test_duplicate_position_returns_conflict(db_session, workouts, open_session):
    payload = WorkoutSetCreate(**make_payload(session_id=open_session.id))
    workout_set_controller.create_workout_set(db_session, payload)

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(db_session, payload)

    assert exc.value.status_code == 409


def test_different_exercise_same_order_returns_conflict(
    db_session, workouts, open_session
):
    workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(**make_payload(session_id=open_session.id, exercise_id=1)),
    )

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(
            db_session,
            WorkoutSetCreate(
                **make_payload(
                    session_id=open_session.id,
                    exercise_id=2,
                    set_number=2,
                )
            ),
        )

    assert exc.value.status_code == 409


def test_missing_session_returns_404(db_session, workouts, open_session):
    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(
            db_session, WorkoutSetCreate(**make_payload(session_id=999))
        )

    assert exc.value.status_code == 404


def test_missing_exercise_returns_404(db_session, workouts, open_session):
    with pytest.raises(HTTPException) as exc:
        workout_set_controller.create_workout_set(
            db_session,
            WorkoutSetCreate(**make_payload(session_id=open_session.id, exercise_id=999)),
        )

    assert exc.value.status_code == 404


def test_update_recalculates_values(db_session, workouts, open_session):
    record = workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(**make_payload(session_id=open_session.id)),
    )

    updated = workout_set_controller.update_workout_set(
        db_session,
        record.id,
        WorkoutSetUpdate(reps=5, rir=5),
    )

    assert decimal_equal(updated.volume_load, "250", "0.001")
    assert decimal_equal(updated.one_rm_kg, "66.67")


def test_cannot_move_set_from_closed_session(db_session, workouts, open_session, test_user):
    target_session = WorkoutSessionModel(
        user_id=test_user.id,
        week_id=None,
        title="Sesion destino",
        session_date=date(2026, 11, 22),
        current_bodyweight_kg=Decimal("80.00"),
        observation=None,
        public=False,
        status=SessionStatus.ABIERTO,
        closed_at=None,
    )
    db_session.add(target_session)
    db_session.commit()
    db_session.refresh(target_session)

    record = workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(**make_payload(session_id=open_session.id)),
    )

    open_session.status = SessionStatus.CERRADO
    open_session.closed_at = date(2026, 11, 22)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.update_workout_set(
            db_session,
            record.id,
            WorkoutSetUpdate(session_id=target_session.id),
        )

    assert exc.value.status_code == 409


def test_delete_removes_set(db_session, workouts, open_session):
    record = workout_set_controller.create_workout_set(
        db_session,
        WorkoutSetCreate(**make_payload(session_id=open_session.id)),
    )

    workout_set_controller.delete_workout_set(db_session, record.id)

    with pytest.raises(HTTPException) as exc:
        workout_set_controller.get_workout_set(db_session, record.id)
    assert exc.value.status_code == 404


def test_routes_create_list_update_delete(client, workouts, open_session):
    created = client.post("/workout-sets/", json=make_payload(session_id=open_session.id))
    assert created.status_code == 201
    set_id = created.json()["id"]
    assert decimal_equal(created.json()["effective_weight_kg"], "50")

    listed = client.get("/workout-sets/", params={"session_id": open_session.id})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [set_id]

    updated = client.put(f"/workout-sets/{set_id}", json={"rir": 10})
    assert updated.status_code == 200
    assert decimal_equal(updated.json()["one_rm_kg"], "83.33")

    deleted = client.delete(f"/workout-sets/{set_id}")
    assert deleted.status_code == 204
    assert client.get(f"/workout-sets/{set_id}").status_code == 404
