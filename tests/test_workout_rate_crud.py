from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.controllers import workout_rate_controller
from app.main import app
from app.models.app_user_model import AppUserModel, RoleUser, UserStatus
from app.schemas.workout_rate_schema import WorkoutRateCreate, WorkoutRateUpdate


def create_user(db_session) -> AppUserModel:
    user = AppUserModel(
        email=f"workout_rate_{uuid4().hex}@example.com",
        password_hash="hash",
        name="Rate",
        role=RoleUser.CLIENTE,
        status=UserStatus.ACTIVO,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_workout(
    db_session, creator_id: int, public: bool = True, state: bool = True
) -> int:
    workout_id = db_session.execute(
        text(
            """
            INSERT INTO workout (
                name,
                description,
                type,
                is_bodyweight,
                allow_positive_ballast,
                allow_negative_ballast,
                public,
                state,
                created_by
            )
            VALUES (
                :name,
                NULL,
                'DINAMICO',
                false,
                false,
                false,
                :public,
                :state,
                :created_by
            )
            RETURNING id
            """
        ),
        {
            "name": f"workout_{uuid4().hex}",
            "public": public,
            "state": state,
            "created_by": creator_id,
        },
    ).scalar_one()
    db_session.commit()
    return workout_id


def test_openapi_schema():
    schema = app.openapi()
    paths = schema["paths"]
    assert "/workout-rates/" in paths
    assert "/workout-rates/{rate_id}" in paths
    assert "/workout-rates/upsert" in paths
    assert "/workout-rates/workout/{id_workout}/score" in paths
    assert "/workout-rates/workout/{id_workout}/user/{user_id}" in paths


def test_pydantic_validation():
    with pytest.raises(Exception):
        WorkoutRateCreate(id_workout=2, user_id=1, rate=0)
    with pytest.raises(Exception):
        WorkoutRateCreate(id_workout=2, user_id=1, rate=6)

    valid_schema = WorkoutRateCreate(id_workout=2, user_id=1, rate=4)
    assert valid_schema.rate == 4


def test_get_workout_rates_list(db_session):
    user = create_user(db_session)
    workout_id = create_workout(db_session, user.id)
    rate = workout_rate_controller.create_workout_rate(
        db_session,
        WorkoutRateCreate(id_workout=workout_id, user_id=user.id, rate=4),
    )

    rates = workout_rate_controller.get_workout_rates(db_session, skip=0, limit=10)

    assert any(item.id == rate.id for item in rates)


def test_get_workout_score(db_session):
    user = create_user(db_session)
    workout_id = create_workout(db_session, user.id)
    workout_rate_controller.create_workout_rate(
        db_session,
        WorkoutRateCreate(id_workout=workout_id, user_id=user.id, rate=5),
    )

    score = workout_rate_controller.get_workout_score(db_session, id_workout=workout_id)

    assert score["id_workout"] == workout_id
    assert score["total_rates"] == 1
    assert score["avg_rate"] == 5.0


def test_reject_private_workout_rate(db_session):
    user = create_user(db_session)
    workout_id = create_workout(db_session, user.id, public=False)

    with pytest.raises(HTTPException) as exc:
        workout_rate_controller.create_workout_rate(
            db_session,
            WorkoutRateCreate(id_workout=workout_id, user_id=user.id, rate=5),
        )

    assert exc.value.status_code == 400
    assert "debe ser público y estar activo" in exc.value.detail


def test_crud_lifecycle_and_upsert(db_session):
    user = create_user(db_session)
    workout_id = create_workout(db_session, user.id)

    new_rate = WorkoutRateCreate(id_workout=workout_id, user_id=user.id, rate=4)
    created = workout_rate_controller.create_workout_rate(db_session, new_rate)
    assert created.id is not None
    assert created.rate == 4
    rate_id = created.id

    fetched = workout_rate_controller.get_workout_rate_by_id(db_session, rate_id)
    assert fetched.id == rate_id
    assert fetched.rate == 4

    fetched_by_user = workout_rate_controller.get_workout_rate_by_workout_and_user(
        db_session, id_workout=workout_id, user_id=user.id
    )
    assert fetched_by_user.id == rate_id

    with pytest.raises(HTTPException) as exc:
        workout_rate_controller.create_workout_rate(db_session, new_rate)
    assert exc.value.status_code == 409

    updated = workout_rate_controller.update_workout_rate(
        db_session, rate_id, WorkoutRateUpdate(rate=5)
    )
    assert updated.rate == 5

    upserted = workout_rate_controller.upsert_workout_rate(
        db_session,
        WorkoutRateCreate(id_workout=workout_id, user_id=user.id, rate=3),
    )
    assert upserted.id == rate_id
    assert upserted.rate == 3

    workout_rate_controller.delete_workout_rate(db_session, rate_id)

    with pytest.raises(HTTPException) as exc:
        workout_rate_controller.get_workout_rate_by_id(db_session, rate_id)
    assert exc.value.status_code == 404
