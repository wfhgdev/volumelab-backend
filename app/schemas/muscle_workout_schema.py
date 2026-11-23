from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.muscle_workout_model import MuscleRole


ROLE_WEIGHTS = {
    MuscleRole.PRIMARY: 100,
    MuscleRole.SECONDARY: 50,
    MuscleRole.TERTIARY: 10,
}


def resolve_weighing(role: MuscleRole, weighing: int | None = None) -> int:
    expected = ROLE_WEIGHTS[role]
    if weighing is not None and weighing != expected:
        raise ValueError("The weighing must match the muscle role")
    return expected


class MuscleWorkoutCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workout_id: int = Field(gt=0)
    muscle_group_id: int = Field(gt=0)
    muscle_role: MuscleRole
    weighing: int | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def validate_weighing(self) -> Self:
        if "weighing" in self.model_fields_set and self.weighing is None:
            raise ValueError("weighing cannot be null")
        self.weighing = resolve_weighing(self.muscle_role, self.weighing)
        return self


class MuscleWorkoutUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muscle_role: MuscleRole | None = None
    weighing: int | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.weighing is not None:
            if self.weighing not in ROLE_WEIGHTS.values():
                raise ValueError("weighing must be 100, 50 or 10")
            if self.muscle_role is not None:
                resolve_weighing(self.muscle_role, self.weighing)
        return self


class MuscleWorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workout_id: int
    muscle_group_id: int
    muscle_role: MuscleRole
    weighing: int
