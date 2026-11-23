from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


MuscleGroupName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]


class MuscleGroupBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    name: MuscleGroupName
    description: str | None = None


class MuscleGroupCreate(MuscleGroupBase):
    created_by: int = Field(gt=0)


class MuscleGroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: MuscleGroupName | None = None
    description: str | None = None
    created_by: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        for field_name in self.model_fields_set - {"description"}:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class MuscleGroupResponse(MuscleGroupBase):
    id: int
    created_by: int | None
