from typing import List, Optional
from fastapi import HTTPException, status as http_status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.controllers.audit_controller import record_audit_event
from app.core.dependencies import AuditContext
from app.core.permissions import ensure_owner_or_admin, is_admin, resolve_owner_id
from app.models.app_user_model import AppUserModel, RoleUser
from app.models.audit_model import AuditAction
from app.models.mesocycle_model import MesocycleModel
from app.models.training_week_model import TrainingWeekModel
from app.models.workout_session_model import WorkoutSessionModel
from app.schemas.workout_session_schema import SessionStatusEnum, WorkoutSessionCreate, WorkoutSessionUpdate


MAX_PUBLIC_SESSIONS_PER_CLIENT = 20


def get_workout_sessions(
    db: Session,
    current_user: AppUserModel | None = None,
    user_id: Optional[int] = None,
    week_id: Optional[int] = None,
    status: Optional[SessionStatusEnum] = None,
    public: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[WorkoutSessionModel]:
    query = select(WorkoutSessionModel)
    if current_user is not None and not is_admin(current_user):
        query = query.filter(
            or_(
                WorkoutSessionModel.user_id == current_user.id,
                WorkoutSessionModel.public.is_(True),
            )
        )
    elif user_id is not None:
        query = query.filter(WorkoutSessionModel.user_id == user_id)

    if week_id is not None:
        query = query.filter(WorkoutSessionModel.week_id == week_id)
    if status is not None:
        query = query.filter(WorkoutSessionModel.status == status)
    if public is not None:
        query = query.filter(WorkoutSessionModel.public == public)
    query = query.order_by(
        WorkoutSessionModel.session_date.desc(),
        WorkoutSessionModel.id.desc(),
    ).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def get_workout_session_by_id(
    db: Session, workout_session_id: int, current_user: AppUserModel | None = None
) -> WorkoutSessionModel:
    workout_session = db.get(WorkoutSessionModel, workout_session_id)
    if not workout_session:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workout session with id {workout_session_id} not found",
        )
    if current_user is not None and not is_admin(current_user) and workout_session.user_id != current_user.id and not workout_session.public:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workout session with id {workout_session_id} not found",
        )
    return workout_session


def _get_user_or_404(db: Session, user_id: int) -> AppUserModel:
    user = db.get(AppUserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return user


def _validate_week_ownership(db: Session, week_id: int, user_id: int) -> None:
    week = db.get(TrainingWeekModel, week_id)
    if not week:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Training week with id {week_id} not found",
        )

    mesocycle = db.get(MesocycleModel, week.mesocycle_id)
    if not mesocycle:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Mesocycle with id {week.mesocycle_id} not found",
        )

    if mesocycle.user_id != user_id:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Training week with id {week_id} does not belong to user {user_id}",
        )


def _validate_public_session_quota(
    db: Session,
    user_id: int,
    role,
    exclude_session_id: Optional[int] = None,
) -> None:
    role_value = getattr(role, "value", role)
    if role_value != RoleUser.CLIENTE.value:
        return

    query = select(func.count(WorkoutSessionModel.id)).where(
        WorkoutSessionModel.user_id == user_id,
        WorkoutSessionModel.public.is_(True),
    )
    if exclude_session_id is not None:
        query = query.where(WorkoutSessionModel.id != exclude_session_id)

    public_session_count = db.scalar(query) or 0
    if public_session_count >= MAX_PUBLIC_SESSIONS_PER_CLIENT:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CLIENTE cannot have more than {MAX_PUBLIC_SESSIONS_PER_CLIENT} public workout sessions",
        )


def create_workout_session(
    db: Session,
    workout_session: WorkoutSessionCreate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> WorkoutSessionModel:
    if current_user is not None:
        owner_id = resolve_owner_id(current_user, workout_session.user_id)
    else:
        owner_id = workout_session.user_id
    user = _get_user_or_404(db, owner_id)

    if workout_session.week_id is not None:
        _validate_week_ownership(db, workout_session.week_id, owner_id)

    if workout_session.public:
        _validate_public_session_quota(db, owner_id, user.role)

    db_workout_session = WorkoutSessionModel(
        user_id=owner_id,
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
    db.flush()
    if audit_context is not None:
        record_audit_event(
            db, "workout_session", str(db_workout_session.id), AuditAction.INSERT, audit_context
        )
    db.commit()
    db.refresh(db_workout_session)
    return db_workout_session


def update_workout_session(
    db: Session,
    workout_session_id: int,
    workout_session_update: WorkoutSessionUpdate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> WorkoutSessionModel:
    db_workout_session = db.get(WorkoutSessionModel, workout_session_id)
    if not db_workout_session:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workout session with id {workout_session_id} not found",
        )
    if current_user is not None:
        ensure_owner_or_admin(
            current_user,
            db_workout_session.user_id,
            is_private=not db_workout_session.public,
        )

    update_data = workout_session_update.model_dump(exclude_unset=True)

    if "user_id" in update_data and update_data["user_id"] is not None:
        if current_user is not None:
            target_user_id = resolve_owner_id(current_user, update_data["user_id"])
        else:
            target_user_id = update_data["user_id"]
        update_data["user_id"] = target_user_id
    else:
        target_user_id = db_workout_session.user_id

    user = _get_user_or_404(db, target_user_id)

    target_week_id = update_data.get("week_id", db_workout_session.week_id)
    if target_week_id is not None and ("week_id" in update_data or "user_id" in update_data):
        _validate_week_ownership(db, target_week_id, target_user_id)

    target_public = update_data.get("public", db_workout_session.public)
    if target_public:
        _validate_public_session_quota(
            db,
            target_user_id,
            user.role,
            exclude_session_id=workout_session_id,
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

    if audit_context is not None:
        record_audit_event(
            db, "workout_session", str(db_workout_session.id), AuditAction.UPDATE, audit_context
        )
    db.commit()
    db.refresh(db_workout_session)
    return db_workout_session


def delete_workout_session(
    db: Session,
    workout_session_id: int,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> None:
    db_workout_session = db.get(WorkoutSessionModel, workout_session_id)
    if not db_workout_session:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workout session with id {workout_session_id} not found",
        )
    if current_user is not None:
        ensure_owner_or_admin(
            current_user,
            db_workout_session.user_id,
            is_private=not db_workout_session.public,
        )
    record_id = str(db_workout_session.id)
    db.delete(db_workout_session)
    if audit_context is not None:
        record_audit_event(db, "workout_session", record_id, AuditAction.DELETE, audit_context)
    db.commit()
