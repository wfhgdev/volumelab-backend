from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError

from app.controllers.workout_controller import create_workout, delete_workout, get_workout, list_workouts, update_workout
from app.models.app_user_model import AppUserModel, RoleUser
from app.models.workout_model import ExerciseType, WorkoutModel
from app.schemas.workout_schema import WorkoutCreate, WorkoutUpdate


def make_workout(**changes):
    values = {
        "id": 1, "name": "Squat", "type": ExerciseType.DYNAMIC,
        "description": None, "created_by": 1, "is_bodyweight": False,
        "allow_positive_ballast": True, "allow_negative_ballast": False,
        "public": False, "state": True,
    }
    return WorkoutModel(**(values | changes))


def database_with_workout(workout):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = workout
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = workout
    return db


def test_creation_checks_creator_and_commits():
    db = MagicMock()
    creator = AppUserModel(id=1, role=RoleUser.CLIENTE)
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = creator
    db.query.return_value.filter.return_value.first.return_value = None
    result = create_workout(db, WorkoutCreate(name="Squat", type="DINAMICO", created_by=1))
    assert result.name == "Squat"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(result)


def test_creation_rejects_missing_creator():
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
    with pytest.raises(HTTPException) as error:
        create_workout(db, WorkoutCreate(name="Squat", type="DINAMICO", created_by=99))
    assert error.value.status_code == 404
    db.commit.assert_not_called()


def test_creation_rejects_duplicate_name():
    db = database_with_workout(make_workout())
    with pytest.raises(HTTPException) as error:
        create_workout(db, WorkoutCreate(name="Squat", type="DINAMICO", created_by=1))
    assert error.value.status_code == 409
    db.commit.assert_not_called()


@pytest.mark.parametrize("operation", [
    lambda db: get_workout(db, 99),
    lambda db: update_workout(db, 99, WorkoutUpdate(name="Plank")),
    lambda db: delete_workout(db, 99),
])
def test_missing_workout_returns_not_found(operation):
    with pytest.raises(HTTPException) as error:
        operation(database_with_workout(None))
    assert error.value.status_code == 404


def test_partial_update_validates_against_existing_flags():
    workout = make_workout(is_bodyweight=True, allow_negative_ballast=True)
    db = database_with_workout(workout)
    with pytest.raises(HTTPException) as error:
        update_workout(db, 1, WorkoutUpdate(is_bodyweight=False))
    assert error.value.status_code == 422
    assert workout.is_bodyweight
    db.commit.assert_not_called()


def test_type_change_with_recorded_sets_is_rejected():
    db = database_with_workout(make_workout())
    db.execute.return_value.first.return_value = (1,)
    with pytest.raises(HTTPException) as error:
        update_workout(db, 1, WorkoutUpdate(type="ISOMETRICO"))
    assert error.value.status_code == 409
    db.commit.assert_not_called()


def test_type_change_without_sets_is_allowed():
    db = database_with_workout(make_workout())
    db.execute.return_value.first.return_value = None
    result = update_workout(db, 1, WorkoutUpdate(type="ISOMETRICO", description=None))
    assert result.type is ExerciseType.ISOMETRIC
    db.commit.assert_called_once()


def test_deletion_is_logical_and_repeatable():
    workout = make_workout()
    db = database_with_workout(workout)
    delete_workout(db, 1)
    delete_workout(db, 1)
    assert workout.state is False
    assert db.commit.call_count == 2
    db.delete.assert_not_called()


@pytest.mark.parametrize(("sqlstate", "expected"), [
    ("23505", 409), ("23503", 409), ("23514", 422),
    ("23502", 422), ("22P02", 422), ("08006", 500),
])
def test_database_errors_are_sanitized_and_rolled_back(sqlstate, expected):
    db = database_with_workout(make_workout())
    original = SimpleNamespace(sqlstate=sqlstate, diag=None)
    db.commit.side_effect = DBAPIError("private SQL", {}, original)
    with pytest.raises(HTTPException) as error:
        delete_workout(db, 1)
    assert error.value.status_code == expected
    assert "private SQL" not in error.value.detail
    db.rollback.assert_called_once()


def test_read_errors_are_sanitized():
    db = MagicMock()
    db.query.side_effect = DBAPIError("private SQL", {}, SimpleNamespace(sqlstate="08006"))
    with pytest.raises(HTTPException) as error:
        list_workouts(db)
    assert error.value.status_code == 500
    db.rollback.assert_called_once()


def test_existing_trigger_limit_is_translated():
    db = database_with_workout(make_workout())
    original = SimpleNamespace(sqlstate="P0001", diag=SimpleNamespace(constraint_name=None, context="PL/pgSQL function fn_workout_client_limit()"))
    db.commit.side_effect = DBAPIError("UPDATE", {}, original)
    with pytest.raises(HTTPException) as error:
        delete_workout(db, 1)
    assert error.value.status_code == 409
