from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MesocycleStatusEnum(str, Enum):
    PLANIFICADO = "PLANIFICADO"
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"


class MesocycleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Nombre descriptivo del mesociclo")
    start_date: date = Field(..., description="Fecha de inicio del mesociclo")
    end_date: date = Field(..., description="Fecha de fin del mesociclo")
    status: MesocycleStatusEnum = Field(
        default=MesocycleStatusEnum.PLANIFICADO,
        description="Estado del mesociclo (PLANIFICADO, ACTIVO, FINALIZADO)"
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "MesocycleBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date debe ser mayor o igual a start_date")
        return self


class MesocycleCreate(MesocycleBase):
    user_id: int = Field(..., gt=0, description="ID del usuario al que pertenece el mesociclo")


class MesocycleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Nombre descriptivo del mesociclo")
    start_date: Optional[date] = Field(None, description="Fecha de inicio del mesociclo")
    end_date: Optional[date] = Field(None, description="Fecha de fin del mesociclo")
    status: Optional[MesocycleStatusEnum] = Field(None, description="Estado del mesociclo")

    @model_validator(mode="after")
    def validate_dates(self) -> "MesocycleUpdate":
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date debe ser mayor o igual a start_date")
        return self


class MesocycleResponse(BaseModel):
    id: int
    user_id: int
    name: str
    start_date: date
    end_date: date
    status: MesocycleStatusEnum

    model_config = ConfigDict(from_attributes=True)
