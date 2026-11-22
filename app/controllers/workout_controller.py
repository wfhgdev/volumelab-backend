from contextlib import contextmanager

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models.app_user_model import AppUserModel, RoleUser
from app.models.workout_model import ExerciseType, WorkoutModel
from app.schemas.workout_schema import WorkoutBase, WorkoutCreate, WorkoutUpdate


def _database_error(exc: DBAPIError) -> HTTPException:
    sqlstate = getattr(exc.orig, "sqlstate", None)
    diagnostic = getattr(exc.orig, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    context = getattr(diagnostic, "context", "") or ""
    if sqlstate == "23505":
        return HTTPException(409, "A workout with this name already exists")
    if sqlstate == "23503":
        return HTTPException(409, "The workout creator no longer exists")
    if sqlstate in {"23502", "23514", "22P02"}:
        return HTTPException(422, "Workout data violates a database constraint")
    if sqlstate == "P0001" and (
            constraint == "workout_public_limit" or "fn_workout_client_limit" in context
    ):
        return HTTPException(409, "A client can have at most 20 public workouts")
    return HTTPException(500, "An unexpected database error occurred")


@contextmanager
def _database_operation(db: Session):
    try:
        yield
    except DBAPIError as exc:
        db.rollback()
        raise _database_error(exc) from exc
    except HTTPException:
        db.rollback()
        raise


def _find_workout(db: Session, workout_id: int, lock: bool = False) -> WorkoutModel:
    query = db.query(WorkoutModel).filter(WorkoutModel.id == workout_id)
    if lock:
        query = query.with_for_update()
    workout = query.first()
    if workout is None:
        raise HTTPException(404, "Workout not found")
    return workout


def _validate_creator_and_limit(
        db: Session, created_by: int, public: bool, workout_id: int | None = None,
) -> None:
    creator = (
        db.query(AppUserModel)
        .filter(AppUserModel.id == created_by)
        .with_for_update()
        .first()
    )
    if creator is None:
        raise HTTPException(404, "Workout creator not found")
    if not public or RoleUser(creator.role) is not RoleUser.CLIENTE:
        return
    query = db.query(WorkoutModel).filter(
        WorkoutModel.created_by == created_by, WorkoutModel.public.is_(True),
    )
    if workout_id is not None:
        query = query.filter(WorkoutModel.id != workout_id)
    if query.count() >= 20:
        raise HTTPException(409, "A client can have at most 20 public workouts")


def _validate_unique_name(db: Session, name: str, workout_id: int | None = None) -> None:
    query = db.query(WorkoutModel).filter(WorkoutModel.name == name)
    if workout_id is not None:
        query = query.filter(WorkoutModel.id != workout_id)
    if query.first() is not None:
        raise HTTPException(409, "A workout with this name already exists")


def create_workout(db: Session, payload: WorkoutCreate) -> WorkoutModel:
    with _database_operation(db):
        _validate_creator_and_limit(db, payload.created_by, payload.public)
        _validate_unique_name(db, payload.name)
        workout = WorkoutModel(**payload.model_dump())
        db.add(workout)
        db.commit()
        db.refresh(workout)
        return workout


def list_workouts(
        db: Session, skip: int = 0, limit: int = 100,
        created_by: int | None = None, exercise_type: ExerciseType | None = None,
        public: bool | None = None, state: bool | None = None,
) -> list[WorkoutModel]:
    with _database_operation(db):
        query = db.query(WorkoutModel)
        filters = {
            "created_by": created_by, "type": exercise_type,
            "public": public, "state": state,
        }
        for field_name, value in filters.items():
            if value is not None:
                query = query.filter(getattr(WorkoutModel, field_name) == value)
        return query.order_by(WorkoutModel.id.asc()).offset(skip).limit(limit).all()


def get_workout(db: Session, workout_id: int) -> WorkoutModel:
    with _database_operation(db):
        return _find_workout(db, workout_id)


def update_workout(db: Session, workout_id: int, payload: WorkoutUpdate) -> WorkoutModel:
    with _database_operation(db):
        workout = _find_workout(db, workout_id, lock=True)
        changes = payload.model_dump(exclude_unset=True)
        current = {field: getattr(workout, field) for field in WorkoutBase.model_fields}
        try:
            WorkoutBase.model_validate(current | {key: value for key, value in changes.items() if key != "created_by"})
        except ValidationError as exc:
            raise HTTPException(422, "Negative ballast requires a bodyweight exercise") from exc
        if "type" in changes and changes["type"] != workout.type:
            has_sets = db.execute(
                text("SELECT 1 FROM workout_set WHERE exercise_id = :workout_id LIMIT 1"),
                {"workout_id": workout_id},
            ).first()
            if has_sets is not None:
                raise HTTPException(409, "The type of a workout with recorded sets cannot be changed")
        if "name" in changes and changes["name"] != workout.name:
            _validate_unique_name(db, changes["name"], workout_id)
        if {"created_by", "public"} & changes.keys():
            created_by = changes.get("created_by", workout.created_by)
            if created_by is not None:
                _validate_creator_and_limit(db, created_by, changes.get("public", workout.public), workout_id)
        for field_name, value in changes.items():
            setattr(workout, field_name, value)
        db.commit()
        db.refresh(workout)
        return workout


def delete_workout(db: Session, workout_id: int) -> None:
    with _database_operation(db):
        workout = _find_workout(db, workout_id, lock=True)
        workout.state = False
        db.commit()
