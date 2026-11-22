from fastapi import HTTPException
import pytest
from pydantic import ValidationError

from app.controllers import workout_rate_controller
from app.main import app
from app.models.app_user_model import AppUserModel
from app.models.workout_model import WorkoutModel
from app.models.workout_rate_model import WorkoutRateModel
from app.schemas.workout_rate_schema import WorkoutRateCreate, WorkoutRateUpdate


@pytest.fixture
def rate_records(postgres_db):
    user = AppUserModel(name="Rate user", email="rate@example.com", password_hash="test", role="CLIENTE",
                        status="ACTIVO")
    postgres_db.add(user)
    postgres_db.commit()
    public = WorkoutModel(name="Public exercise", type="DINAMICO", created_by=user.id, public=True)
    private = WorkoutModel(name="Private exercise", type="DINAMICO", created_by=user.id)
    postgres_db.add_all([public, private])
    postgres_db.commit()
    return postgres_db, user, public, private


def test_openapi_schema():
    paths = app.openapi()["paths"]
    assert "/workout-rates/" in paths
    assert "/workout-rates/{rate_id}" in paths
    assert "/workout-rates/upsert" in paths
    assert "/workout-rates/workout/{id_workout}/score" in paths
    assert "/workout-rates/workout/{id_workout}/user/{user_id}" in paths


@pytest.mark.parametrize("rate", [0, 6])
def test_pydantic_validation(rate):
    with pytest.raises(ValidationError):
        WorkoutRateCreate(id_workout=1, user_id=1, rate=rate)


@pytest.mark.postgres
def test_get_workout_rates_list(rate_records):
    db, user, public, _ = rate_records
    db.add(WorkoutRateModel(id_workout=public.id, user_id=user.id, rate=4))
    db.commit()
    rates = workout_rate_controller.get_workout_rates(db, skip=0, limit=10, id_workout=public.id)
    assert len(rates) == 1


@pytest.mark.postgres
def test_get_workout_score(rate_records):
    db, user, public, _ = rate_records
    db.add(WorkoutRateModel(id_workout=public.id, user_id=user.id, rate=4))
    db.commit()
    score = workout_rate_controller.get_workout_score(db, id_workout=public.id)
    assert score == {"id_workout": public.id, "avg_rate": 4.0, "total_rates": 1}


@pytest.mark.postgres
def test_reject_private_workout_rate(rate_records):
    db, user, _, private = rate_records
    with pytest.raises(HTTPException) as error:
        workout_rate_controller.create_workout_rate(db,
                                                    WorkoutRateCreate(id_workout=private.id, user_id=user.id, rate=5))
    assert error.value.status_code == 400


@pytest.mark.postgres
def test_crud_lifecycle_and_upsert(rate_records):
    db, user, public, _ = rate_records
    payload = WorkoutRateCreate(id_workout=public.id, user_id=user.id, rate=4)
    created = workout_rate_controller.create_workout_rate(db, payload)
    rate_id = created.id
    assert workout_rate_controller.get_workout_rate_by_id(db, rate_id).rate == 4
    assert workout_rate_controller.get_workout_rate_by_workout_and_user(db, public.id, user.id).id == rate_id
    with pytest.raises(HTTPException) as error:
        workout_rate_controller.create_workout_rate(db, payload)
    assert error.value.status_code == 409
    assert workout_rate_controller.update_workout_rate(db, rate_id, WorkoutRateUpdate(rate=5)).rate == 5
    assert workout_rate_controller.upsert_workout_rate(db, WorkoutRateCreate(id_workout=public.id, user_id=user.id,
                                                                             rate=3)).rate == 3
    workout_rate_controller.delete_workout_rate(db, rate_id)
    with pytest.raises(HTTPException) as error:
        workout_rate_controller.get_workout_rate_by_id(db, rate_id)
    assert error.value.status_code == 404
