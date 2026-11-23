from datetime import date

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.app_user_model import AppUserModel, RoleUser
from app.models.mesocycle_model import MesocycleModel
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import WorkoutSessionModel


scenarios("../features/workout_session.feature")


@pytest.fixture
def bdd_context():
    return {"users": {}, "weeks": {}, "session_id": None, "last_response": None}


def _create_client_user(db_session, label):
    user = AppUserModel(
        email=f"bdd_{label}@volumelab.test",
        password_hash="hashed_secret_password",
        name="Usuario BDD",
        role=RoleUser.CLIENTE,
        status="ACTIVO",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _session_payload(user_id, week_id=None, public=False):
    payload = {
        "user_id": user_id,
        "title": "Sesion BDD",
        "session_date": "2026-11-21",
        "public": public,
        "status": "ABIERTO",
    }
    if week_id is not None:
        payload["week_id"] = week_id
    return payload


@given(parsers.parse("existe un usuario CLIENTE con identificador {user_id:d}"))
def existing_client_user(db_session, bdd_context, user_id):
    if user_id not in bdd_context["users"]:
        bdd_context["users"][user_id] = _create_client_user(db_session, user_id)


@given(parsers.parse("existe una semana de entrenamiento del usuario {user_id:d}"))
def existing_training_week(db_session, bdd_context, user_id):
    user = bdd_context["users"][user_id]
    mesocycle = MesocycleModel(
        user_id=user.id,
        name="Mesociclo BDD",
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
    bdd_context["weeks"][user_id] = week


@given(parsers.parse("el usuario {user_id:d} tiene {count:d} sesiones públicas"))
def public_session_history(db_session, bdd_context, user_id, count):
    user = bdd_context["users"][user_id]
    for _ in range(count):
        db_session.add(
            WorkoutSessionModel(
                user_id=user.id,
                session_date=date(2026, 11, 20),
                public=True,
            )
        )
    db_session.commit()


@given(parsers.parse("existe una sesión del usuario {user_id:d}"))
def existing_workout_session(db_session, bdd_context, user_id):
    user = bdd_context["users"][user_id]
    session = WorkoutSessionModel(
        user_id=user.id,
        session_date=date(2026, 11, 21),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    bdd_context["session_id"] = session.id


@when(parsers.parse("creo una sesión para el usuario {user_id:d} con la semana del usuario {week_owner_id:d}"))
def create_session_with_week(client, bdd_context, user_id, week_owner_id):
    user = bdd_context["users"][user_id]
    week = bdd_context["weeks"][week_owner_id]
    bdd_context["last_response"] = client.post(
        "/workout-sessions/",
        json=_session_payload(user.id, week.id),
    )


@when(parsers.parse("creo una sesión pública para el usuario {user_id:d}"))
def create_public_session(client, bdd_context, user_id):
    user = bdd_context["users"][user_id]
    bdd_context["last_response"] = client.post(
        "/workout-sessions/",
        json=_session_payload(user.id, public=True),
    )


@when("actualizo el usuario de esa sesión a nulo")
def update_session_user_to_null(client, bdd_context):
    bdd_context["last_response"] = client.put(
        f"/workout-sessions/{bdd_context['session_id']}",
        json={"user_id": None},
    )


@then(parsers.parse("la respuesta tiene el código de estado {status_code:d}"))
def check_status_code(bdd_context, status_code):
    assert bdd_context["last_response"].status_code == status_code


@then(parsers.parse("la sesión pertenece al usuario {user_id:d}"))
def check_session_owner(bdd_context, user_id):
    assert bdd_context["last_response"].json()["user_id"] == bdd_context["users"][user_id].id
