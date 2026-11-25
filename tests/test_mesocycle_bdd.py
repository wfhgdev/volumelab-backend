import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from tests.conftest import create_auth_headers

# Vincular los escenarios definidos en el archivo Gherkin
scenarios("features/mesocycle.feature")


@pytest.fixture(autouse=True)
def authenticate_client(client, admin_user):
    client.headers.update(create_auth_headers(admin_user))


@pytest.fixture
def bdd_context():
    """Contenedor de estado compartido entre los pasos de un escenario."""
    return {}


@given("un usuario existente con rol CLIENTE")
def user_exists(test_user, bdd_context):
    bdd_context["user_id"] = test_user.id


@given(parsers.parse('un mesociclo previamente creado con nombre "{name}"'))
def create_initial_mesocycle(client, test_user, bdd_context, name):
    bdd_context["user_id"] = test_user.id
    payload = {
        "name": name,
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
        "user_id": test_user.id,
        "status": "PLANIFICADO"
    }
    response = client.post("/mesocycles/", json=payload)
    assert response.status_code == 201
    created = response.json()
    bdd_context["mesocycle_id"] = created["id"]
    bdd_context["mesocycle_data"] = created


@when(parsers.parse('envío una solicitud para crear un mesociclo con nombre "{name}", fecha inicio "{start_date}", fecha fin "{end_date}" y estado "{status}"'))
def send_create_mesocycle_request(client, bdd_context, name, start_date, end_date, status):
    payload = {
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "user_id": bdd_context["user_id"],
        "status": status
    }
    response = client.post("/mesocycles/", json=payload)
    bdd_context["last_response"] = response


@when(parsers.parse('envío una solicitud para crear un mesociclo para el usuario inexistente {user_id:d}'))
def send_create_mesocycle_invalid_user(client, bdd_context, user_id):
    payload = {
        "name": "Meso Usuario Fantasma",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
        "user_id": user_id,
        "status": "PLANIFICADO"
    }
    response = client.post("/mesocycles/", json=payload)
    bdd_context["last_response"] = response


@when("consulto el mesociclo por su identificador")
def query_mesocycle_by_id(client, bdd_context):
    meso_id = bdd_context["mesocycle_id"]
    response = client.get(f"/mesocycles/{meso_id}")
    bdd_context["last_response"] = response


@when(parsers.parse('consulto un mesociclo con el identificador inexistente {non_existent_id:d}'))
def query_non_existent_mesocycle(client, bdd_context, non_existent_id):
    response = client.get(f"/mesocycles/{non_existent_id}")
    bdd_context["last_response"] = response


@when(parsers.parse('actualizo el nombre a "{new_name}" y el estado a "{new_status}"'))
def update_mesocycle_name_and_status(client, bdd_context, new_name, new_status):
    meso_id = bdd_context["mesocycle_id"]
    payload = {
        "name": new_name,
        "status": new_status
    }
    response = client.put(f"/mesocycles/{meso_id}", json=payload)
    bdd_context["last_response"] = response


@when("elimino el mesociclo por su identificador")
def delete_mesocycle_by_id(client, bdd_context):
    meso_id = bdd_context["mesocycle_id"]
    response = client.delete(f"/mesocycles/{meso_id}")
    bdd_context["last_response"] = response


@then(parsers.parse('la respuesta debe tener el código de estado {status_code:d}'))
def check_response_status(bdd_context, status_code):
    response = bdd_context["last_response"]
    assert response.status_code == status_code


@then("la respuesta debe tener un código de error de validación 422 o 400")
def check_validation_error_code(bdd_context):
    response = bdd_context["last_response"]
    assert response.status_code in [400, 422]


@then(parsers.parse('el mesociclo creado debe contener el nombre "{expected_name}" y estado "{expected_status}"'))
def check_created_mesocycle_data(bdd_context, expected_name, expected_status):
    data = bdd_context["last_response"].json()
    assert data["name"] == expected_name
    assert data["status"] == expected_status


@then("los datos deben coincidir con el mesociclo creado")
def check_matching_data(bdd_context):
    data = bdd_context["last_response"].json()
    assert data["id"] == bdd_context["mesocycle_data"]["id"]
    assert data["name"] == bdd_context["mesocycle_data"]["name"]


@then(parsers.parse('el mesociclo actualizado debe tener el nombre "{expected_name}" y estado "{expected_status}"'))
def check_updated_mesocycle_data(bdd_context, expected_name, expected_status):
    data = bdd_context["last_response"].json()
    assert data["name"] == expected_name
    assert data["status"] == expected_status


@then(parsers.parse('si intento consultar nuevamente dicho mesociclo obtengo un código {status_code:d}'))
def verify_deleted_mesocycle_status(client, bdd_context, status_code):
    meso_id = bdd_context["mesocycle_id"]
    response = client.get(f"/mesocycles/{meso_id}")
    assert response.status_code == status_code
