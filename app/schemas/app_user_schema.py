from datetime import date, datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Gender = Literal["HOMBRE", "MUJER", "PREFIERO NO DECIR"]
Status = Literal["ACTIVO", "BLOQUEADO"]
Role = Literal["ADMIN", "CLIENTE"]

_NON_NULLABLE_UPDATE_FIELDS = ("name", "email", "password_hash", "role", "status")


class AppUserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=150)
    lastname: str | None = Field(default=None, max_length=150)
    email: str = Field(max_length=255)
    birth_date: date | None = None
    gender: Gender | None = None
    height_cm: int | None = Field(default=None, ge=50, le=300)
    role: Role = "CLIENTE"
    status: Status = "ACTIVO"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
            raise ValueError("email no tiene un formato válido")
        return cleaned.lower()

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("birth_date no puede ser posterior a la fecha actual")
        return value


class AppUserCreate(AppUserBase):
    password_hash: str = Field(min_length=1, max_length=255)


class AppUserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = Field(default=None, min_length=1, max_length=150)
    lastname: str | None = Field(default=None, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    password_hash: str | None = Field(default=None, min_length=1, max_length=255)
    birth_date: date | None = None
    gender: Gender | None = None
    height_cm: int | None = Field(default=None, ge=50, le=300)
    role: Role | None = None
    status: Status | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
            raise ValueError("email no tiene un formato válido")
        return cleaned.lower()

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("birth_date no puede ser posterior a la fecha actual")
        return value

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "AppUserUpdate":
        for field_name in _NON_NULLABLE_UPDATE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} no puede ser nulo")
        return self


class AppUserResponse(AppUserBase):
    id: int
    created_at: datetime
