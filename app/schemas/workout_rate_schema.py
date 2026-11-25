from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class WorkoutRateBase(BaseModel):
    """Campos base de valoración."""
    id_workout: int = Field(..., gt=0, description="ID del ejercicio público a valorar")
    rate: int = Field(..., ge=1, le=5, description="Puntuación otorgada al ejercicio (entero entre 1 y 5)")


class WorkoutRateCreate(WorkoutRateBase):
    """Esquema para creación de una valoración de ejercicio."""
    user_id: int | None = Field(None, gt=0, description="ID del usuario que realiza la valoración")


class WorkoutRateUpdate(BaseModel):
    """Esquema para actualización de la puntuación."""
    rate: int = Field(..., ge=1, le=5, description="Nueva puntuación (entero entre 1 y 5)")


class WorkoutRateResponse(BaseModel):
    """Esquema de respuesta para una valoración."""
    id: int
    id_workout: int
    user_id: int
    rate: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkoutScoreResponse(BaseModel):
    """Esquema de respuesta para la puntuación agregada de un ejercicio (v_workout_score)."""
    id_workout: int
    avg_rate: float = Field(..., description="Puntuación media del ejercicio")
    total_rates: int = Field(..., description="Total de valoraciones recibidas")

    model_config = ConfigDict(from_attributes=True)
