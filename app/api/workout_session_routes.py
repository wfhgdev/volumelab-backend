from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status as http_status
from sqlalchemy.orm import Session
from app.core.database_connection import get_db
from app.schemas.workout_session_schema import (
    SessionStatusEnum,
    WorkoutSessionCreate,
    WorkoutSessionResponse,
    WorkoutSessionUpdate,
)
from app.controllers import workout_session_controller


router = APIRouter(prefix="/workout-sessions", tags=["Workout Sessions"])


@router.post("/", response_model=WorkoutSessionResponse, status_code=http_status.HTTP_201_CREATED)
def create_new_workout_session(
    workout_session: WorkoutSessionCreate,
    db: Session = Depends(get_db),
):
    return workout_session_controller.create_workout_session(db=db, workout_session=workout_session)


@router.get("/", response_model=List[WorkoutSessionResponse], status_code=http_status.HTTP_200_OK)
def list_workout_sessions(
    user_id: Optional[int] = Query(None, description="Filtrar sesiones por ID de usuario"),
    week_id: Optional[int] = Query(None, description="Filtrar sesiones por ID de semana"),
    status: Optional[SessionStatusEnum] = Query(None, description="Filtrar sesiones por estado"),
    public: Optional[bool] = Query(None, description="Filtrar sesiones por visibilidad"),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Máximo de registros a retornar"),
    db: Session = Depends(get_db),
):
    return workout_session_controller.get_workout_sessions(
        db=db,
        user_id=user_id,
        week_id=week_id,
        status=status,
        public=public,
        skip=skip,
        limit=limit,
    )


@router.get("/{workout_session_id}", response_model=WorkoutSessionResponse, status_code=http_status.HTTP_200_OK)
def get_workout_session(
    workout_session_id: int,
    db: Session = Depends(get_db),
):
    return workout_session_controller.get_workout_session_by_id(
        db=db, workout_session_id=workout_session_id
    )


@router.put("/{workout_session_id}", response_model=WorkoutSessionResponse, status_code=http_status.HTTP_200_OK)
def update_workout_session(
    workout_session_id: int,
    workout_session_update: WorkoutSessionUpdate,
    db: Session = Depends(get_db),
):
    return workout_session_controller.update_workout_session(
        db=db,
        workout_session_id=workout_session_id,
        workout_session_update=workout_session_update,
    )


@router.delete("/{workout_session_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_workout_session(
    workout_session_id: int,
    db: Session = Depends(get_db),
):
    workout_session_controller.delete_workout_session(
        db=db, workout_session_id=workout_session_id
    )
    return None
