from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.core.database_connection import get_db
from app.main import app
from app.models.app_user_model import AppUserModel


class InMemoryAppUserDB:
    """Sesión SQLAlchemy simulada en memoria para pruebas BDD contra FastAPI."""

    def __init__(self) -> None:
        self.users: list[AppUserModel] = []
        self._next_id = 1

    def add(self, user: AppUserModel) -> None:
        if getattr(user, "id", None) is None:
            user.id = self._next_id
            self._next_id += 1
        if getattr(user, "created_at", None) is None:
            user.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if getattr(user, "role", None) is None:
            user.role = "CLIENTE"
        if getattr(user, "status", None) is None:
            user.status = "ACTIVO"
        self.users.append(user)

    def commit(self) -> None:
        pass

    def refresh(self, user: AppUserModel) -> None:
        pass

    def delete(self, user: AppUserModel) -> None:
        self.users = [u for u in self.users if u.id != user.id]

    def query(self, model):
        assert model is AppUserModel
        return _InMemoryQuery(self.users)


class _InMemoryQuery:
    def __init__(self, users: list[AppUserModel]) -> None:
        self._users = list(users)
        self._offset = 0
        self._limit: int | None = None

    def filter(self, *criteria):
        filtered = self._users
        for criterion in criteria:
            left = getattr(criterion, "left", None)
            right = getattr(criterion, "right", None)
            operator = getattr(criterion, "operator", None)
            right_val = getattr(right, "value", None)

            left_str = str(left).lower()
            op_name = getattr(operator, "__name__", "")

            if "lower" in left_str and "email" in left_str and op_name == "eq":
                filtered = [u for u in filtered if u.email.lower() == str(right_val).lower()]
            elif left_str.endswith(".id") and op_name == "eq":
                filtered = [u for u in filtered if u.id == right_val]
            elif left_str.endswith(".id") and op_name == "ne":
                filtered = [u for u in filtered if u.id != right_val]
        self._users = filtered
        return self

    def offset(self, skip: int):
        self._offset = skip
        return self

    def limit(self, limit: int):
        self._limit = limit
        return self

    def first(self):
        return self._users[0] if self._users else None

    def all(self):
        end = None if self._limit is None else self._offset + self._limit
        return self._users[self._offset : end]


@pytest.fixture
def bdd_context():
    fake_db = InMemoryAppUserDB()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    ctx = {"client": client, "db": fake_db, "response": None, "user_id": None}
    try:
        yield ctx
    finally:
        app.dependency_overrides.clear()


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


@given(parsers.parse('no existe un usuario con el email "{email}"'))
def missing_email(bdd_context, email):
    bdd_context["db"].users = [
        u for u in bdd_context["db"].users if u.email.lower() != email.lower()
    ]


@given(parsers.parse('ya existe un usuario con el email "{email}"'))
def existing_email(bdd_context, email):
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
    bdd_context["db"].add(user)
    bdd_context["user_id"] = user.id


@given(parsers.parse("no existe el usuario con identificador {user_id:d}"))
def missing_user(bdd_context, user_id):
    bdd_context["db"].users = [u for u in bdd_context["db"].users if u.id != user_id]


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
    bdd_context["response"] = bdd_context["client"].get("/app-users/")


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


@then(parsers.parse("obtengo una lista con {count:d} usuario"))
def list_has_count(bdd_context, count):
    assert len(bdd_context["response"].json()) == count


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
