from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrainingWeekBase(BaseModel):
    mesocycle_id: int = Field(..., gt=0, description="ID del mesociclo al que pertenece la semana")
    week_order: int = Field(..., ge=1, description="Número de orden correlativo de la semana dentro del mesociclo (>= 1)")
    start_date: date = Field(..., description="Fecha de inicio de la semana de entrenamiento")
    end_date: date = Field(..., description="Fecha de fin de la semana de entrenamiento")

    @model_validator(mode="after")
    def validate_dates(self) -> "TrainingWeekBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date debe ser mayor o igual a start_date")
        return self


class TrainingWeekCreate(TrainingWeekBase):
    pass


class TrainingWeekUpdate(BaseModel):
    mesocycle_id: Optional[int] = Field(None, gt=0, description="ID del mesociclo")
    week_order: Optional[int] = Field(None, ge=1, description="Número de orden de la semana (>= 1)")
    start_date: Optional[date] = Field(None, description="Fecha de inicio")
    end_date: Optional[date] = Field(None, description="Fecha de fin")

    @model_validator(mode="after")
    def validate_dates(self) -> "TrainingWeekUpdate":
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date debe ser mayor o igual a start_date")
        return self


class TrainingWeekResponse(TrainingWeekBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
