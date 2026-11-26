from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.controllers.audit_controller import record_audit_event
from app.core.dependencies import AuditContext
from app.core.permissions import ensure_owner_or_admin, is_admin, resolve_owner_id
from app.models.app_user_model import AppUserModel
from app.models.audit_model import AuditAction
from app.models.workout_model import WorkoutModel
from app.models.workout_rate_model import WorkoutRateModel
from app.schemas.workout_rate_schema import (
    WorkoutRateCreate,
    WorkoutRateUpdate,
)


def create_workout_rate(
    db: Session,
    workout_rate: WorkoutRateCreate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> WorkoutRateModel:
    """
    Crea una nueva valoración para un ejercicio público y activo.

    Reglas aplicadas:
    - RN-18: Comprueba unicidad de voto por usuario y ejercicio (uq_workout_rate_user).
    - Valida trigger trg_workout_rate_check_public (el ejercicio debe ser público y estar activo).
    """
    owner_id = resolve_owner_id(current_user, workout_rate.user_id) if current_user else workout_rate.user_id

    existing_rate = db.query(WorkoutRateModel).filter(
        WorkoutRateModel.id_workout == workout_rate.id_workout,
        WorkoutRateModel.user_id == owner_id,
    ).first()

    if existing_rate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El usuario {owner_id} ya ha valorado el ejercicio {workout_rate.id_workout}. Utilice el endpoint de actualización para modificar su puntuación.",
        )

    db_workout_rate = WorkoutRateModel(
        id_workout=workout_rate.id_workout,
        user_id=owner_id,
        rate=workout_rate.rate,
    )

    try:
        db.add(db_workout_rate)
        db.flush()
        if audit_context is not None:
            record_audit_event(
                db, "workout_rate", str(db_workout_rate.id), AuditAction.INSERT, audit_context
            )
        db.commit()
        db.refresh(db_workout_rate)
        return db_workout_rate
    except IntegrityError as exc:
        db.rollback()
        orig = getattr(exc, "orig", None)
        error_msg = str(orig) if orig is not None else str(exc)
        lowered = error_msg.lower()
        if "uq_workout_rate_user" in lowered or "unique" in lowered:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya ha valorado este ejercicio.",
            )
        if "fk_workout_rate_workout" in lowered or "workout" in lowered:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El ejercicio con id {workout_rate.id_workout} no existe.",
            )
        if "fk_workout_rate_user" in lowered or "app_user" in lowered:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El usuario con id {owner_id} no existe.",
            )
        if "chk_workout_rate" in lowered or "check" in lowered:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La puntuación debe estar comprendida entre 1 y 5.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error de integridad al guardar la valoración.",
        )
    except DBAPIError as exc:
        db.rollback()
        orig = getattr(exc, "orig", None)
        error_msg = str(orig) if orig is not None else str(exc)
        if "debe ser público y estar activo" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El ejercicio {workout_rate.id_workout} debe ser público y estar activo para valorarlo.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error en base de datos: {error_msg}",
        )


def get_workout_rates(
    db: Session,
    current_user: AppUserModel | None = None,
    skip: int = 0,
    limit: int = 100,
    id_workout: Optional[int] = None,
    user_id: Optional[int] = None,
) -> list[WorkoutRateModel]:
    """Obtiene una lista paginada de valoraciones con filtros opcionales."""
    query = db.query(WorkoutRateModel)

    if current_user and not is_admin(current_user):
        query = query.filter(WorkoutRateModel.user_id == current_user.id)
    elif user_id is not None:
        query = query.filter(WorkoutRateModel.user_id == user_id)

    if id_workout is not None:
        query = query.filter(WorkoutRateModel.id_workout == id_workout)

    return query.order_by(WorkoutRateModel.id.desc()).offset(skip).limit(limit).all()


def get_workout_rate_by_id(
    db: Session, rate_id: int, current_user: AppUserModel | None = None
) -> WorkoutRateModel:
    """Obtiene una valoración por su ID primario."""
    db_rate = db.query(WorkoutRateModel).filter(WorkoutRateModel.id == rate_id).first()
    if db_rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valoración con id {rate_id} no encontrada.",
        )
    if current_user:
        ensure_owner_or_admin(current_user, db_rate.user_id, is_private=True)
    return db_rate


def get_workout_rate_by_workout_and_user(
    db: Session, id_workout: int, user_id: int, current_user: AppUserModel | None = None
) -> WorkoutRateModel:
    """Obtiene la valoración que un usuario específico hizo a un ejercicio."""
    if current_user and not is_admin(current_user) and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario {user_id} no ha valorado el ejercicio {id_workout}.",
        )

    db_rate = db.query(WorkoutRateModel).filter(
        WorkoutRateModel.id_workout == id_workout,
        WorkoutRateModel.user_id == user_id,
    ).first()

    if db_rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario {user_id} no ha valorado el ejercicio {id_workout}.",
        )
    return db_rate


def update_workout_rate(
    db: Session,
    rate_id: int,
    workout_rate_update: WorkoutRateUpdate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> WorkoutRateModel:
    """
    Actualiza la puntuación de una valoración existente.
    """
    db_rate = get_workout_rate_by_id(db, rate_id, current_user)
    db_rate.rate = workout_rate_update.rate
    try:
        db.flush()
        if audit_context is not None:
            record_audit_event(
                db, "workout_rate", str(db_rate.id), AuditAction.UPDATE, audit_context
            )
        db.commit()
        db.refresh(db_rate)
        return db_rate
    except DBAPIError as exc:
        db.rollback()
        orig = getattr(exc, "orig", None)
        error_msg = str(orig) if orig is not None else str(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al actualizar la valoración: {error_msg}",
        )


def upsert_workout_rate(
    db: Session,
    workout_rate: WorkoutRateCreate,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> WorkoutRateModel:
    """
    Crea o actualiza la valoración de un usuario sobre un ejercicio (RN-18: 1 voto por usuario y recurso actualizable).
    """
    owner_id = resolve_owner_id(current_user, workout_rate.user_id) if current_user else workout_rate.user_id

    existing_rate = db.query(WorkoutRateModel).filter(
        WorkoutRateModel.id_workout == workout_rate.id_workout,
        WorkoutRateModel.user_id == owner_id,
    ).first()

    if existing_rate is not None:
        existing_rate.rate = workout_rate.rate
        if audit_context is not None:
            record_audit_event(
                db, "workout_rate", str(existing_rate.id), AuditAction.UPDATE, audit_context
            )
        db.commit()
        db.refresh(existing_rate)
        return existing_rate

    return create_workout_rate(
        db=db,
        workout_rate=workout_rate,
        current_user=current_user,
        audit_context=audit_context,
    )


def delete_workout_rate(
    db: Session,
    rate_id: int,
    current_user: AppUserModel | None = None,
    audit_context: AuditContext | None = None,
) -> None:
    """Elimina una valoración por su ID primario."""
    db_rate = get_workout_rate_by_id(db, rate_id, current_user)
    record_id = str(db_rate.id)
    db.delete(db_rate)
    if audit_context is not None:
        record_audit_event(db, "workout_rate", record_id, AuditAction.DELETE, audit_context)
    db.commit()


def get_workout_score(
    db: Session, id_workout: int, current_user: AppUserModel | None = None
) -> dict:
    """
    Obtiene la puntuación media y el total de votos para un ejercicio dado (v_workout_score).
    """
    workout = db.get(WorkoutModel, id_workout)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejercicio con id {id_workout} no encontrado",
        )
    if current_user and not is_admin(current_user) and workout.created_by != current_user.id and not workout.public:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejercicio con id {id_workout} no encontrado",
        )

    result = db.query(
        func.coalesce(func.round(func.avg(WorkoutRateModel.rate), 2), 0.0).label("avg_rate"),
        func.count(WorkoutRateModel.id).label("total_rates"),
    ).filter(WorkoutRateModel.id_workout == id_workout).one()

    return {
        "id_workout": id_workout,
        "avg_rate": float(result.avg_rate),
        "total_rates": int(result.total_rates),
    }
