import pytest
from pytest_bdd import given, parsers, scenarios, then, when


scenarios("../features/audit.feature")


@pytest.fixture
def audit_bdd_context():
    return {"user_id": None, "audit_id": None, "response": None}


@given("existe un usuario registrado para auditoría")
def existing_audit_user(test_user, audit_bdd_context):
    audit_bdd_context["user_id"] = test_user.id


@given(
    parsers.parse(
        'ya existe un registro de auditoría de acción "{action}" para la entidad "{entity}"'
    )
)
def existing_audit_record(client, audit_bdd_context, action, entity):
    payload = {
        "user_id": audit_bdd_context["user_id"],
        "entity": entity,
        "record_id": "100",
        "action": action,
        "endpoint": f"/{entity}/100",
    }
    response = client.post("/audits/", json=payload)
    assert response.status_code == 201
    audit_bdd_context["audit_id"] = response.json()["id"]


@when(
    parsers.parse(
        'creo un registro de auditoría de acción "{action}" sobre la entidad "{entity}" con record_id "{record_id}" y endpoint "{endpoint}"'
    )
)
def create_audit_for_user(client, audit_bdd_context, action, entity, record_id, endpoint):
    payload = {
        "user_id": audit_bdd_context["user_id"],
        "entity": entity,
        "record_id": record_id,
        "action": action,
        "endpoint": endpoint,
    }
    audit_bdd_context["response"] = client.post("/audits/", json=payload)


@when(
    parsers.parse(
        'creo un registro de auditoría anónimo de acción "{action}" sobre la entidad "{entity}" con record_id "{record_id}"'
    )
)
def create_anonymous_audit(client, audit_bdd_context, action, entity, record_id):
    payload = {
        "user_id": None,
        "entity": entity,
        "record_id": record_id,
        "action": action,
        "endpoint": f"/{entity}/{record_id}",
    }
    audit_bdd_context["response"] = client.post("/audits/", json=payload)


@when(
    parsers.parse(
        "intento crear un registro de auditoría para el usuario inexistente {user_id:d}"
    )
)
def create_audit_missing_user(client, audit_bdd_context, user_id):
    payload = {
        "user_id": user_id,
        "entity": "app_user",
        "record_id": str(user_id),
        "action": "UPDATE",
    }
    audit_bdd_context["response"] = client.post("/audits/", json=payload)


@when(
    parsers.parse('intento crear un registro de auditoría con acción inválida "{action}"')
)
def create_audit_invalid_action(client, audit_bdd_context, action):
    payload = {
        "entity": "workout",
        "record_id": "1",
        "action": action,
    }
    audit_bdd_context["response"] = client.post("/audits/", json=payload)


@when(
    parsers.parse('listo los registros de auditoría filtrando por acción "{action}"')
)
def list_audits_by_action(client, audit_bdd_context, action):
    audit_bdd_context["response"] = client.get(f"/audits/?action={action}")


@when("listo los registros de auditoría con fecha inicial posterior a la fecha final")
def list_audits_invalid_dates(client, audit_bdd_context):
    audit_bdd_context["response"] = client.get(
        "/audits/?date_from=2026-11-25T00:00:00&date_to=2026-11-20T00:00:00"
    )


@when("consulto ese registro de auditoría existente")
def get_existing_audit(client, audit_bdd_context):
    audit_id = audit_bdd_context["audit_id"]
    audit_bdd_context["response"] = client.get(f"/audits/{audit_id}")


@when(parsers.parse("consulto el registro de auditoría con identificador {audit_id:d}"))
def get_missing_audit(client, audit_bdd_context, audit_id):
    audit_bdd_context["response"] = client.get(f"/audits/{audit_id}")


@when(
    parsers.parse(
        'actualizo la acción del registro existente a "{action}" y el endpoint a "{endpoint}"'
    )
)
def update_existing_audit(client, audit_bdd_context, action, endpoint):
    audit_id = audit_bdd_context["audit_id"]
    audit_bdd_context["response"] = client.put(
        f"/audits/{audit_id}",
        json={"action": action, "endpoint": endpoint},
    )


@when("elimino ese registro de auditoría existente")
def delete_existing_audit(client, audit_bdd_context):
    audit_id = audit_bdd_context["audit_id"]
    audit_bdd_context["response"] = client.delete(f"/audits/{audit_id}")


@when(parsers.parse("elimino el registro de auditoría con identificador {audit_id:d}"))
def delete_missing_audit(client, audit_bdd_context, audit_id):
    audit_bdd_context["response"] = client.delete(f"/audits/{audit_id}")


@then(
    parsers.parse(
        'el registro de auditoría se crea correctamente con acción "{action}" y entidad "{entity}"'
    )
)
def assert_audit_created(audit_bdd_context, action, entity):
    body = audit_bdd_context["response"].json()
    assert body["id"] >= 1
    assert body["action"] == action
    assert body["entity"] == entity
    assert body["created_at"] is not None


@then("el registro de auditoría se crea correctamente sin usuario asociado")
def assert_anonymous_audit_created(audit_bdd_context):
    body = audit_bdd_context["response"].json()
    assert body["id"] >= 1
    assert body["user_id"] is None
    assert body["action"] == "EXPORT"


@then("la operación indica que no fue encontrado")
def assert_not_found(audit_bdd_context):
    assert "no encontrado" in audit_bdd_context["response"].json()["detail"].lower()


@then("la operación falla por validación")
def assert_validation_failed(audit_bdd_context):
    assert "detail" in audit_bdd_context["response"].json()


@then("la operación falla por rango de fechas inválido")
def assert_invalid_date_range(audit_bdd_context):
    assert "date_from" in audit_bdd_context["response"].json()["detail"]


@then(
    parsers.parse(
        'obtengo una lista con {count:d} registro de auditoría de acción "{action}"'
    )
)
def assert_filtered_list(audit_bdd_context, count, action):
    items = audit_bdd_context["response"].json()
    assert len(items) == count
    assert all(item["action"] == action for item in items)


@then("obtengo el registro de auditoría consultado")
def assert_got_audit(audit_bdd_context):
    body = audit_bdd_context["response"].json()
    assert body["id"] == audit_bdd_context["audit_id"]
    assert body["entity"] == "workout_session"


@then(
    parsers.parse(
        'el registro queda actualizado con acción "{action}" y endpoint "{endpoint}"'
    )
)
def assert_audit_updated(audit_bdd_context, action, endpoint):
    body = audit_bdd_context["response"].json()
    assert body["action"] == action
    assert body["endpoint"] == endpoint


@then(parsers.parse("el estado HTTP es {status_code:d}"))
def assert_status_code(audit_bdd_context, status_code):
    assert audit_bdd_context["response"].status_code == status_code


@then(
    parsers.parse(
        "al consultar ese registro de auditoría obtengo un estado HTTP {status_code:d}"
    )
)
def assert_deleted_audit_status(client, audit_bdd_context, status_code):
    audit_id = audit_bdd_context["audit_id"]
    response = client.get(f"/audits/{audit_id}")
    assert response.status_code == status_code
