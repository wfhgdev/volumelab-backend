from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenario, then, when

from app.core.database_connection import get_db
from app.main import app
from app.models.session_rate_model import SessionRateModel


class InMemorySessionRateDB:
    """Sesión simulada en memoria para pruebas BDD de session_rate contra FastAPI."""

    def __init__(self) -> None:
        self.rates: list[SessionRateModel] = []
        self._next_id = 1
        self.public_sessions: set[int] = {100}
        self.private_sessions: set[int] = {101}

    def add(self, item: SessionRateModel) -> None:
        if getattr(item, "id", None) is None:
            item.id = self._next_id
            self._next_id += 1
        if getattr(item, "created_at", None) is None:
            item.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.rates.append(item)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, item: SessionRateModel) -> None:
        pass

    def delete(self, item: SessionRateModel) -> None:
        self.rates = [r for r in self.rates if r.id != item.id]

    def query(self, *entities):
        if len(entities) == 1 and entities[0] is SessionRateModel:
            return _InMemorySessionRateQuery(self.rates)
        return _InMemoryScoreQuery(self.rates)


class _InMemorySessionRateQuery:
    def __init__(self, rates: list[SessionRateModel]) -> None:
        self._rates = list(rates)
        self._offset = 0
        self._limit: int | None = None

    def filter(self, *criteria):
        filtered = self._rates
        for criterion in criteria:
            left = getattr(criterion, "left", None)
            right = getattr(criterion, "right", None)
            operator = getattr(criterion, "operator", None)
            right_val = getattr(right, "value", None)
            left_str = str(left).lower()
            op_name = getattr(operator, "__name__", "")

            if left_str.endswith(".id") and op_name == "eq":
                filtered = [r for r in filtered if r.id == right_val]
            elif "id_workout_session" in left_str and op_name == "eq":
                filtered = [r for r in filtered if r.id_workout_session == right_val]
            elif "user_id" in left_str and op_name == "eq":
                filtered = [r for r in filtered if r.user_id == right_val]
        self._rates = filtered
        return self

    def order_by(self, *clauses):
        return self

    def offset(self, skip: int):
        self._offset = skip
        return self

    def limit(self, limit: int):
        self._limit = limit
        return self

    def first(self):
        return self._rates[0] if self._rates else None

    def all(self):
        end = None if self._limit is None else self._offset + self._limit
        return self._rates[self._offset : end]


class _InMemoryScoreQuery:
    def __init__(self, rates: list[SessionRateModel]) -> None:
        self._rates = rates

    def filter(self, *criteria):
        filtered = self._rates
        for criterion in criteria:
            right = getattr(criterion, "right", None)
            right_val = getattr(right, "value", None)
            if right_val is not None:
                filtered = [r for r in filtered if r.id_workout_session == right_val]
        self._rates = filtered
        return self

    def one(self):
        total = len(self._rates)
        avg = round(sum(r.rate for r in self._rates) / total, 2) if total > 0 else 0.0
        mock_res = type("ScoreResult", (), {"avg_rate": avg, "total_rates": total})()
        return mock_res


@pytest.fixture
def bdd_context():
    fake_db = InMemorySessionRateDB()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    ctx = {"client": client, "db": fake_db, "response": None}
    try:
        yield ctx
    finally:
        app.dependency_overrides.clear()


# Scenarios
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


# Steps
@given(parsers.parse("existe una sesión pública con id {session_id:d}"))
def step_public_session(bdd_context, session_id):
    bdd_context["db"].public_sessions.add(session_id)


@given(parsers.parse("existe una sesión privada con id {session_id:d}"))
def step_private_session(bdd_context, session_id):
    bdd_context["db"].private_sessions.add(session_id)


@given(parsers.parse("no existe una valoración del usuario {user_id:d} para la sesión {session_id:d}"))
def step_no_rate_exists(bdd_context, user_id, session_id):
    bdd_context["db"].rates = [
        r for r in bdd_context["db"].rates
        if not (r.id_workout_session == session_id and r.user_id == user_id)
    ]


@given(parsers.parse("ya existe una valoración del usuario {user_id:d} para la sesión {session_id:d}"))
def step_rate_exists(bdd_context, user_id, session_id):
    existing = [r for r in bdd_context["db"].rates if r.id_workout_session == session_id and r.user_id == user_id]
    if not existing:
        rate = SessionRateModel(
            id=bdd_context["db"]._next_id,
            id_workout_session=session_id,
            user_id=user_id,
            rate=5,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        bdd_context["db"]._next_id += 1
        bdd_context["db"].rates.append(rate)


@given(parsers.parse("existe una valoración registrada con id {rate_id:d}"))
def step_rate_with_id_exists(bdd_context, rate_id):
    existing = [r for r in bdd_context["db"].rates if r.id == rate_id]
    if not existing:
        rate = SessionRateModel(
            id=rate_id,
            id_workout_session=100,
            user_id=1,
            rate=5,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        bdd_context["db"].rates.append(rate)


@given(parsers.parse("no existe ninguna valoración con id {rate_id:d}"))
def step_no_rate_with_id(bdd_context, rate_id):
    bdd_context["db"].rates = [r for r in bdd_context["db"].rates if r.id != rate_id]


@given(parsers.parse("la sesión {session_id:d} tiene valoraciones registradas"))
def step_session_has_rates(bdd_context, session_id):
    if not any(r.id_workout_session == session_id for r in bdd_context["db"].rates):
        bdd_context["db"].rates.append(
            SessionRateModel(
                id=bdd_context["db"]._next_id,
                id_workout_session=session_id,
                user_id=1,
                rate=4,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        bdd_context["db"]._next_id += 1


@when(parsers.parse("creo la valoración con puntuación {rate:d} para la sesión {session_id:d} y usuario {user_id:d}"))
def step_when_create_rate(bdd_context, rate, session_id, user_id):
    client = bdd_context["client"]
    bdd_context["response"] = client.post(
        "/session-rates/",
        json={"id_workout_session": session_id, "user_id": user_id, "rate": rate},
    )


@when(parsers.parse("intento valorar la sesión {session_id:d} con puntuación {rate:d} para el usuario {user_id:d}"))
def step_when_try_private_rate(bdd_context, rate, session_id, user_id):
    client = bdd_context["client"]
    # Mock behavior of private session trigger
    from sqlalchemy.exc import DBAPIError
    orig_commit = bdd_context["db"].commit
    bdd_context["db"].commit = MagicMock(side_effect=DBAPIError(
        "INSERT", {}, Exception(f"La sesión {session_id} no es pública y no se puede valorar")
    ))
    try:
        bdd_context["response"] = client.post(
            "/session-rates/",
            json={"id_workout_session": session_id, "user_id": user_id, "rate": rate},
        )
    finally:
        bdd_context["db"].commit = orig_commit


@when("listo las valoraciones de sesiones")
def step_when_list(bdd_context):
    bdd_context["response"] = bdd_context["client"].get("/session-rates/")


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
