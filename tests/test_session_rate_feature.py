import pytest
from pytest_bdd import given, parsers, scenario, then, when
from sqlalchemy import text

from app.models.session_rate_model import SessionRateModel


@pytest.fixture
def bdd_context(client, db_session):
    return {"client": client, "db": db_session, "response": None}


def ensure_user(db_session, user_id: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO app_user (
                id,
                email,
                password_hash,
                name,
                role,
                status
            )
            OVERRIDING SYSTEM VALUE
            VALUES (
                :id,
                :email,
                'hash',
                'BDD Rate',
                'CLIENTE',
                'ACTIVO'
            )
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": user_id, "email": f"bdd_rate_user_{user_id}@example.com"},
    )
    db_session.commit()


def ensure_session(db_session, session_id: int, public: bool) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO workout_session (
                id,
                user_id,
                title,
                session_date,
                current_bodyweight_kg,
                public,
                status
            )
            OVERRIDING SYSTEM VALUE
            VALUES (
                :id,
                1,
                'BDD Session',
                DATE '2026-01-01',
                70.0,
                :public,
                'ABIERTO'
            )
            ON CONFLICT (id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                public = EXCLUDED.public,
                status = 'ABIERTO',
                closed_at = NULL
            """
        ),
        {"id": session_id, "public": public},
    )
    db_session.commit()


def delete_rates_for_pair(db_session, session_id: int, user_id: int) -> None:
    db_session.query(SessionRateModel).filter(
        SessionRateModel.id_workout_session == session_id,
        SessionRateModel.user_id == user_id,
    ).delete(synchronize_session=False)
    db_session.commit()


def delete_rates_for_session(db_session, session_id: int) -> None:
    db_session.query(SessionRateModel).filter(
        SessionRateModel.id_workout_session == session_id
    ).delete(synchronize_session=False)
    db_session.commit()


def delete_rate_by_id(db_session, rate_id: int) -> None:
    db_session.query(SessionRateModel).filter(
        SessionRateModel.id == rate_id
    ).delete(synchronize_session=False)
    db_session.commit()


def insert_rate(db_session, session_id: int, user_id: int, rate: int, rate_id: int | None = None):
    if rate_id is None:
        record = SessionRateModel(
            id_workout_session=session_id,
            user_id=user_id,
            rate=rate,
        )
        db_session.add(record)
    else:
        db_session.execute(
            text(
                """
                INSERT INTO session_rate (
                    id,
                    id_workout_session,
                    user_id,
                    rate
                )
                OVERRIDING SYSTEM VALUE
                VALUES (
                    :id,
                    :session_id,
                    :user_id,
                    :rate
                )
                """
            ),
            {
                "id": rate_id,
                "session_id": session_id,
                "user_id": user_id,
                "rate": rate,
            },
        )
    db_session.commit()


@scenario("../features/session_rate.feature", "Crear una valoración válida para una sesión pública")
def test_create_valid_rate():
    pass


@scenario("../features/session_rate.feature", "Rechazar una valoración para una sesión privada")
def test_reject_private_rate():
    pass


@scenario("../features/session_rate.feature", "Rechazar una valoración duplicada del mismo usuario sobre la misma sesión")
def test_reject_duplicate_rate():
    pass


@scenario("../features/session_rate.feature", "Rechazar una puntuación fuera del rango permitido")
def test_reject_out_of_range():
    pass


@scenario("../features/session_rate.feature", "Listar valoraciones existentes")
def test_list_rates():
    pass


@scenario("../features/session_rate.feature", "Consultar una valoración por ID existente")
def test_get_by_id():
    pass


@scenario("../features/session_rate.feature", "Consultar una valoración por ID inexistente")
def test_get_by_id_not_found():
    pass


@scenario("../features/session_rate.feature", "Consultar la puntuación media de una sesión")
def test_get_session_score():
    pass


@scenario("../features/session_rate.feature", "Actualizar una valoración existente")
def test_update_rate():
    pass


@scenario("../features/session_rate.feature", "Crear o actualizar valoración mediante upsert")
def test_upsert_rate():
    pass


@scenario("../features/session_rate.feature", "Eliminar una valoración existente")
def test_delete_rate():
    pass


@scenario("../features/session_rate.feature", "Eliminar una valoración inexistente")
def test_delete_rate_not_found():
    pass


@given(parsers.parse("existe una sesión pública con id {session_id:d}"))
def step_public_session(bdd_context, session_id):
    ensure_user(bdd_context["db"], 1)
    ensure_session(bdd_context["db"], session_id, public=True)


@given(parsers.parse("existe una sesión privada con id {session_id:d}"))
def step_private_session(bdd_context, session_id):
    ensure_user(bdd_context["db"], 1)
    ensure_session(bdd_context["db"], session_id, public=False)


@given(parsers.parse("no existe una valoración del usuario {user_id:d} para la sesión {session_id:d}"))
def step_no_rate_exists(bdd_context, user_id, session_id):
    delete_rates_for_pair(bdd_context["db"], session_id, user_id)


@given(parsers.parse("ya existe una valoración del usuario {user_id:d} para la sesión {session_id:d}"))
def step_rate_exists(bdd_context, user_id, session_id):
    db = bdd_context["db"]
    ensure_user(db, user_id)
    ensure_session(db, session_id, public=True)
    delete_rates_for_pair(db, session_id, user_id)
    insert_rate(db, session_id, user_id, 5)


@given(parsers.parse("existe una valoración registrada con id {rate_id:d}"))
def step_rate_with_id_exists(bdd_context, rate_id):
    db = bdd_context["db"]
    ensure_user(db, 1)
    ensure_session(db, 100, public=True)
    delete_rate_by_id(db, rate_id)
    delete_rates_for_pair(db, 100, 1)
    insert_rate(db, 100, 1, 5, rate_id=rate_id)


@given(parsers.parse("no existe ninguna valoración con id {rate_id:d}"))
def step_no_rate_with_id(bdd_context, rate_id):
    delete_rate_by_id(bdd_context["db"], rate_id)


@given(parsers.parse("la sesión {session_id:d} tiene valoraciones registradas"))
def step_session_has_rates(bdd_context, session_id):
    db = bdd_context["db"]
    ensure_user(db, 1)
    ensure_session(db, session_id, public=True)
    delete_rates_for_session(db, session_id)
    insert_rate(db, session_id, 1, 4)


@when(parsers.parse("creo la valoración con puntuación {rate:d} para la sesión {session_id:d} y usuario {user_id:d}"))
def step_when_create_rate(bdd_context, rate, session_id, user_id):
    bdd_context["response"] = bdd_context["client"].post(
        "/session-rates/",
        json={"id_workout_session": session_id, "user_id": user_id, "rate": rate},
    )


@when(parsers.parse("intento valorar la sesión {session_id:d} con puntuación {rate:d} para el usuario {user_id:d}"))
def step_when_try_private_rate(bdd_context, rate, session_id, user_id):
    bdd_context["response"] = bdd_context["client"].post(
        "/session-rates/",
        json={"id_workout_session": session_id, "user_id": user_id, "rate": rate},
    )


@when("listo las valoraciones de sesiones")
def step_when_list(bdd_context):
    bdd_context["response"] = bdd_context["client"].get("/session-rates/?limit=500")


@when(parsers.parse("consulto la valoración con id {rate_id:d}"))
def step_when_get_by_id(bdd_context, rate_id):
    bdd_context["response"] = bdd_context["client"].get(f"/session-rates/{rate_id}")


@when(parsers.parse("consulto la puntuación acumulada de la sesión {session_id:d}"))
def step_when_get_score(bdd_context, session_id):
    bdd_context["response"] = bdd_context["client"].get(f"/session-rates/session/{session_id}/score")


@when(parsers.parse("actualizo la puntuación de la valoración {rate_id:d} a {new_rate:d}"))
def step_when_update(bdd_context, rate_id, new_rate):
    bdd_context["response"] = bdd_context["client"].put(
        f"/session-rates/{rate_id}",
        json={"rate": new_rate},
    )


@when(parsers.parse("realizo un upsert con puntuación {rate:d} para la sesión {session_id:d} y usuario {user_id:d}"))
def step_when_upsert(bdd_context, rate, session_id, user_id):
    bdd_context["response"] = bdd_context["client"].post(
        "/session-rates/upsert",
        json={"id_workout_session": session_id, "user_id": user_id, "rate": rate},
    )


@when(parsers.parse("elimino la valoración con id {rate_id:d}"))
def step_when_delete(bdd_context, rate_id):
    bdd_context["response"] = bdd_context["client"].delete(f"/session-rates/{rate_id}")


@then(parsers.parse("la valoración se crea correctamente con puntuación {expected_rate:d}"))
def step_then_created(bdd_context, expected_rate):
    assert bdd_context["response"].status_code == 201
    assert bdd_context["response"].json()["rate"] == expected_rate


@then("la operación falla porque la sesión no es pública")
def step_then_fails_private(bdd_context):
    assert bdd_context["response"].status_code == 400
    assert "no es pública" in bdd_context["response"].json()["detail"]


@then("la operación falla por conflicto de voto duplicado")
def step_then_duplicate_conflict(bdd_context):
    assert bdd_context["response"].status_code == 409


@then("la operación falla por validación de datos")
def step_then_validation_fails(bdd_context):
    assert bdd_context["response"].status_code == 422


@then("obtengo una lista con al menos 1 valoración")
def step_then_list_ok(bdd_context):
    assert bdd_context["response"].status_code == 200
    assert len(bdd_context["response"].json()) >= 1


@then(parsers.parse("obtengo los datos de la valoración con id {rate_id:d}"))
def step_then_data_id(bdd_context, rate_id):
    assert bdd_context["response"].status_code == 200
    assert bdd_context["response"].json()["id"] == rate_id


@then("la operación indica que la valoración no fue encontrada")
def step_then_not_found(bdd_context):
    assert bdd_context["response"].status_code == 404


@then("obtengo la nota media y el total de valoraciones")
def step_then_score_ok(bdd_context):
    assert bdd_context["response"].status_code == 200
    data = bdd_context["response"].json()
    assert "avg_rate" in data
    assert "total_rates" in data


@then(parsers.parse("la valoración {rate_id:d} queda actualizada con puntuación {expected_rate:d}"))
def step_then_updated_ok(bdd_context, rate_id, expected_rate):
    assert bdd_context["response"].status_code == 200
    assert bdd_context["response"].json()["rate"] == expected_rate


@then(parsers.parse("la valoración queda registrada o actualizada con puntuación {expected_rate:d}"))
def step_then_upserted_ok(bdd_context, expected_rate):
    assert bdd_context["response"].status_code == 200
    assert bdd_context["response"].json()["rate"] == expected_rate


@then(parsers.parse("el estado HTTP es {expected_code:d}"))
def step_then_status_code(bdd_context, expected_code):
    assert bdd_context["response"].status_code == expected_code
