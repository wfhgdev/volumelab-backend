from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.app_user_schema import AppUserBase, Gender


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    lastname: str | None = Field(default=None, max_length=150)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    birth_date: date | None = None
    gender: Gender | None = None
    height_cm: int | None = Field(default=None, ge=50, le=300)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return AppUserBase.validate_email(value)

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date | None) -> date | None:
        return AppUserBase.validate_birth_date(value)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
