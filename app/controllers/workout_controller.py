from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.app_user_model import AppUserModel, RoleUser
from app.models.workout_model import ExerciseType, WorkoutModel
from app.schemas.workout_schema import WorkoutBase, WorkoutCreate, WorkoutUpdate


def _find_workout(db: Session, workout_id: int, lock: bool = False) -> WorkoutModel:
    query = db.query(WorkoutModel).filter(WorkoutModel.id == workout_id)
    if lock:
        query = query.with_for_update()
    workout = query.first()
    if workout is None:
        raise HTTPException(404, "Ejercicio no encontrado")
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
        raise HTTPException(404, "Usuario creador no encontrado")
    if not public or RoleUser(creator.role) is not RoleUser.CLIENTE:
        return
    query = db.query(WorkoutModel).filter(
        WorkoutModel.created_by == created_by, WorkoutModel.public.is_(True),
    )
    if workout_id is not None:
        query = query.filter(WorkoutModel.id != workout_id)
    if query.count() >= 20:
        raise HTTPException(409, "Un cliente puede tener como máximo 20 ejercicios públicos")


def _validate_unique_name(db: Session, name: str, workout_id: int | None = None) -> None:
    query = db.query(WorkoutModel).filter(WorkoutModel.name == name)
    if workout_id is not None:
        query = query.filter(WorkoutModel.id != workout_id)
    if query.first() is not None:
        raise HTTPException(409, "Ya existe un ejercicio con este nombre")


def create_workout(db: Session, payload: WorkoutCreate) -> WorkoutModel:
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
    return _find_workout(db, workout_id)


def update_workout(db: Session, workout_id: int, payload: WorkoutUpdate) -> WorkoutModel:
    workout = _find_workout(db, workout_id, lock=True)
    changes = payload.model_dump(exclude_unset=True)
    current = {field: getattr(workout, field) for field in WorkoutBase.model_fields}
    try:
        WorkoutBase.model_validate(current | {key: value for key, value in changes.items() if key != "created_by"})
    except ValidationError as exc:
        raise HTTPException(422, "Un lastre negativo requiere un ejercicio con peso corporal") from exc
    if "type" in changes and changes["type"] != workout.type:
        has_sets = db.execute(
            text("SELECT 1 FROM workout_set WHERE exercise_id = :workout_id LIMIT 1"),
            {"workout_id": workout_id},
        ).first()
        if has_sets is not None:
            raise HTTPException(409, "No se puede cambiar el tipo de un ejercicio que ya tiene series registradas")
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
    workout = _find_workout(db, workout_id, lock=True)
    workout.state = False
    db.commit()
