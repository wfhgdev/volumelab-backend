from typing import List, Optional
from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.app_user_model import AppUserModel
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import WorkoutSessionModel
from app.schemas.workout_session_schema import SessionStatusEnum, WorkoutSessionCreate, WorkoutSessionUpdate


def get_workout_sessions(
    db: Session,
    user_id: Optional[int] = None,
    week_id: Optional[int] = None,
    status: Optional[SessionStatusEnum] = None,
    public: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[WorkoutSessionModel]:
    query = select(WorkoutSessionModel)
    if user_id is not None:
        query = query.filter(WorkoutSessionModel.user_id == user_id)
    if week_id is not None:
        query = query.filter(WorkoutSessionModel.week_id == week_id)
    if status is not None:
        query = query.filter(WorkoutSessionModel.status == status)
    if public is not None:
        query = query.filter(WorkoutSessionModel.public == public)
    query = query.order_by(WorkoutSessionModel.session_date.desc()).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def get_workout_session_by_id(db: Session, workout_session_id: int) -> WorkoutSessionModel:
    workout_session = db.get(WorkoutSessionModel, workout_session_id)
    if not workout_session:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workout session with id {workout_session_id} not found",
        )
    return workout_session


def create_workout_session(db: Session, workout_session: WorkoutSessionCreate) -> WorkoutSessionModel:
    if not db.get(AppUserModel, workout_session.user_id):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"User with id {workout_session.user_id} not found",
        )
    if workout_session.week_id is not None and not db.get(TrainingWeekModel, workout_session.week_id):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Training week with id {workout_session.week_id} not found",
        )

    db_workout_session = WorkoutSessionModel(
        user_id=workout_session.user_id,
        week_id=workout_session.week_id,
        title=workout_session.title,
        session_date=workout_session.session_date,
        current_bodyweight_kg=workout_session.current_bodyweight_kg,
        observation=workout_session.observation,
        closed_at=workout_session.closed_at,
        public=workout_session.public,
        status=workout_session.status,
    )
    db.add(db_workout_session)
    db.commit()
    db.refresh(db_workout_session)
    return db_workout_session


def update_workout_session(
    db: Session,
    workout_session_id: int,
    workout_session_update: WorkoutSessionUpdate,
) -> WorkoutSessionModel:
    db_workout_session = db.get(WorkoutSessionModel, workout_session_id)
    if not db_workout_session:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workout session with id {workout_session_id} not found",
        )

    update_data = workout_session_update.model_dump(exclude_unset=True)

    target_user_id = update_data.get("user_id", db_workout_session.user_id)
    if "user_id" in update_data and not db.get(AppUserModel, target_user_id):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"User with id {target_user_id} not found",
        )

    target_week_id = update_data.get("week_id", db_workout_session.week_id)
    if "week_id" in update_data and target_week_id is not None:
        if not db.get(TrainingWeekModel, target_week_id):
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Training week with id {target_week_id} not found",
            )

    target_status = update_data.get("status", db_workout_session.status)
    target_closed_at = update_data.get("closed_at", db_workout_session.closed_at)
    status_value = target_status.value if hasattr(target_status, "value") else target_status
    if status_value == "CERRADO" and target_closed_at is None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="closed_at is required when status is CERRADO",
        )
    if status_value == "ABIERTO" and target_closed_at is not None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="closed_at must be null when status is ABIERTO",
        )

    for key, value in update_data.items():
        setattr(db_workout_session, key, value)

    db.commit()
    db.refresh(db_workout_session)
    return db_workout_session


def delete_workout_session(db: Session, workout_session_id: int) -> None:
    db_workout_session = db.get(WorkoutSessionModel, workout_session_id)
    if not db_workout_session:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workout session with id {workout_session_id} not found",
        )
    db.delete(db_workout_session)
    db.commit()
