from datetime import date
import pytest
from pydantic import ValidationError
from app.schemas.training_week_schema import (
    TrainingWeekCreate,
    TrainingWeekUpdate
)
from app.controllers import training_week_controller
from app.core.exceptions import (
    TrainingWeekNotFoundException,
    TrainingWeekOrderConflictException,
    TrainingWeekDateValidationException,
    MesocycleNotFoundException
)


class TestTrainingWeekSchemaValidations:
    """Pruebas unitarias de las validaciones de esquemas Pydantic para TrainingWeek."""

    def test_schema_valid_dates(self):
        schema = TrainingWeekCreate(
            mesocycle_id=1,
            week_order=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7)
        )
        assert schema.mesocycle_id == 1
        assert schema.week_order == 1
        assert schema.end_date >= schema.start_date

    def test_schema_invalid_dates_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TrainingWeekCreate(
                mesocycle_id=1,
                week_order=1,
                start_date=date(2026, 1, 7),
                end_date=date(2026, 1, 1)
            )
        assert "end_date debe ser mayor o igual a start_date" in str(exc_info.value)

    def test_schema_invalid_week_order_zero(self):
        with pytest.raises(ValidationError) as exc_info:
            TrainingWeekCreate(
                mesocycle_id=1,
                week_order=0,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 7)
            )
        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_schema_update_invalid_dates(self):
        with pytest.raises(ValidationError) as exc_info:
            TrainingWeekUpdate(
                start_date=date(2026, 2, 10),
                end_date=date(2026, 2, 1)
            )
        assert "end_date debe ser mayor o igual a start_date" in str(exc_info.value)


class TestTrainingWeekController:
    """Pruebas unitarias del controlador de TrainingWeek."""

    def test_create_training_week_success(self, db_session, test_mesocycle):
        data = TrainingWeekCreate(
            mesocycle_id=test_mesocycle.id,
            week_order=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7)
        )
        week = training_week_controller.create_training_week(db_session, data)
        assert week.id is not None
        assert week.mesocycle_id == test_mesocycle.id
        assert week.week_order == 1

    def test_create_training_week_mesocycle_not_found(self, db_session):
        data = TrainingWeekCreate(
            mesocycle_id=99999,
            week_order=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7)
        )
        with pytest.raises(MesocycleNotFoundException):
            training_week_controller.create_training_week(db_session, data)

    def test_create_training_week_duplicate_order(self, db_session, test_mesocycle):
        data1 = TrainingWeekCreate(
            mesocycle_id=test_mesocycle.id,
            week_order=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7)
        )
        training_week_controller.create_training_week(db_session, data1)

        data2 = TrainingWeekCreate(
            mesocycle_id=test_mesocycle.id,
            week_order=1,
            start_date=date(2026, 1, 8),
            end_date=date(2026, 1, 14)
        )
        with pytest.raises(TrainingWeekOrderConflictException):
            training_week_controller.create_training_week(db_session, data2)

    def test_create_training_week_invalid_dates(self, db_session, test_mesocycle):
        data = TrainingWeekCreate.model_construct(
            mesocycle_id=test_mesocycle.id,
            week_order=1,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 1)
        )
        with pytest.raises(TrainingWeekDateValidationException):
            training_week_controller.create_training_week(db_session, data)


    def test_get_training_week_by_id_not_found(self, db_session):
        with pytest.raises(TrainingWeekNotFoundException):
            training_week_controller.get_training_week_by_id(db_session, 99999)

    def test_update_training_week_order_conflict(self, db_session, test_mesocycle):
        week1 = training_week_controller.create_training_week(
            db_session,
            TrainingWeekCreate(
                mesocycle_id=test_mesocycle.id,
                week_order=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 7)
            )
        )
        week2 = training_week_controller.create_training_week(
            db_session,
            TrainingWeekCreate(
                mesocycle_id=test_mesocycle.id,
                week_order=2,
                start_date=date(2026, 1, 8),
                end_date=date(2026, 1, 14)
            )
        )
        # Intentar cambiar week2 al orden 1
        with pytest.raises(TrainingWeekOrderConflictException):
            training_week_controller.update_training_week(
                db_session,
                week2.id,
                TrainingWeekUpdate(week_order=1)
            )

    def test_delete_training_week_success(self, db_session, test_mesocycle):
        week = training_week_controller.create_training_week(
            db_session,
            TrainingWeekCreate(
                mesocycle_id=test_mesocycle.id,
                week_order=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 7)
            )
        )
        training_week_controller.delete_training_week(db_session, week.id)

        with pytest.raises(TrainingWeekNotFoundException):
            training_week_controller.get_training_week_by_id(db_session, week.id)


class TestTrainingWeekHTTPRoutes:
    """Pruebas unitarias de las rutas HTTP para TrainingWeek."""

    def test_http_create_training_week_201(self, client, test_mesocycle):
        payload = {
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        }
        response = client.post("/training-weeks/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["mesocycle_id"] == test_mesocycle.id
        assert data["week_order"] == 1

    def test_http_create_training_week_mesocycle_not_found_404(self, client):
        payload = {
            "mesocycle_id": 99999,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        }
        response = client.post("/training-weeks/", json=payload)
        assert response.status_code == 404
        assert "Mesocycle with id 99999 not found" in response.json()["detail"]

    def test_http_create_training_week_duplicate_order_409(self, client, test_mesocycle):
        payload1 = {
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        }
        client.post("/training-weeks/", json=payload1)

        payload2 = {
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-08",
            "end_date": "2026-01-14"
        }
        response = client.post("/training-weeks/", json=payload2)
        assert response.status_code == 409
        assert "already exists for mesocycle" in response.json()["detail"]

    def test_http_create_training_week_invalid_dates_422_or_400(self, client, test_mesocycle):
        payload = {
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-15",
            "end_date": "2026-01-01"
        }
        response = client.post("/training-weeks/", json=payload)
        assert response.status_code in [400, 422]

    def test_http_create_training_week_invalid_order_422(self, client, test_mesocycle):
        payload = {
            "mesocycle_id": test_mesocycle.id,
            "week_order": 0,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        }
        response = client.post("/training-weeks/", json=payload)
        assert response.status_code == 422

    def test_http_get_training_week_by_id_200(self, client, test_mesocycle):
        create_res = client.post("/training-weeks/", json={
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        })
        week_id = create_res.json()["id"]

        get_res = client.get(f"/training-weeks/{week_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == week_id
        assert get_res.json()["week_order"] == 1

    def test_http_get_training_week_not_found_404(self, client):
        response = client.get("/training-weeks/999999")
        assert response.status_code == 404
        assert "Training week with id 999999 not found" in response.json()["detail"]

    def test_http_list_training_weeks_with_filter(self, client, test_mesocycle):
        client.post("/training-weeks/", json={
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        })
        client.post("/training-weeks/", json={
            "mesocycle_id": test_mesocycle.id,
            "week_order": 2,
            "start_date": "2026-01-08",
            "end_date": "2026-01-14"
        })

        res_all = client.get(f"/training-weeks/?mesocycle_id={test_mesocycle.id}")
        assert res_all.status_code == 200
        assert len(res_all.json()) == 2

        res_other = client.get("/training-weeks/?mesocycle_id=88888")
        assert res_other.status_code == 200
        assert len(res_other.json()) == 0

    def test_http_update_training_week_200(self, client, test_mesocycle):
        create_res = client.post("/training-weeks/", json={
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        })
        week_id = create_res.json()["id"]

        update_res = client.put(f"/training-weeks/{week_id}", json={
            "end_date": "2026-01-08"
        })
        assert update_res.status_code == 200
        assert update_res.json()["end_date"] == "2026-01-08"

    def test_http_update_training_week_conflict_409(self, client, test_mesocycle):
        client.post("/training-weeks/", json={
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        })
        res2 = client.post("/training-weeks/", json={
            "mesocycle_id": test_mesocycle.id,
            "week_order": 2,
            "start_date": "2026-01-08",
            "end_date": "2026-01-14"
        })
        week2_id = res2.json()["id"]

        update_res = client.put(f"/training-weeks/{week2_id}", json={
            "week_order": 1
        })
        assert update_res.status_code == 409

    def test_http_delete_training_week_204_and_then_404(self, client, test_mesocycle):
        create_res = client.post("/training-weeks/", json={
            "mesocycle_id": test_mesocycle.id,
            "week_order": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-07"
        })
        week_id = create_res.json()["id"]

        del_res = client.delete(f"/training-weeks/{week_id}")
        assert del_res.status_code == 204

        get_res = client.get(f"/training-weeks/{week_id}")
        assert get_res.status_code == 404

    def test_http_delete_training_week_not_found_404(self, client):
        response = client.delete("/training-weeks/999999")
        assert response.status_code == 404
