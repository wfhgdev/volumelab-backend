from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.core.database_connection import get_db
from app.main import app
from app.models.weight_history_model import WeightHistoryModel


class _ScalarResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _InMemoryWeightHistoryQuery:
    def __init__(self, records: list[WeightHistoryModel]) -> None:
        self._records = list(records)
        self._offset = 0
        self._limit: int | None = None

    def filter(self, *criteria):
        filtered = self._records
        for criterion in criteria:
            left = getattr(criterion, "left", None)
            right = getattr(criterion, "right", None)
            col_name = getattr(left, "name", None)
            value = getattr(right, "value", None)
            if col_name is not None:
                filtered = [
                    r for r in filtered if getattr(r, col_name) == value
                ]
        self._records = filtered
        return self

    def order_by(self, *clauses):
        self._records.sort(
            key=lambda r: (r.created_at, r.id),
            reverse=True,
        )
        return self

    def offset(self, skip: int):
        self._offset = skip
        return self

    def limit(self, limit: int):
        self._limit = limit
        return self

    def all(self) -> list[WeightHistoryModel]:
        end = None if self._limit is None else self._offset + self._limit
        return self._records[self._offset:end]

    def first(self) -> WeightHistoryModel | None:
        return self._records[0] if self._records else None


class InMemoryWeightHistoryDB:
    """Sesión SQLAlchemy simulada en memoria para pruebas BDD contra FastAPI."""

    def __init__(self) -> None:
        self.user_ids: set[int] = set()
        self.records: list[WeightHistoryModel] = []
        self._next_id = 1
        self._base_time = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)

    def execute(self, statement, params=None):
        user_id = (params or {}).get("user_id")
        if user_id in self.user_ids:
            return _ScalarResult((1,))
        return _ScalarResult(None)

    def add(self, record: WeightHistoryModel) -> None:
        if getattr(record, "id", None) is None:
            record.id = self._next_id
            self._next_id += 1
        if getattr(record, "created_at", None) is None:
            record.created_at = self._base_time + timedelta(minutes=record.id)
        self.records.append(record)

    def commit(self) -> None:
        pass

    def refresh(self, record: WeightHistoryModel) -> None:
        pass

    def delete(self, record: WeightHistoryModel) -> None:
        self.records = [r for r in self.records if r.id != record.id]

    def query(self, model):
        assert model is WeightHistoryModel
        return _InMemoryWeightHistoryQuery(self.records)


@pytest.fixture
def bdd_context():
    db = InMemoryWeightHistoryDB()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    context = {"db": db, "client": client, "response": None, "record_id": None}
    try:
        yield context
    finally:
        app.dependency_overrides.clear()


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


@given(parsers.parse("existe el usuario con identificador {user_id:d}"))
def existing_user(bdd_context, user_id):
    bdd_context["db"].user_ids.add(user_id)


@given(parsers.parse("no existe el usuario con identificador {user_id:d}"))
def missing_user(bdd_context, user_id):
    bdd_context["db"].user_ids.discard(user_id)


@given(parsers.parse("ya existe un registro de peso de {weight} kg para el usuario {user_id:d}"))
def existing_weight_record(bdd_context, weight, user_id):
    bdd_context["db"].user_ids.add(user_id)
    record = WeightHistoryModel(
        user_id=user_id,
        weight_kg=Decimal(weight),
    )
    bdd_context["db"].add(record)
    bdd_context["record_id"] = record.id


@given(parsers.parse("no existe el registro de peso con identificador {record_id:d}"))
def missing_weight_record(bdd_context, record_id):
    bdd_context["db"].records = [
        r for r in bdd_context["db"].records if r.id != record_id
    ]


@when(parsers.parse("registro un peso de {weight} kg para el usuario {user_id:d}"))
def create_weight_record(bdd_context, weight, user_id):
    bdd_context["response"] = bdd_context["client"].post(
        "/weight-history/",
        json={"user_id": user_id, "weight_kg": weight},
    )


@when("listo los registros de peso")
def list_all_weight_records(bdd_context):
    bdd_context["response"] = bdd_context["client"].get("/weight-history/")


@when(parsers.parse("listo los registros de peso del usuario {user_id:d}"))
def list_user_weight_records(bdd_context, user_id):
    bdd_context["response"] = bdd_context["client"].get(
        f"/weight-history/?user_id={user_id}"
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


@then(parsers.parse("obtengo una lista con {count:d} registro de peso"))
def list_has_count(bdd_context, count):
    assert len(bdd_context["response"].json()) == count


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
