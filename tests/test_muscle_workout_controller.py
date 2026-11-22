from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest
from sqlalchemy.exc import DBAPIError

from app.controllers import muscle_workout_controller as controller
from app.models.muscle_group_model import MuscleGroupModel
from app.models.muscle_workout_model import MuscleRole, MuscleWorkoutModel
from app.models.workout_model import WorkoutModel
from app.schemas.muscle_workout_schema import MuscleWorkoutCreate, MuscleWorkoutUpdate


class DatabaseError(Exception):
    def __init__(self, sqlstate):
        super().__init__("Private SQL details")
        self.sqlstate = sqlstate


@pytest.fixture
def database(monkeypatch):
    db = MagicMock()
    queries = {model: MagicMock() for model in (WorkoutModel, MuscleGroupModel, MuscleWorkoutModel)}
    for query in queries.values():
        query.filter.return_value = query
        query.with_for_update.return_value = query
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
    queries[MuscleWorkoutModel].first.return_value = None
    db.query.side_effect = lambda model: queries[model]
    inspector = MagicMock()
    inspector.has_table.return_value = False
    monkeypatch.setattr(controller, "inspect", lambda bind: inspector)
    return db, queries, inspector


def payload():
    return MuscleWorkoutCreate(workout_id=1, muscle_group_id=2, muscle_role=MuscleRole.PRIMARY)


def existing_record():
    return MuscleWorkoutModel(workout_id=1, muscle_group_id=2, muscle_role=MuscleRole.PRIMARY, weighing=100)


def test_creation_locks_workout_and_commits(database):
    db, queries, _ = database
    record = controller.create_muscle_workout(db, payload())
    assert record.weighing == 100
    queries[WorkoutModel].with_for_update.assert_called_once()
    queries[MuscleGroupModel].with_for_update.assert_called_once_with(read=True, key_share=True)
    db.commit.assert_called_once()


@pytest.mark.parametrize("model", [WorkoutModel, MuscleGroupModel])
def test_missing_parent_returns_not_found(database, model):
    db, queries, _ = database
    queries[model].first.return_value = None
    with pytest.raises(HTTPException) as error:
        controller.create_muscle_workout(db, payload())
    assert error.value.status_code == 404
    db.commit.assert_not_called()


def test_duplicate_pair_is_rejected(database):
    db, queries, _ = database
    queries[MuscleWorkoutModel].first.return_value = existing_record()
    with pytest.raises(HTTPException) as error:
        controller.create_muscle_workout(db, payload())
    assert error.value.status_code == 409


@pytest.mark.parametrize("operation", [
    lambda db: controller.get_muscle_workout(db, 1, 2),
    lambda db: controller.update_muscle_workout(db, 1, 2, MuscleWorkoutUpdate()),
    lambda db: controller.delete_muscle_workout(db, 1, 2),
])
def test_missing_association_returns_not_found(database, operation):
    db, _, _ = database
    with pytest.raises(HTTPException) as error:
        operation(db)
    assert error.value.status_code == 404


@pytest.mark.parametrize("operation", [
    lambda db: controller.create_muscle_workout(db, payload()),
    lambda db: controller.update_muscle_workout(db, 1, 2, MuscleWorkoutUpdate()),
    lambda db: controller.delete_muscle_workout(db, 1, 2),
])
def test_recorded_sets_block_all_writes(database, operation):
    db, queries, inspector = database
    queries[MuscleWorkoutModel].first.return_value = existing_record()
    inspector.has_table.return_value = True
    db.execute.return_value.first.return_value = (1,)
    with pytest.raises(HTTPException) as error:
        operation(db)
    assert error.value.status_code == 409
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_role_update_changes_weighing_atomically(database):
    db, queries, _ = database
    queries[MuscleWorkoutModel].first.return_value = existing_record()
    record = controller.update_muscle_workout(db, 1, 2, MuscleWorkoutUpdate(muscle_role=MuscleRole.SECONDARY))
    assert (record.muscle_role, record.weighing) == (MuscleRole.SECONDARY, 50)
    db.commit.assert_called_once()


def test_weighing_only_update_validates_existing_role(database):
    db, queries, _ = database
    queries[MuscleWorkoutModel].first.return_value = existing_record()
    with pytest.raises(HTTPException) as error:
        controller.update_muscle_workout(db, 1, 2, MuscleWorkoutUpdate(weighing=50))
    assert error.value.status_code == 422
    db.commit.assert_not_called()


def test_delete_only_removes_association(database):
    db, queries, _ = database
    record = existing_record()
    queries[MuscleWorkoutModel].first.return_value = record
    controller.delete_muscle_workout(db, 1, 2)
    db.delete.assert_called_once_with(record)
    db.commit.assert_called_once()


@pytest.mark.parametrize(("sqlstate", "status"), [
    ("23505", 409), ("23503", 409), ("23514", 422),
    ("23502", 422), ("22P02", 422), ("08006", 500),
])
def test_database_errors_are_sanitized_and_rolled_back(database, sqlstate, status):
    db, _, _ = database
    db.commit.side_effect = DBAPIError("Private SQL", {}, DatabaseError(sqlstate))
    with pytest.raises(HTTPException) as error:
        controller.create_muscle_workout(db, payload())
    assert error.value.status_code == status
    assert "Private" not in error.value.detail
    db.rollback.assert_called_once()
