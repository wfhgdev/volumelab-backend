from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database_connection import get_db
from app.schemas.training_week_schema import (
    TrainingWeekCreate,
    TrainingWeekUpdate,
    TrainingWeekResponse
)
from app.controllers import training_week_controller


router = APIRouter(prefix="/training-weeks", tags=["Training Weeks"])


@router.post("/", response_model=TrainingWeekResponse, status_code=status.HTTP_201_CREATED)
def create_new_training_week(
    training_week: TrainingWeekCreate,
    db: Session = Depends(get_db)
):
    """Crea una nueva semana de entrenamiento vinculada a un mesociclo."""
    return training_week_controller.create_training_week(db=db, training_week=training_week)


@router.get("/", response_model=List[TrainingWeekResponse], status_code=status.HTTP_200_OK)
def list_training_weeks(
    mesocycle_id: Optional[int] = Query(None, description="Filtrar semanas por ID de mesociclo"),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Máximo de registros a retornar"),
    db: Session = Depends(get_db)
):
    """Obtiene el listado de semanas de entrenamiento con filtros opcionales."""
    return training_week_controller.get_training_weeks(
        db=db,
        mesocycle_id=mesocycle_id,
        skip=skip,
        limit=limit
    )


@router.get("/{training_week_id}", response_model=TrainingWeekResponse, status_code=status.HTTP_200_OK)
def get_training_week(
    training_week_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene una semana de entrenamiento por su ID."""
    return training_week_controller.get_training_week_by_id(db=db, training_week_id=training_week_id)


@router.put("/{training_week_id}", response_model=TrainingWeekResponse, status_code=status.HTTP_200_OK)
def update_training_week(
    training_week_id: int,
    training_week_update: TrainingWeekUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza los datos de una semana de entrenamiento existente."""
    return training_week_controller.update_training_week(
        db=db,
        training_week_id=training_week_id,
        training_week_update=training_week_update
    )


@router.delete("/{training_week_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training_week(
    training_week_id: int,
    db: Session = Depends(get_db)
):
    """Elimina una semana de entrenamiento por su ID."""
    training_week_controller.delete_training_week(db=db, training_week_id=training_week_id)
    return None
