import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from tests.conftest import create_auth_headers

# Vincular los escenarios definidos en el archivo Gherkin
scenarios("features/training_week.feature")


@pytest.fixture(autouse=True)
def authenticate_client(client, admin_user):
    client.headers.update(create_auth_headers(admin_user))


@pytest.fixture
def bdd_week_context():
    """Contenedor de estado compartido entre los pasos de un escenario de semana."""
    return {}


@given("un mesociclo base existente")
def base_mesocycle_exists(test_mesocycle, bdd_week_context):
    bdd_week_context["mesocycle_id"] = test_mesocycle.id


@given(parsers.parse('una semana de entrenamiento previamente creada con orden {order:d}'))
def existing_training_week(client, test_mesocycle, bdd_week_context, order):
    bdd_week_context["mesocycle_id"] = test_mesocycle.id
    payload = {
        "mesocycle_id": test_mesocycle.id,
        "week_order": order,
        "start_date": "2026-01-01",
        "end_date": "2026-01-07"
    }
    response = client.post("/training-weeks/", json=payload)
    assert response.status_code == 201
    created = response.json()
    bdd_week_context["week_id"] = created["id"]
    bdd_week_context["week_data"] = created


@when(parsers.parse('envío una solicitud para crear una semana con orden {order:d}, fecha inicio "{start_date}" y fecha fin "{end_date}"'))
def send_create_week_request(client, bdd_week_context, order, start_date, end_date):
    payload = {
        "mesocycle_id": bdd_week_context["mesocycle_id"],
        "week_order": order,
        "start_date": start_date,
        "end_date": end_date
    }
    response = client.post("/training-weeks/", json=payload)
    bdd_week_context["last_response"] = response


@when(parsers.parse('envío una solicitud para crear otra semana con el mismo orden {order:d} en el mismo mesociclo'))
def send_create_duplicate_order(client, bdd_week_context, order):
    payload = {
        "mesocycle_id": bdd_week_context["mesocycle_id"],
        "week_order": order,
        "start_date": "2026-01-08",
        "end_date": "2026-01-14"
    }
    response = client.post("/training-weeks/", json=payload)
    bdd_week_context["last_response"] = response


@when(parsers.parse('envío una solicitud para crear una semana para el mesociclo inexistente {mesocycle_id:d}'))
def send_create_week_invalid_mesocycle(client, bdd_week_context, mesocycle_id):
    payload = {
        "mesocycle_id": mesocycle_id,
        "week_order": 1,
        "start_date": "2026-01-01",
        "end_date": "2026-01-07"
    }
    response = client.post("/training-weeks/", json=payload)
    bdd_week_context["last_response"] = response


@when("consulto la semana de entrenamiento por su identificador")
def query_week_by_id(client, bdd_week_context):
    week_id = bdd_week_context["week_id"]
    response = client.get(f"/training-weeks/{week_id}")
    bdd_week_context["last_response"] = response


@when(parsers.parse('consulto una semana de entrenamiento con el identificador inexistente {non_existent_id:d}'))
def query_non_existent_week(client, bdd_week_context, non_existent_id):
    response = client.get(f"/training-weeks/{non_existent_id}")
    bdd_week_context["last_response"] = response


@when(parsers.parse('actualizo la fecha de fin de la semana a "{new_end_date}"'))
def update_week_end_date(client, bdd_week_context, new_end_date):
    week_id = bdd_week_context["week_id"]
    payload = {
        "end_date": new_end_date
    }
    response = client.put(f"/training-weeks/{week_id}", json=payload)
    bdd_week_context["last_response"] = response


@when("elimino la semana de entrenamiento por su identificador")
def delete_week_by_id(client, bdd_week_context):
    week_id = bdd_week_context["week_id"]
    response = client.delete(f"/training-weeks/{week_id}")
    bdd_week_context["last_response"] = response


@then(parsers.parse('la respuesta debe tener el código de estado {status_code:d}'))
def check_week_response_status(bdd_week_context, status_code):
    response = bdd_week_context["last_response"]
    assert response.status_code == status_code


@then("la respuesta de semana debe tener un código de error de validación 422 o 400")
def check_week_validation_error_code(bdd_week_context):
    response = bdd_week_context["last_response"]
    assert response.status_code in [400, 422]


@then(parsers.parse('la semana creada debe pertenecer al mesociclo y tener orden {expected_order:d}'))
def check_created_week_data(bdd_week_context, expected_order):
    data = bdd_week_context["last_response"].json()
    assert data["mesocycle_id"] == bdd_week_context["mesocycle_id"]
    assert data["week_order"] == expected_order


@then("los datos deben coincidir con la semana creada")
def check_matching_week_data(bdd_week_context):
    data = bdd_week_context["last_response"].json()
    assert data["id"] == bdd_week_context["week_data"]["id"]
    assert data["week_order"] == bdd_week_context["week_data"]["week_order"]


@then(parsers.parse('la semana actualizada debe tener fecha fin "{expected_end_date}"'))
def check_updated_week_data(bdd_week_context, expected_end_date):
    data = bdd_week_context["last_response"].json()
    assert data["end_date"] == expected_end_date


@then(parsers.parse('si intento consultar nuevamente dicha semana obtengo un código {status_code:d}'))
def verify_deleted_week_status(client, bdd_week_context, status_code):
    week_id = bdd_week_context["week_id"]
    response = client.get(f"/training-weeks/{week_id}")
    assert response.status_code == status_code
