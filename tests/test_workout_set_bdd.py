from datetime import date, datetime
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import text

from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import SessionStatus, WorkoutSessionModel
from tests.conftest import create_auth_headers

scenarios("features/workout_set.feature")


@pytest.fixture(autouse=True)
def authenticate_client(client, test_user):
    client.headers.update(create_auth_headers(test_user))


@pytest.fixture
def bdd_workout_set_context():
    return {}


@pytest.fixture
def bdd_week(db_session, test_mesocycle):
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
def bdd_workouts(db_session, test_user):
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
def bdd_open_session(db_session, test_user, bdd_week):
    session = WorkoutSessionModel(
        user_id=test_user.id,
        week_id=bdd_week.id,
        title="Sesion BDD",
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


def decimal_equal(value, expected: str, places: str = "0.01") -> bool:
    quantum = Decimal(places)
    return Decimal(str(value)).quantize(quantum) == Decimal(expected).quantize(quantum)


@given("una sesión abierta con ejercicios base")
def open_session_with_exercises(
    bdd_workouts, bdd_open_session, bdd_workout_set_context
):
    bdd_workout_set_context["session_id"] = bdd_open_session.id


@given("el ejercicio 1 está desactivado")
def deactivate_exercise(db_session):
    db_session.execute(text("UPDATE workout SET state = false WHERE id = 1"))
    db_session.commit()


@given("la sesión está cerrada")
def close_session(db_session, bdd_workout_set_context):
    db_session.execute(
        text(
            "UPDATE workout_session SET status = 'CERRADO', closed_at = :closed_at "
            "WHERE id = :session_id"
        ),
        {
            "closed_at": datetime(2026, 11, 21, 22, 0, 0),
            "session_id": bdd_workout_set_context["session_id"],
        },
    )
    db_session.commit()


@given("ya existe una serie del ejercicio 1 en la posición 1")
def existing_set_in_position(client, bdd_workout_set_context):
    response = client.post(
        "/workout-sets/",
        json={
            "session_id": bdd_workout_set_context["session_id"],
            "exercise_id": 1,
            "exercise_order": 1,
            "set_number": 1,
            "added_weight_kg": 50,
            "reps": 10,
            "rir": 0,
        },
    )
    assert response.status_code == 201


@when(
    parsers.parse(
        "envío una serie dinámica con peso {weight:d}, {reps:d} repeticiones y RIR {rir:d}"
    )
)
def send_dynamic_set(client, bdd_workout_set_context, weight, reps, rir):
    bdd_workout_set_context["last_response"] = client.post(
        "/workout-sets/",
        json={
            "session_id": bdd_workout_set_context["session_id"],
            "exercise_id": 1,
            "exercise_order": 1,
            "set_number": 1,
            "added_weight_kg": weight,
            "reps": reps,
            "rir": rir,
        },
    )


@when(
    parsers.parse(
        "envío una serie dinámica con peso externo {weight:d}, {reps:d} repeticiones y RIR {rir:d}"
    )
)
def send_negative_external_weight_set(
    client, bdd_workout_set_context, weight, reps, rir
):
    bdd_workout_set_context["last_response"] = client.post(
        "/workout-sets/",
        json={
            "session_id": bdd_workout_set_context["session_id"],
            "exercise_id": 1,
            "exercise_order": 1,
            "set_number": 1,
            "added_weight_kg": weight,
            "reps": reps,
            "rir": rir,
        },
    )


@when(parsers.parse("envío una serie isométrica con peso {weight:d} y {duration:d} segundos"))
def send_isometric_set(client, bdd_workout_set_context, weight, duration):
    bdd_workout_set_context["last_response"] = client.post(
        "/workout-sets/",
        json={
            "session_id": bdd_workout_set_context["session_id"],
            "exercise_id": 3,
            "exercise_order": 1,
            "set_number": 1,
            "added_weight_kg": weight,
            "duration_second": duration,
        },
    )


@when(
    parsers.parse(
        "envío una serie del ejercicio {exercise_id:d} en la posición {order:d} "
        "y número de serie {set_number:d}"
    )
)
def send_set_in_existing_position(
    client, bdd_workout_set_context, exercise_id, order, set_number
):
    bdd_workout_set_context["last_response"] = client.post(
        "/workout-sets/",
        json={
            "session_id": bdd_workout_set_context["session_id"],
            "exercise_id": exercise_id,
            "exercise_order": order,
            "set_number": set_number,
            "added_weight_kg": 50,
            "reps": 10,
            "rir": 0,
        },
    )


@then(parsers.parse("la respuesta debe tener el código de estado {status_code:d}"))
def check_status_code(bdd_workout_set_context, status_code):
    assert bdd_workout_set_context["last_response"].status_code == status_code


@then(parsers.parse("el volumen calculado debe ser {expected:d}"))
def check_volume(bdd_workout_set_context, expected):
    data = bdd_workout_set_context["last_response"].json()
    assert decimal_equal(data["volume_load"], str(expected), "0.001")


@then(parsers.re(r"el 1RM estimado debe ser (?P<expected>\d+\.\d+)"))
def check_one_rm(bdd_workout_set_context, expected):
    data = bdd_workout_set_context["last_response"].json()
    assert decimal_equal(data["one_rm_kg"], expected)


@then("el 1RM estimado debe ser nulo")
def check_one_rm_is_null(bdd_workout_set_context):
    data = bdd_workout_set_context["last_response"].json()
    assert data["one_rm_kg"] is None
