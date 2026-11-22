from decimal import Decimal
from enum import Enum as PythonEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_INT_FIELDS = (
    "session_id",
    "exercise_id",
    "exercise_order",
    "set_number",
    "reps",
    "duration_second",
    "rir",
)

_NON_NULLABLE_UPDATE_FIELDS = (
    "session_id",
    "exercise_id",
    "exercise_order",
    "set_number",
    "completed",
)


class WorkoutSetExerciseType(str, PythonEnum):
    DINAMICO = "DINAMICO"
    ISOMETRICO = "ISOMETRICO"


class WorkoutSetSessionStatus(str, PythonEnum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class WorkoutSetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int = Field(gt=0)
    exercise_id: int = Field(gt=0)
    exercise_order: int = Field(gt=0)
    set_number: int = Field(gt=0)
    added_weight_kg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    reps: int | None = Field(default=None, ge=1)
    duration_second: int | None = Field(default=None, ge=1)
    rir: int | None = Field(default=None, ge=0, le=10)
    note: str | None = None
    completed: bool = False

    @field_validator(*_INT_FIELDS, mode="before")
    @classmethod
    def validate_int_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("debe ser un entero válido")
        return value

    @model_validator(mode="after")
    def validate_set_shape(self) -> "WorkoutSetBase":
        if (self.reps is None) == (self.duration_second is None):
            raise ValueError("debe indicar exactamente uno de reps o duration_second")
        if self.reps is not None and self.rir is None:
            raise ValueError("rir es obligatorio en series dinámicas para calcular el 1RM")
        return self


class WorkoutSetCreate(WorkoutSetBase):
    pass


class WorkoutSetUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int | None = Field(default=None, gt=0)
    exercise_id: int | None = Field(default=None, gt=0)
    exercise_order: int | None = Field(default=None, gt=0)
    set_number: int | None = Field(default=None, gt=0)
    added_weight_kg: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    reps: int | None = Field(default=None, ge=1)
    duration_second: int | None = Field(default=None, ge=1)
    rir: int | None = Field(default=None, ge=0, le=10)
    note: str | None = None
    completed: bool | None = None

    @field_validator(*_INT_FIELDS, mode="before")
    @classmethod
    def validate_int_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("debe ser un entero válido")
        return value

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "WorkoutSetUpdate":
        for field_name in _NON_NULLABLE_UPDATE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} no puede ser nulo")
        if "reps" in self.model_fields_set and "duration_second" in self.model_fields_set:
            if (self.reps is None) == (self.duration_second is None):
                raise ValueError("debe indicar exactamente uno de reps o duration_second")
        return self


class WorkoutSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    exercise_id: int
    exercise_order: int
    set_number: int
    added_weight_kg: Decimal | None
    reps: int | None
    duration_second: int | None
    rir: int | None
    note: str | None
    effective_weight_kg: Decimal | None
    one_rm_kg: Decimal | None
    one_rm_percentage: Decimal | None
    volume_load: Decimal | None
    completed: bool
