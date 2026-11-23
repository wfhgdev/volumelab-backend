from datetime import date

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from sqlalchemy import func

from app.models.app_user_model import AppUserModel


@pytest.fixture
def bdd_context(client, db_session):
    return {
        "client": client,
        "db": db_session,
        "response": None,
        "user_id": None,
        "email": None,
    }


@scenario("../features/app_user.feature", "Crear un usuario válido")
def test_create_user():
    pass


@scenario("../features/app_user.feature", "Rechazar un email duplicado sin distinguir mayúsculas")
def test_duplicate_email():
    pass


@scenario("../features/app_user.feature", "Rechazar datos inválidos al crear un usuario")
def test_invalid_payload():
    pass


@scenario("../features/app_user.feature", "Listar usuarios existentes")
def test_list_users():
    pass


@scenario("../features/app_user.feature", "Consultar un usuario existente")
def test_get_existing_user():
    pass


@scenario("../features/app_user.feature", "Consultar un usuario inexistente")
def test_missing_user():
    pass


@scenario("../features/app_user.feature", "Actualizar un usuario existente")
def test_update_user():
    pass


@scenario("../features/app_user.feature", "Eliminar un usuario existente")
def test_delete_user():
    pass


@scenario("../features/app_user.feature", "Eliminar un usuario inexistente")
def test_delete_missing_user():
    pass


def remove_user_by_email(db_session, email: str) -> None:
    users = (
        db_session.query(AppUserModel)
        .filter(func.lower(AppUserModel.email) == email.lower())
        .all()
    )
    for user in users:
        db_session.delete(user)
    db_session.commit()


def remove_user_by_id(db_session, user_id: int) -> None:
    user = db_session.get(AppUserModel, user_id)
    if user is not None:
        db_session.delete(user)
        db_session.commit()


@given(parsers.parse('no existe un usuario con el email "{email}"'))
def missing_email(bdd_context, email):
    remove_user_by_email(bdd_context["db"], email)


@given(parsers.parse('ya existe un usuario con el email "{email}"'))
def existing_email(bdd_context, email):
    db = bdd_context["db"]
    user = (
        db.query(AppUserModel)
        .filter(func.lower(AppUserModel.email) == email.lower())
        .first()
    )
    if user is None:
        user = AppUserModel(
            name="Ana",
            lastname="Lopez",
            email=email.lower(),
            password_hash="hashed_pw",
            birth_date=date(1995, 5, 20),
            gender="PREFIERO NO DECIR",
            height_cm=170,
            role="CLIENTE",
            status="ACTIVO",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    bdd_context["user_id"] = user.id
    bdd_context["email"] = user.email.lower()


@given(parsers.parse("no existe el usuario con identificador {user_id:d}"))
def missing_user(bdd_context, user_id):
    remove_user_by_id(bdd_context["db"], user_id)


@when(parsers.parse('creo el usuario "{name}" con el email "{email}"'))
def create_user(bdd_context, name, email):
    bdd_context["response"] = bdd_context["client"].post(
        "/app-users/",
        json={
            "name": name,
            "lastname": "Lopez",
            "email": email,
            "password_hash": "hashed_secret",
            "gender": "PREFIERO NO DECIR",
            "height_cm": 170,
        },
    )


@when("listo los usuarios")
def list_users(bdd_context):
    bdd_context["response"] = bdd_context["client"].get("/app-users/?limit=500")


@when("consulto ese usuario existente")
def query_existing(bdd_context):
    user_id = bdd_context["user_id"]
    bdd_context["response"] = bdd_context["client"].get(f"/app-users/{user_id}")


@when(parsers.parse("consulto el usuario con identificador {user_id:d}"))
def query_missing(bdd_context, user_id):
    bdd_context["response"] = bdd_context["client"].get(f"/app-users/{user_id}")


@when(parsers.parse('actualizo el nombre del usuario existente a "{name}" y su estado a "{status}"'))
def update_existing(bdd_context, name, status):
    user_id = bdd_context["user_id"]
    bdd_context["response"] = bdd_context["client"].put(
        f"/app-users/{user_id}",
        json={"name": name, "status": status},
    )


@when("elimino ese usuario existente")
def delete_existing(bdd_context):
    user_id = bdd_context["user_id"]
    bdd_context["response"] = bdd_context["client"].delete(f"/app-users/{user_id}")


@when(parsers.parse("elimino el usuario con identificador {user_id:d}"))
def delete_missing(bdd_context, user_id):
    bdd_context["response"] = bdd_context["client"].delete(f"/app-users/{user_id}")


@then("el usuario se crea correctamente")
def user_created(bdd_context):
    body = bdd_context["response"].json()
    assert body["id"] >= 1
    assert body["name"] == "Ana"
    assert body["email"] == "ana@example.com"
    assert "password_hash" not in body


@then("la operación falla por conflicto")
def conflict(bdd_context):
    assert "email" in bdd_context["response"].json()["detail"].lower()


@then("la operación falla por validación")
def validation_error(bdd_context):
    assert "detail" in bdd_context["response"].json()


@then("la lista contiene el usuario con ese email")
def list_contains_user(bdd_context):
    body = bdd_context["response"].json()
    assert any(user["email"] == bdd_context["email"] for user in body)


@then(parsers.parse('obtengo los datos del usuario "{email}"'))
def got_user_data(bdd_context, email):
    body = bdd_context["response"].json()
    assert body["email"] == email
    assert "password_hash" not in body


@then("la operación indica que no fue encontrado")
def not_found(bdd_context):
    assert "no encontrado" in bdd_context["response"].json()["detail"].lower()


@then(parsers.parse('el usuario queda actualizado con nombre "{name}" y estado "{status}"'))
def user_updated(bdd_context, name, status):
    body = bdd_context["response"].json()
    assert body["name"] == name
    assert body["status"] == status


@then(parsers.parse("el estado HTTP es {status_code:d}"))
def check_status(bdd_context, status_code):
    assert bdd_context["response"].status_code == status_code
