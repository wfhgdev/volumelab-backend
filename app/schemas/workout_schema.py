from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.workout_model import ExerciseType

WorkoutName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class WorkoutBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    name: WorkoutName
    description: str | None = None
    type: ExerciseType
    is_bodyweight: bool = False
    allow_positive_ballast: bool = True
    allow_negative_ballast: bool = False
    public: bool = False
    state: bool = True

    @model_validator(mode="after")
    def validate_ballast(self) -> Self:
        if self.allow_negative_ballast and not self.is_bodyweight:
            raise ValueError("Negative ballast requires a bodyweight exercise")
        return self


class WorkoutCreate(WorkoutBase):
    created_by: int | None = Field(default=None, gt=0)


class WorkoutUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: WorkoutName | None = None
    description: str | None = None
    type: ExerciseType | None = None
    is_bodyweight: bool | None = None
    allow_positive_ballast: bool | None = None
    allow_negative_ballast: bool | None = None
    public: bool | None = None
    state: bool | None = None
    created_by: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        for field_name in self.model_fields_set - {"description"}:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class WorkoutResponse(WorkoutBase):
    id: int
    created_by: int | None
