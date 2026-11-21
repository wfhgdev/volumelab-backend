from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database_connection import get_db
from app.controllers import session_rate_controller
from app.schemas.session_rate_schema import (
    SessionRateCreate,
    SessionRateResponse,
    SessionRateUpdate,
    SessionScoreResponse,
)

router = APIRouter(prefix="/session-rates", tags=["Session Rates"])


@router.post(
    "/",
    response_model=SessionRateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear valoración de sesión",
    description="Registra la valoración de una sesión de entrenamiento pública (1 a 5). Falla si la sesión no es pública o si el usuario ya la valoró.",
)
def create_new_session_rate(
    session_rate: SessionRateCreate,
    db: Session = Depends(get_db),
):
    return session_rate_controller.create_session_rate(db=db, session_rate=session_rate)


@router.post(
    "/upsert",
    response_model=SessionRateResponse,
    status_code=status.HTTP_200_OK,
    summary="Crear o actualizar valoración de sesión",
    description="Crea la valoración si no existe o actualiza la puntuación existente según la regla RN-18.",
)
def upsert_session_rate(
    session_rate: SessionRateCreate,
    db: Session = Depends(get_db),
):
    return session_rate_controller.upsert_session_rate(db=db, session_rate=session_rate)


@router.get(
    "/",
    response_model=list[SessionRateResponse],
    summary="Listar valoraciones de sesiones",
    description="Recupera la lista de valoraciones con paginación y filtros opcionales por id_workout_session y user_id.",
)
def list_session_rates(
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros a recuperar"),
    id_workout_session: Optional[int] = Query(None, description="Filtrar por ID de sesión de entrenamiento"),
    user_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    db: Session = Depends(get_db),
):
    return session_rate_controller.get_session_rates(
        db=db,
        skip=skip,
        limit=limit,
        id_workout_session=id_workout_session,
        user_id=user_id,
    )


@router.get(
    "/session/{id_workout_session}/score",
    response_model=SessionScoreResponse,
    summary="Obtener puntuación media de la sesión",
    description="Calcula la puntuación media y el número total de valoraciones para una sesión (equivalente a v_session_score).",
)
def get_session_score(
    id_workout_session: int,
    db: Session = Depends(get_db),
):
    return session_rate_controller.get_session_score(db=db, id_workout_session=id_workout_session)


@router.get(
    "/session/{id_workout_session}/user/{user_id}",
    response_model=SessionRateResponse,
    summary="Consultar valoración de un usuario sobre una sesión",
    description="Permite conocer si un usuario específico ya valoró una sesión determinada.",
)
def get_user_rate_for_session(
    id_workout_session: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    return session_rate_controller.get_session_rate_by_session_and_user(
        db=db,
        id_workout_session=id_workout_session,
        user_id=user_id,
    )


@router.get(
    "/{rate_id}",
    response_model=SessionRateResponse,
    summary="Obtener valoración de sesión por ID",
    description="Recupera una valoración específica por su clave primaria.",
)
def get_session_rate_by_id(
    rate_id: int,
    db: Session = Depends(get_db),
):
    return session_rate_controller.get_session_rate_by_id(db=db, rate_id=rate_id)


@router.put(
    "/{rate_id}",
    response_model=SessionRateResponse,
    summary="Actualizar valoración de sesión existente",
    description="Modifica la puntuación (1 a 5) de una valoración ya registrada.",
)
def update_session_rate(
    rate_id: int,
    session_rate_update: SessionRateUpdate,
    db: Session = Depends(get_db),
):
    return session_rate_controller.update_session_rate(
        db=db,
        rate_id=rate_id,
        session_rate_update=session_rate_update,
    )


@router.delete(
    "/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar valoración de sesión",
    description="Elimina una valoración por su ID.",
)
def delete_session_rate(
    rate_id: int,
    db: Session = Depends(get_db),
):
    session_rate_controller.delete_session_rate(db=db, rate_id=rate_id)
    return None
