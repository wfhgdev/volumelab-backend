from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models.workout_rate_model import WorkoutRateModel
from app.schemas.workout_rate_schema import (
    WorkoutRateCreate,
    WorkoutRateUpdate,
)


def create_workout_rate(db: Session, workout_rate: WorkoutRateCreate) -> WorkoutRateModel:
    """
    Crea una nueva valoración para un ejercicio público y activo.

    Reglas aplicadas:
    - RN-18: Comprueba unicidad de voto por usuario y ejercicio (uq_workout_rate_user).
    - Valida trigger trg_workout_rate_check_public (el ejercicio debe ser público y estar activo).
    """
    # Verificar si el usuario ya valoró previamente este ejercicio
    existing_rate = db.execute(
        select(WorkoutRateModel).where(
            WorkoutRateModel.id_workout == workout_rate.id_workout,
            WorkoutRateModel.user_id == workout_rate.user_id,
        )
    ).scalar_one_or_none()

    if existing_rate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El usuario {workout_rate.user_id} ya ha valorado el ejercicio {workout_rate.id_workout}. Utilice el endpoint de actualización para modificar su puntuación.",
        )

    db_workout_rate = WorkoutRateModel(
        id_workout=workout_rate.id_workout,
        user_id=workout_rate.user_id,
        rate=workout_rate.rate,
    )

    try:
        db.add(db_workout_rate)
        db.commit()
        db.refresh(db_workout_rate)
        return db_workout_rate
    except IntegrityError as exc:
        db.rollback()
        error_msg = str(exc.orig) if exc.orig else str(exc)
        if "uq_workout_rate_user" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya ha valorado este ejercicio.",
            )
        if "fk_workout_rate_workout" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El ejercicio con id {workout_rate.id_workout} no existe.",
            )
        if "fk_workout_rate_user" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El usuario con id {workout_rate.user_id} no existe.",
            )
        if "chk_workout_rate" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La puntuación debe estar comprendida entre 1 y 5.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad al guardar la valoración.",
        )
    except DBAPIError as exc:
        db.rollback()
        error_msg = str(exc.orig) if exc.orig else str(exc)
        # Captura de la excepción del trigger fn_workout_rate_check_public
        if "debe ser público y estar activo" in error_msg:
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
    skip: int = 0,
    limit: int = 100,
    id_workout: Optional[int] = None,
    user_id: Optional[int] = None,
) -> list[WorkoutRateModel]:
    """Obtiene una lista paginada de valoraciones con filtros opcionales."""
    query = select(WorkoutRateModel)

    if id_workout is not None:
        query = query.where(WorkoutRateModel.id_workout == id_workout)
    if user_id is not None:
        query = query.where(WorkoutRateModel.user_id == user_id)

    query = query.order_by(WorkoutRateModel.id.desc()).offset(skip).limit(limit)
    return list(db.execute(query).scalars().all())


def get_workout_rate_by_id(db: Session, rate_id: int) -> WorkoutRateModel:
    """Obtiene una valoración por su ID primario."""
    db_rate = db.get(WorkoutRateModel, rate_id)
    if not db_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valoración con id {rate_id} no encontrada.",
        )
    return db_rate


def get_workout_rate_by_workout_and_user(
    db: Session, id_workout: int, user_id: int
) -> WorkoutRateModel:
    """Obtiene la valoración que un usuario específico hizo a un ejercicio."""
    db_rate = db.execute(
        select(WorkoutRateModel).where(
            WorkoutRateModel.id_workout == id_workout,
            WorkoutRateModel.user_id == user_id,
        )
    ).scalar_one_or_none()

    if not db_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario {user_id} no ha valorado el ejercicio {id_workout}.",
        )
    return db_rate


def update_workout_rate(
    db: Session, rate_id: int, workout_rate_update: WorkoutRateUpdate
) -> WorkoutRateModel:
    """
    Actualiza la puntuación de una valoración existente.
    """
    db_rate = get_workout_rate_by_id(db, rate_id)

    db_rate.rate = workout_rate_update.rate
    try:
        db.commit()
        db.refresh(db_rate)
        return db_rate
    except DBAPIError as exc:
        db.rollback()
        error_msg = str(exc.orig) if exc.orig else str(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al actualizar la valoración: {error_msg}",
        )


def upsert_workout_rate(
    db: Session, workout_rate: WorkoutRateCreate
) -> WorkoutRateModel:
    """
    Crea o actualiza la valoración de un usuario sobre un ejercicio (RN-18: 1 voto por usuario y recurso actualizable).
    """
    existing_rate = db.execute(
        select(WorkoutRateModel).where(
            WorkoutRateModel.id_workout == workout_rate.id_workout,
            WorkoutRateModel.user_id == workout_rate.user_id,
        )
    ).scalar_one_or_none()

    if existing_rate:
        existing_rate.rate = workout_rate.rate
        db.commit()
        db.refresh(existing_rate)
        return existing_rate

    return create_workout_rate(db=db, workout_rate=workout_rate)


def delete_workout_rate(db: Session, rate_id: int) -> None:
    """Elimina una valoración por su ID primario."""
    db_rate = get_workout_rate_by_id(db, rate_id)
    db.delete(db_rate)
    db.commit()


def get_workout_score(db: Session, id_workout: int) -> dict:
    """
    Obtiene la puntuación media y el total de votos para un ejercicio dado (v_workout_score).
    """
    result = db.execute(
        select(
            func.coalesce(func.round(func.avg(WorkoutRateModel.rate), 2), 0.0).label("avg_rate"),
            func.count(WorkoutRateModel.id).label("total_rates"),
        ).where(WorkoutRateModel.id_workout == id_workout)
    ).one()

    return {
        "id_workout": id_workout,
        "avg_rate": float(result.avg_rate),
        "total_rates": int(result.total_rates),
    }
