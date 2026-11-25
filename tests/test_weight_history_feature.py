from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from sqlalchemy import text

from app.models.weight_history_model import WeightHistoryModel
from tests.conftest import create_auth_headers


@pytest.fixture
def bdd_context(client, db_session, admin_user):
    client.headers.update(create_auth_headers(admin_user))
    return {
        "db": db_session,
        "client": client,
        "response": None,
        "record_id": None,
        "last_user_id": None,
        "list_user_id": None,
    }


@scenario("../features/weight_history.feature", "Crear un registro de peso válido")
def test_create_valid_weight_history():
    pass


@scenario(
    "../features/weight_history.feature",
    "Rechazar la creación de un registro para un usuario inexistente",
)
def test_create_missing_user():
    pass


@scenario(
    "../features/weight_history.feature",
    "Rechazar un peso inválido al crear un registro",
)
def test_create_invalid_weight():
    pass


@scenario("../features/weight_history.feature", "Listar registros de peso existentes")
def test_list_weight_history():
    pass


@scenario(
    "../features/weight_history.feature",
    "Listar registros de peso filtrados por usuario",
)
def test_list_weight_history_by_user():
    pass


@scenario("../features/weight_history.feature", "Consultar un registro de peso existente")
def test_get_existing_weight_history():
    pass


@scenario("../features/weight_history.feature", "Consultar un registro de peso inexistente")
def test_get_missing_weight_history():
    pass


@scenario("../features/weight_history.feature", "Actualizar un registro de peso existente")
def test_update_existing_weight_history():
    pass


@scenario("../features/weight_history.feature", "Eliminar un registro de peso existente")
def test_delete_existing_weight_history():
    pass


@scenario("../features/weight_history.feature", "Eliminar un registro de peso inexistente")
def test_delete_missing_weight_history():
    pass


def ensure_user_exists(db_session, user_id: int) -> None:
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
                'BDD User',
                'CLIENTE',
                'ACTIVO'
            )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": user_id, "email": f"bdd_weight_user_{user_id}@example.com"},
    )
    db_session.commit()


def remove_user_by_id(db_session, user_id: int) -> None:
    db_session.execute(
        text("DELETE FROM app_user WHERE id = :id"),
        {"id": user_id},
    )
    db_session.commit()


@given(parsers.parse("existe el usuario con identificador {user_id:d}"))
def existing_user(bdd_context, user_id):
    ensure_user_exists(bdd_context["db"], user_id)


@given(parsers.parse("no existe el usuario con identificador {user_id:d}"))
def missing_user(bdd_context, user_id):
    remove_user_by_id(bdd_context["db"], user_id)


@given(parsers.parse("ya existe un registro de peso de {weight} kg para el usuario {user_id:d}"))
def existing_weight_record(bdd_context, weight, user_id):
    db = bdd_context["db"]
    ensure_user_exists(db, user_id)
    db.query(WeightHistoryModel).filter(WeightHistoryModel.user_id == user_id).delete()
    record = WeightHistoryModel(
        user_id=user_id,
        weight_kg=Decimal(weight),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    bdd_context["record_id"] = record.id
    bdd_context["last_user_id"] = user_id


@given(parsers.parse("no existe el registro de peso con identificador {record_id:d}"))
def missing_weight_record(bdd_context, record_id):
    db = bdd_context["db"]
    record = db.get(WeightHistoryModel, record_id)
    if record is not None:
        db.delete(record)
        db.commit()


@when(parsers.parse("registro un peso de {weight} kg para el usuario {user_id:d}"))
def create_weight_record(bdd_context, weight, user_id):
    bdd_context["response"] = bdd_context["client"].post(
        "/weight-history/",
        json={"user_id": user_id, "weight_kg": weight},
    )


@when("listo los registros de peso")
def list_all_weight_records(bdd_context):
    bdd_context["list_user_id"] = bdd_context["last_user_id"]
    bdd_context["response"] = bdd_context["client"].get("/weight-history/?limit=500")


@when(parsers.parse("listo los registros de peso del usuario {user_id:d}"))
def list_user_weight_records(bdd_context, user_id):
    bdd_context["list_user_id"] = user_id
    bdd_context["response"] = bdd_context["client"].get(
        f"/weight-history/?user_id={user_id}&limit=500"
    )


@when("consulto ese registro de peso existente")
def query_existing_weight_record(bdd_context):
    record_id = bdd_context["record_id"]
    bdd_context["response"] = bdd_context["client"].get(f"/weight-history/{record_id}")


@when(parsers.parse("consulto el registro de peso con identificador {record_id:d}"))
def query_missing_weight_record(bdd_context, record_id):
    bdd_context["response"] = bdd_context["client"].get(f"/weight-history/{record_id}")


@when(parsers.parse("actualizo el peso del registro existente a {weight} kg"))
def update_existing_weight_record(bdd_context, weight):
    record_id = bdd_context["record_id"]
    bdd_context["response"] = bdd_context["client"].put(
        f"/weight-history/{record_id}",
        json={"weight_kg": weight},
    )


@when("elimino ese registro de peso existente")
def delete_existing_weight_record(bdd_context):
    record_id = bdd_context["record_id"]
    bdd_context["response"] = bdd_context["client"].delete(
        f"/weight-history/{record_id}"
    )


@when(parsers.parse("elimino el registro de peso con identificador {record_id:d}"))
def delete_missing_weight_record(bdd_context, record_id):
    bdd_context["response"] = bdd_context["client"].delete(
        f"/weight-history/{record_id}"
    )


@then(
    parsers.parse(
        "el registro de peso se crea correctamente con {weight} kg para el usuario {user_id:d}"
    )
)
def weight_record_created(bdd_context, weight, user_id):
    body = bdd_context["response"].json()
    assert body["id"] >= 1
    assert body["user_id"] == user_id
    assert Decimal(str(body["weight_kg"])) == Decimal(weight)
    assert body["created_at"] is not None


@then("la operación falla por validación")
def validation_error(bdd_context):
    assert "detail" in bdd_context["response"].json()


@then(
    parsers.parse(
        "obtengo una lista con {count:d} registro de peso para el usuario {user_id:d}"
    )
)
def list_has_count(bdd_context, count, user_id):
    body = bdd_context["response"].json()
    assert sum(1 for item in body if item["user_id"] == user_id) == count


@then(
    parsers.parse(
        "obtengo el registro de peso con {weight} kg para el usuario {user_id:d}"
    )
)
def got_weight_record(bdd_context, weight, user_id):
    body = bdd_context["response"].json()
    assert body["user_id"] == user_id
    assert Decimal(str(body["weight_kg"])) == Decimal(weight)


@then("la operación indica que no fue encontrado")
def not_found(bdd_context):
    assert "no encontrado" in bdd_context["response"].json()["detail"].lower()


@then(parsers.parse("el registro queda actualizado con peso {weight} kg"))
def weight_record_updated(bdd_context, weight):
    body = bdd_context["response"].json()
    assert Decimal(str(body["weight_kg"])) == Decimal(weight)


@then(parsers.parse("el estado HTTP es {status_code:d}"))
def check_status(bdd_context, status_code):
    assert bdd_context["response"].status_code == status_code
