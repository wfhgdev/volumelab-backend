from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


_NON_NULLABLE_UPDATE_FIELDS = ("user_id", "session_date", "public", "status")


class SessionStatusEnum(str, Enum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class WorkoutSessionBase(BaseModel):
    user_id: int = Field(..., gt=0, description="ID del usuario que realiza la sesión")
    week_id: Optional[int] = Field(None, gt=0, description="ID de la semana de entrenamiento")
    title: Optional[str] = Field(None, max_length=200, description="Título de la sesión")
    session_date: date = Field(..., description="Fecha de la sesión")
    current_bodyweight_kg: Optional[Decimal] = Field(
        None, gt=0, max_digits=6, decimal_places=2, description="Peso corporal introducido desde el frontend"
    )
    observation: Optional[str] = Field(None, description="Observaciones de la sesión")
    closed_at: Optional[datetime] = Field(None, description="Fecha de cierre de la sesión")
    public: bool = Field(False, description="Si la sesión es pública")
    status: SessionStatusEnum = Field(SessionStatusEnum.ABIERTO, description="Estado de la sesión")

    @model_validator(mode="after")
    def validate_status(self) -> "WorkoutSessionBase":
        if self.status == SessionStatusEnum.CERRADO and self.closed_at is None:
            raise ValueError("closed_at is required when status is CERRADO")
        if self.status == SessionStatusEnum.ABIERTO and self.closed_at is not None:
            raise ValueError("closed_at must be null when status is ABIERTO")
        return self


class WorkoutSessionCreate(WorkoutSessionBase):
    pass


class WorkoutSessionUpdate(BaseModel):
    user_id: Optional[int] = Field(None, gt=0, description="ID del usuario")
    week_id: Optional[int] = Field(None, gt=0, description="ID de la semana de entrenamiento")
    title: Optional[str] = Field(None, max_length=200, description="Título de la sesión")
    session_date: Optional[date] = Field(None, description="Fecha de la sesión")
    current_bodyweight_kg: Optional[Decimal] = Field(
        None, gt=0, max_digits=6, decimal_places=2, description="Peso corporal introducido desde el frontend"
    )
    observation: Optional[str] = Field(None, description="Observaciones de la sesión")
    closed_at: Optional[datetime] = Field(None, description="Fecha de cierre de la sesión")
    public: Optional[bool] = Field(None, description="Si la sesión es pública")
    status: Optional[SessionStatusEnum] = Field(None, description="Estado de la sesión")

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "WorkoutSessionUpdate":
        for field_name in _NON_NULLABLE_UPDATE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class WorkoutSessionResponse(BaseModel):
    id: int
    user_id: int
    week_id: Optional[int]
    title: Optional[str]
    session_date: date
    current_bodyweight_kg: Optional[Decimal]
    observation: Optional[str]
    created_at: datetime
    closed_at: Optional[datetime]
    public: bool
    status: SessionStatusEnum

    model_config = ConfigDict(from_attributes=True)
