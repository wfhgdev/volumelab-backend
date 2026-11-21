from datetime import date
import pytest
from pydantic import ValidationError
from app.schemas.mesocycle_schema import MesocycleCreate, MesocycleUpdate, MesocycleStatusEnum
from app.controllers import mesocycle_controller
from app.core.exceptions import (
    MesocycleNotFoundException,
    UserNotFoundException,
    MesocycleDateValidationException
)


class TestMesocycleSchemaValidations:
    """Pruebas unitarias de las validaciones de esquemas Pydantic."""

    def test_schema_valid_dates(self):
        schema = MesocycleCreate(
            name="Mesociclo Volumen",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            user_id=1,
            status=MesocycleStatusEnum.PLANIFICADO
        )
        assert schema.name == "Mesociclo Volumen"
        assert schema.end_date >= schema.start_date

    def test_schema_invalid_dates_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            MesocycleCreate(
                name="Mesociclo Invalido",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 1, 1),
                user_id=1,
                status=MesocycleStatusEnum.PLANIFICADO
            )
        assert "end_date debe ser mayor o igual a start_date" in str(exc_info.value)

    def test_schema_update_invalid_dates(self):
        with pytest.raises(ValidationError) as exc_info:
            MesocycleUpdate(
                start_date=date(2026, 5, 10),
                end_date=date(2026, 5, 1)
            )
        assert "end_date debe ser mayor o igual a start_date" in str(exc_info.value)


class TestMesocycleController:
    """Pruebas unitarias del controlador de Mesocycle."""

    def test_create_mesocycle_success(self, db_session, test_user):
        data = MesocycleCreate(
            name="Mesociclo de Hipertrofia",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            user_id=test_user.id,
            status=MesocycleStatusEnum.PLANIFICADO
        )
        mesocycle = mesocycle_controller.create_mesocycle(db_session, data)
        assert mesocycle.id is not None
        assert mesocycle.name == "Mesociclo de Hipertrofia"
        assert mesocycle.user_id == test_user.id
        assert mesocycle.status.value == "PLANIFICADO"

    def test_create_mesocycle_user_not_found(self, db_session):
        data = MesocycleCreate(
            name="Mesociclo Fantasma",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            user_id=99999,
            status=MesocycleStatusEnum.PLANIFICADO
        )
        with pytest.raises(UserNotFoundException):
            mesocycle_controller.create_mesocycle(db_session, data)

    def test_get_mesocycle_by_id_not_found(self, db_session):
        with pytest.raises(MesocycleNotFoundException):
            mesocycle_controller.get_mesocycle_by_id(db_session, 99999)

    def test_update_mesocycle_incompatible_dates(self, db_session, test_user):
        create_data = MesocycleCreate(
            name="Mesociclo Base",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            user_id=test_user.id,
            status=MesocycleStatusEnum.PLANIFICADO
        )
        meso = mesocycle_controller.create_mesocycle(db_session, create_data)

        # Actualizar solo end_date a una fecha previa al start_date existente
        update_data = MesocycleUpdate(end_date=date(2026, 3, 15))
        with pytest.raises(MesocycleDateValidationException):
            mesocycle_controller.update_mesocycle(db_session, meso.id, update_data)

    def test_delete_mesocycle_success(self, db_session, test_user):
        create_data = MesocycleCreate(
            name="Mesociclo a Eliminar",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            user_id=test_user.id,
            status=MesocycleStatusEnum.PLANIFICADO
        )
        meso = mesocycle_controller.create_mesocycle(db_session, create_data)
        mesocycle_controller.delete_mesocycle(db_session, meso.id)

        with pytest.raises(MesocycleNotFoundException):
            mesocycle_controller.get_mesocycle_by_id(db_session, meso.id)


class TestMesocycleHTTPRoutes:
    """Pruebas unitarias de las rutas HTTP y manejo de códigos de error."""

    def test_http_create_mesocycle_201(self, client, test_user):
        payload = {
            "name": "Mesociclo Fuerza Maxima",
            "start_date": "2026-05-01",
            "end_date": "2026-06-01",
            "user_id": test_user.id,
            "status": "PLANIFICADO"
        }
        response = client.post("/mesocycles/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Mesociclo Fuerza Maxima"
        assert data["user_id"] == test_user.id
        assert data["status"] == "PLANIFICADO"

    def test_http_create_mesocycle_invalid_dates_422_or_400(self, client, test_user):
        payload = {
            "name": "Mesociclo Fechas Invalidas",
            "start_date": "2026-06-01",
            "end_date": "2026-05-01",
            "user_id": test_user.id,
            "status": "PLANIFICADO"
        }
        response = client.post("/mesocycles/", json=payload)
        assert response.status_code in [400, 422]

    def test_http_create_mesocycle_user_not_found_404(self, client):
        payload = {
            "name": "Mesociclo Sin Usuario",
            "start_date": "2026-05-01",
            "end_date": "2026-06-01",
            "user_id": 88888,
            "status": "PLANIFICADO"
        }
        response = client.post("/mesocycles/", json=payload)
        assert response.status_code == 404
        assert "User with id 88888 not found" in response.json()["detail"]

    def test_http_get_mesocycle_by_id_200(self, client, test_user):
        payload = {
            "name": "Mesociclo a Consultar",
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
            "user_id": test_user.id,
            "status": "ACTIVO"
        }
        create_res = client.post("/mesocycles/", json=payload)
        created_id = create_res.json()["id"]

        get_res = client.get(f"/mesocycles/{created_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Mesociclo a Consultar"
        assert get_res.json()["status"] == "ACTIVO"

    def test_http_get_mesocycle_not_found_404(self, client):
        response = client.get("/mesocycles/999999")
        assert response.status_code == 404
        assert "Mesocycle with id 999999 not found" in response.json()["detail"]

    def test_http_list_mesocycles_with_filters(self, client, test_user):
        payload1 = {
            "name": "Meso 1",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "user_id": test_user.id,
            "status": "PLANIFICADO"
        }
        payload2 = {
            "name": "Meso 2",
            "start_date": "2026-02-01",
            "end_date": "2026-02-28",
            "user_id": test_user.id,
            "status": "ACTIVO"
        }
        client.post("/mesocycles/", json=payload1)
        client.post("/mesocycles/", json=payload2)

        # Sin filtros
        res_all = client.get("/mesocycles/")
        assert res_all.status_code == 200
        assert len(res_all.json()) == 2

        # Filtro por status ACTIVO
        res_active = client.get("/mesocycles/?status=ACTIVO")
        assert res_active.status_code == 200
        assert len(res_active.json()) == 1
        assert res_active.json()[0]["name"] == "Meso 2"

        # Filtro por usuario inexistente
        res_empty = client.get("/mesocycles/?user_id=77777")
        assert res_empty.status_code == 200
        assert len(res_empty.json()) == 0

    def test_http_update_mesocycle_200(self, client, test_user):
        payload = {
            "name": "Meso Original",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "user_id": test_user.id,
            "status": "PLANIFICADO"
        }
        create_res = client.post("/mesocycles/", json=payload)
        meso_id = create_res.json()["id"]

        update_payload = {
            "name": "Meso Modificado",
            "status": "FINALIZADO"
        }
        update_res = client.put(f"/mesocycles/{meso_id}", json=update_payload)
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Meso Modificado"
        assert update_res.json()["status"] == "FINALIZADO"

    def test_http_update_mesocycle_not_found_404(self, client):
        update_payload = {"name": "No Existe"}
        response = client.put("/mesocycles/999999", json=update_payload)
        assert response.status_code == 404

    def test_http_update_mesocycle_invalid_dates_400(self, client, test_user):
        payload = {
            "name": "Meso Para Fechas",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
            "user_id": test_user.id,
            "status": "PLANIFICADO"
        }
        create_res = client.post("/mesocycles/", json=payload)
        meso_id = create_res.json()["id"]

        # Modificamos end_date a una fecha anterior a start_date (2026-09-01)
        update_payload = {"end_date": "2026-08-15"}
        response = client.put(f"/mesocycles/{meso_id}", json=update_payload)
        assert response.status_code == 400
        assert "end_date debe ser mayor o igual a start_date" in response.json()["detail"]

    def test_http_delete_mesocycle_204_and_then_404(self, client, test_user):
        payload = {
            "name": "Meso Para Borrar",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "user_id": test_user.id,
            "status": "PLANIFICADO"
        }
        create_res = client.post("/mesocycles/", json=payload)
        meso_id = create_res.json()["id"]

        del_res = client.delete(f"/mesocycles/{meso_id}")
        assert del_res.status_code == 204

        # Comprobar que ya no existe (404)
        get_res = client.get(f"/mesocycles/{meso_id}")
        assert get_res.status_code == 404

    def test_http_delete_mesocycle_not_found_404(self, client):
        response = client.delete("/mesocycles/999999")
        assert response.status_code == 404
