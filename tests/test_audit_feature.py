import pytest
from pytest_bdd import given, parsers, scenarios, then, when


scenarios("../features/audit.feature")


@pytest.fixture
def audit_bdd_context():
    return {"response": None}


@given("existe un usuario cliente autenticado")
def user_client_auth(user_client, audit_bdd_context):
    audit_bdd_context["client"] = user_client


@given("existe un usuario administrador autenticado")
def admin_client_auth(admin_client, audit_bdd_context):
    audit_bdd_context["client"] = admin_client


@when("intento listar los registros de auditoría sin autenticación")
def list_audits_unauthenticated(client, audit_bdd_context):
    audit_bdd_context["response"] = client.get("/audits/")


@when("intento listar los registros de auditoría como cliente")
def list_audits_as_client(audit_bdd_context):
    audit_bdd_context["response"] = audit_bdd_context["client"].get("/audits/")


@when("listo los registros de auditoría como administrador")
def list_audits_as_admin(audit_bdd_context):
    audit_bdd_context["response"] = audit_bdd_context["client"].get("/audits/")


@when(parsers.parse('listo los registros de auditoría filtrando por acción "{action}"'))
def list_audits_filter_action(audit_bdd_context, action):
    audit_bdd_context["response"] = audit_bdd_context["client"].get(f"/audits/?action={action}")


@when("listo los registros de auditoría con fecha inicial posterior a la fecha final")
def list_audits_invalid_dates(audit_bdd_context):
    audit_bdd_context["response"] = audit_bdd_context["client"].get(
        "/audits/?date_from=2026-11-22T00:00:00&date_to=2026-11-20T00:00:00"
    )


@when(parsers.parse("consulto el registro de auditoría con identificador {audit_id:d}"))
def get_audit_by_id(audit_bdd_context, audit_id):
    audit_bdd_context["response"] = audit_bdd_context["client"].get(f"/audits/{audit_id}")


@when("intento crear un registro de auditoría por POST")
def post_audit_attempt(audit_bdd_context):
    audit_bdd_context["response"] = audit_bdd_context["client"].post("/audits/", json={})


@when("intento modificar un registro de auditoría por PUT")
def put_audit_attempt(audit_bdd_context):
    audit_bdd_context["response"] = audit_bdd_context["client"].put("/audits/1", json={})


@when("intento eliminar un registro de auditoría por DELETE")
def delete_audit_attempt(audit_bdd_context):
    audit_bdd_context["response"] = audit_bdd_context["client"].delete("/audits/1")


@then(parsers.parse("el estado HTTP de auditoría es {status_code:d}"))
def check_status_code(audit_bdd_context, status_code):
    assert audit_bdd_context["response"].status_code == status_code

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
