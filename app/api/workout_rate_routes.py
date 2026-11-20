from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database_connection import get_db
from app.controllers import workout_rate_controller
from app.schemas.workout_rate_schema import (
    WorkoutRateCreate,
    WorkoutRateResponse,
    WorkoutRateUpdate,
    WorkoutScoreResponse,
)

router = APIRouter(prefix="/workout-rates", tags=["Workout Rates"])


@router.post(
    "/",
    response_model=WorkoutRateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear valoración de ejercicio",
    description="Registra la valoración de un ejercicio público y activo (1 a 5). Falla si el ejercicio no es público/activo o si el usuario ya lo valoró.",
)
def create_new_workout_rate(
    workout_rate: WorkoutRateCreate,
    db: Session = Depends(get_db),
):
    return workout_rate_controller.create_workout_rate(db=db, workout_rate=workout_rate)


@router.post(
    "/upsert",
    response_model=WorkoutRateResponse,
    status_code=status.HTTP_200_OK,
    summary="Crear o actualizar valoración",
    description="Crea la valoración si no existe o actualiza la puntuación existente según la regla RN-18.",
)
def upsert_workout_rate(
    workout_rate: WorkoutRateCreate,
    db: Session = Depends(get_db),
):
    return workout_rate_controller.upsert_workout_rate(db=db, workout_rate=workout_rate)


@router.get(
    "/",
    response_model=list[WorkoutRateResponse],
    summary="Listar valoraciones",
    description="Recupera la lista de valoraciones con paginación y filtros opcionales por id_workout y user_id.",
)
def list_workout_rates(
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros a recuperar"),
    id_workout: Optional[int] = Query(None, description="Filtrar por ID de ejercicio"),
    user_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    db: Session = Depends(get_db),
):
    return workout_rate_controller.get_workout_rates(
        db=db,
        skip=skip,
        limit=limit,
        id_workout=id_workout,
        user_id=user_id,
    )


@router.get(
    "/workout/{id_workout}/score",
    response_model=WorkoutScoreResponse,
    summary="Obtener puntuación media del ejercicio",
    description="Calcula la puntuación media y el número total de valoraciones para un ejercicio (equivalente a v_workout_score).",
)
def get_workout_score(
    id_workout: int,
    db: Session = Depends(get_db),
):
    return workout_rate_controller.get_workout_score(db=db, id_workout=id_workout)


@router.get(
    "/workout/{id_workout}/user/{user_id}",
    response_model=WorkoutRateResponse,
    summary="Consultar valoración de un usuario sobre un ejercicio",
    description="Permite conocer si un usuario específico ya valoró un ejercicio determinado.",
)
def get_user_rate_for_workout(
    id_workout: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    return workout_rate_controller.get_workout_rate_by_workout_and_user(
        db=db,
        id_workout=id_workout,
        user_id=user_id,
    )


@router.get(
    "/{rate_id}",
    response_model=WorkoutRateResponse,
    summary="Obtener valoración por ID",
    description="Recupera una valoración específica por su clave primaria.",
)
def get_workout_rate_by_id(
    rate_id: int,
    db: Session = Depends(get_db),
):
    return workout_rate_controller.get_workout_rate_by_id(db=db, rate_id=rate_id)


@router.put(
    "/{rate_id}",
    response_model=WorkoutRateResponse,
    summary="Actualizar valoración existente",
    description="Modifica la puntuación (1 a 5) de una valoración ya registrada.",
)
def update_workout_rate(
    rate_id: int,
    workout_rate_update: WorkoutRateUpdate,
    db: Session = Depends(get_db),
):
    return workout_rate_controller.update_workout_rate(
        db=db,
        rate_id=rate_id,
        workout_rate_update=workout_rate_update,
    )


@router.delete(
    "/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar valoración",
    description="Elimina una valoración por su ID.",
)
def delete_workout_rate(
    rate_id: int,
    db: Session = Depends(get_db),
):
    workout_rate_controller.delete_workout_rate(db=db, rate_id=rate_id)
    return None
