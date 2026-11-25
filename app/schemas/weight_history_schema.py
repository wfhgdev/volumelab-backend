from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_NON_NULLABLE_UPDATE_FIELDS = ("user_id", "weight_kg")


class WeightHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(gt=0)
    weight_kg: Decimal = Field(gt=0, max_digits=6, decimal_places=2)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("user_id debe ser un entero válido")
        return value


class WeightHistoryCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int | None = Field(default=None, gt=0)
    weight_kg: Decimal = Field(gt=0, max_digits=6, decimal_places=2)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("user_id debe ser un entero válido")
        return value


class WeightHistoryUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int | None = Field(default=None, gt=0)
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=2)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("user_id debe ser un entero válido")
        return value

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "WeightHistoryUpdate":
        for field_name in _NON_NULLABLE_UPDATE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} no puede ser nulo")
        return self


class WeightHistoryResponse(WeightHistoryBase):
    id: int
    created_at: datetime
