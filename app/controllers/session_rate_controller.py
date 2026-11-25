from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import ensure_owner_or_admin, is_admin, resolve_owner_id
from app.models.app_user_model import AppUserModel
from app.models.session_rate_model import SessionRateModel
from app.models.workout_session_model import WorkoutSessionModel
from app.schemas.session_rate_schema import (
    SessionRateCreate,
    SessionRateUpdate,
)


def create_session_rate(
    db: Session, session_rate: SessionRateCreate, current_user: AppUserModel
) -> SessionRateModel:
    """
    Crea una nueva valoración para una sesión de entrenamiento pública.

    Reglas aplicadas:
    - RN-18: Comprueba unicidad de voto por usuario y sesión (uq_session_rate_user).
    - Valida trigger trg_session_rate_check_public (la sesión debe ser pública).
    """
    owner_id = resolve_owner_id(current_user, session_rate.user_id)

    existing_rate = db.query(SessionRateModel).filter(
        SessionRateModel.id_workout_session == session_rate.id_workout_session,
        SessionRateModel.user_id == owner_id,
    ).first()

    if existing_rate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El usuario {owner_id} ya ha valorado la sesión {session_rate.id_workout_session}. Utilice el endpoint de actualización para modificar su puntuación.",
        )

    db_session_rate = SessionRateModel(
        id_workout_session=session_rate.id_workout_session,
        user_id=owner_id,
        rate=session_rate.rate,
    )

    try:
        db.add(db_session_rate)
        db.commit()
        db.refresh(db_session_rate)
        return db_session_rate
    except IntegrityError as exc:
        db.rollback()
        orig = getattr(exc, "orig", None)
        error_msg = str(orig) if orig is not None else str(exc)
        lowered = error_msg.lower()
        if "uq_session_rate_user" in lowered or "unique" in lowered:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario ya ha valorado esta sesión de entrenamiento.",
            )
        if "fk_session_rate_session" in lowered or "workout_session" in lowered:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La sesión de entrenamiento con id {session_rate.id_workout_session} no existe.",
            )
        if "fk_session_rate_user" in lowered or "app_user" in lowered:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El usuario con id {owner_id} no existe.",
            )
        if "chk_session_rate" in lowered or "check" in lowered:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La puntuación debe estar comprendida entre 1 y 5.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error de integridad al guardar la valoración de la sesión.",
        )
    except DBAPIError as exc:
        db.rollback()
        orig = getattr(exc, "orig", None)
        error_msg = str(orig) if orig is not None else str(exc)
        if "no es pública" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La sesión {session_rate.id_workout_session} no es pública y no se puede valorar.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error en base de datos: {error_msg}",
        )


def get_session_rates(
    db: Session,
    current_user: AppUserModel,
    skip: int = 0,
    limit: int = 100,
    id_workout_session: Optional[int] = None,
    user_id: Optional[int] = None,
) -> list[SessionRateModel]:
    """Obtiene una lista paginada de valoraciones de sesiones con filtros opcionales."""
    query = db.query(SessionRateModel)

    if not is_admin(current_user):
        query = query.filter(SessionRateModel.user_id == current_user.id)
    elif user_id is not None:
        query = query.filter(SessionRateModel.user_id == user_id)

    if id_workout_session is not None:
        query = query.filter(SessionRateModel.id_workout_session == id_workout_session)

    return query.order_by(SessionRateModel.id.desc()).offset(skip).limit(limit).all()


def get_session_rate_by_id(
    db: Session, rate_id: int, current_user: AppUserModel
) -> SessionRateModel:
    """Obtiene una valoración de sesión por su ID primario."""
    db_rate = db.query(SessionRateModel).filter(SessionRateModel.id == rate_id).first()
    if db_rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valoración con id {rate_id} no encontrada.",
        )
    ensure_owner_or_admin(current_user, db_rate.user_id, is_private=True)
    return db_rate


def get_session_rate_by_session_and_user(
    db: Session, id_workout_session: int, user_id: int, current_user: AppUserModel
) -> SessionRateModel:
    """Obtiene la valoración que un usuario específico hizo a una sesión de entrenamiento."""
    if not is_admin(current_user) and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario {user_id} no ha valorado la sesión {id_workout_session}.",
        )

    db_rate = db.query(SessionRateModel).filter(
        SessionRateModel.id_workout_session == id_workout_session,
        SessionRateModel.user_id == user_id,
    ).first()

    if db_rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario {user_id} no ha valorado la sesión {id_workout_session}.",
        )
    return db_rate


def update_session_rate(
    db: Session,
    rate_id: int,
    session_rate_update: SessionRateUpdate,
    current_user: AppUserModel,
) -> SessionRateModel:
    """
    Actualiza la puntuación de una valoración de sesión existente.
    """
    db_rate = get_session_rate_by_id(db, rate_id, current_user)
    db_rate.rate = session_rate_update.rate
    try:
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


def upsert_session_rate(
    db: Session, session_rate: SessionRateCreate, current_user: AppUserModel
) -> SessionRateModel:
    """
    Crea o actualiza la valoración de un usuario sobre una sesión (RN-18).
    """
    owner_id = resolve_owner_id(current_user, session_rate.user_id)

    existing_rate = db.query(SessionRateModel).filter(
        SessionRateModel.id_workout_session == session_rate.id_workout_session,
        SessionRateModel.user_id == owner_id,
    ).first()

    if existing_rate is not None:
        existing_rate.rate = session_rate.rate
        db.commit()
        db.refresh(existing_rate)
        return existing_rate

    return create_session_rate(db=db, session_rate=session_rate, current_user=current_user)


def delete_session_rate(
    db: Session, rate_id: int, current_user: AppUserModel
) -> None:
    """Elimina una valoración de sesión por su ID primario."""
    db_rate = get_session_rate_by_id(db, rate_id, current_user)
    db.delete(db_rate)
    db.commit()


def get_session_score(
    db: Session, id_workout_session: int, current_user: AppUserModel
) -> dict:
    """
    Obtiene la puntuación media y el total de votos para una sesión dada (v_session_score).
    """
    session = db.get(WorkoutSessionModel, id_workout_session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesión con id {id_workout_session} no encontrada",
        )
    if not is_admin(current_user) and session.user_id != current_user.id and not session.public:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesión con id {id_workout_session} no encontrada",
        )

    result = db.query(
        func.coalesce(func.round(func.avg(SessionRateModel.rate), 2), 0.0).label("avg_rate"),
        func.count(SessionRateModel.id).label("total_rates"),
    ).filter(SessionRateModel.id_workout_session == id_workout_session).one()

    return {
        "id_workout_session": id_workout_session,
        "avg_rate": float(result.avg_rate),
        "total_rates": int(result.total_rates),
    }
