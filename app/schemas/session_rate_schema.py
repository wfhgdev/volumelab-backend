from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SessionRateBase(BaseModel):
    """Campos base de valoración de sesión."""
    id_workout_session: int = Field(..., gt=0, description="ID de la sesión de entrenamiento pública a valorar")
    rate: int = Field(..., ge=1, le=5, description="Puntuación otorgada a la sesión (entero entre 1 y 5)")


class SessionRateCreate(SessionRateBase):
    """Esquema para creación de una valoración de sesión."""
    user_id: int | None = Field(None, gt=0, description="ID del usuario que realiza la valoración")


class SessionRateUpdate(BaseModel):
    """Esquema para actualización de la puntuación."""
    rate: int = Field(..., ge=1, le=5, description="Nueva puntuación (entero entre 1 y 5)")


class SessionRateResponse(BaseModel):
    """Esquema de respuesta para una valoración de sesión."""
    id: int
    id_workout_session: int
    user_id: int
    rate: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionScoreResponse(BaseModel):
    """Esquema de respuesta para la puntuación agregada de una sesión (v_session_score)."""
    id_workout_session: int
    avg_rate: float = Field(..., description="Puntuación media de la sesión")
    total_rates: int = Field(..., description="Total de valoraciones recibidas")

    model_config = ConfigDict(from_attributes=True)
