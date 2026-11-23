from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.muscle_group_model import MuscleGroupModel
from app.models.muscle_workout_model import MuscleRole, MuscleWorkoutModel
from app.models.workout_model import WorkoutModel
from app.schemas.muscle_workout_schema import MuscleWorkoutCreate, MuscleWorkoutUpdate, resolve_weighing


def _lock_workout(db: Session, workout_id: int) -> None:
    workout = db.query(WorkoutModel).filter(WorkoutModel.id == workout_id).with_for_update().first()
    if workout is None:
        raise HTTPException(404, "Workout not found")


def _validate_muscle_group(db: Session, muscle_group_id: int) -> None:
    group = (
        db.query(MuscleGroupModel)
        .filter(MuscleGroupModel.id == muscle_group_id)
        .with_for_update(read=True, key_share=True)
        .first()
    )
    if group is None:
        raise HTTPException(404, "Muscle group not found")


def _ensure_no_recorded_sets(db: Session, workout_id: int) -> None:
    if not inspect(db.get_bind()).has_table("workout_set"):
        return
    existing = db.execute(
        text("SELECT 1 FROM workout_set WHERE exercise_id = :workout_id LIMIT 1"),
        {"workout_id": workout_id},
    ).first()
    if existing is not None:
        raise HTTPException(409, "Muscle associations cannot change after the workout has recorded sets")


def _association_query(db: Session, workout_id: int, muscle_group_id: int):
    return db.query(MuscleWorkoutModel).filter(
        MuscleWorkoutModel.workout_id == workout_id,
        MuscleWorkoutModel.muscle_group_id == muscle_group_id,
    )


def _find_association(db: Session, workout_id: int, muscle_group_id: int) -> MuscleWorkoutModel:
    record = _association_query(db, workout_id, muscle_group_id).first()
    if record is None:
        raise HTTPException(404, "Muscle association not found")
    return record


def create_muscle_workout(db: Session, payload: MuscleWorkoutCreate) -> MuscleWorkoutModel:
    _lock_workout(db, payload.workout_id)
    _validate_muscle_group(db, payload.muscle_group_id)
    _ensure_no_recorded_sets(db, payload.workout_id)
    if _association_query(db, payload.workout_id, payload.muscle_group_id).first() is not None:
        raise HTTPException(409, "This workout and muscle group are already associated")
    record = MuscleWorkoutModel(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_muscle_workouts(
    db: Session, skip: int = 0, limit: int = 100,
    workout_id: int | None = None, muscle_group_id: int | None = None,
    muscle_role: MuscleRole | None = None,
) -> list[MuscleWorkoutModel]:
    query = db.query(MuscleWorkoutModel)
    for field_name, value in {
        "workout_id": workout_id, "muscle_group_id": muscle_group_id, "muscle_role": muscle_role,
    }.items():
        if value is not None:
            query = query.filter(getattr(MuscleWorkoutModel, field_name) == value)
    return query.order_by(
        MuscleWorkoutModel.workout_id.asc(), MuscleWorkoutModel.muscle_group_id.asc(),
    ).offset(skip).limit(limit).all()


def get_muscle_workout(db: Session, workout_id: int, muscle_group_id: int) -> MuscleWorkoutModel:
    return _find_association(db, workout_id, muscle_group_id)


def update_muscle_workout(
    db: Session, workout_id: int, muscle_group_id: int, payload: MuscleWorkoutUpdate,
) -> MuscleWorkoutModel:
    _lock_workout(db, workout_id)
    record = _find_association(db, workout_id, muscle_group_id)
    _ensure_no_recorded_sets(db, workout_id)
    role = payload.muscle_role or record.muscle_role
    try:
        weighing = resolve_weighing(role, payload.weighing)
    except ValueError as exc:
        raise HTTPException(422, "The weighing must match the muscle role") from exc
    record.muscle_role = role
    record.weighing = weighing
    db.commit()
    db.refresh(record)
    return record


def delete_muscle_workout(db: Session, workout_id: int, muscle_group_id: int) -> None:
    _lock_workout(db, workout_id)
    record = _find_association(db, workout_id, muscle_group_id)
    _ensure_no_recorded_sets(db, workout_id)
    db.delete(record)
    db.commit()
