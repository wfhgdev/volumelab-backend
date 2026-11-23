from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.audit_model import AuditAction


_NON_NULLABLE_UPDATE_FIELDS = ("entity", "record_id", "action")


def _reject_bool(value: object, field_name: str) -> object:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} debe ser un entero válido")
    return value


def _clean_non_empty_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} no puede estar vacío")
    return cleaned


def _clean_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} no puede estar vacío")
    return cleaned


class AuditBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int | None = Field(default=None, gt=0)
    entity: str = Field(min_length=1, max_length=60)
    record_id: str = Field(min_length=1, max_length=60)
    action: AuditAction
    endpoint: str | None = Field(default=None, max_length=255)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id_not_bool(cls, value: object) -> object:
        return _reject_bool(value, "user_id")

    @field_validator("entity")
    @classmethod
    def validate_entity(cls, value: str) -> str:
        return _clean_non_empty_text(value, "entity")

    @field_validator("record_id")
    @classmethod
    def validate_record_id(cls, value: str) -> str:
        return _clean_non_empty_text(value, "record_id")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str | None) -> str | None:
        return _clean_optional_text(value, "endpoint")


class AuditCreate(AuditBase):
    pass


class AuditUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int | None = Field(default=None, gt=0)
    entity: str | None = Field(default=None, min_length=1, max_length=60)
    record_id: str | None = Field(default=None, min_length=1, max_length=60)
    action: AuditAction | None = None
    endpoint: str | None = Field(default=None, max_length=255)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id_not_bool(cls, value: object) -> object:
        return _reject_bool(value, "user_id")

    @field_validator("entity")
    @classmethod
    def validate_entity(cls, value: str | None) -> str | None:
        return _clean_optional_text(value, "entity")

    @field_validator("record_id")
    @classmethod
    def validate_record_id(cls, value: str | None) -> str | None:
        return _clean_optional_text(value, "record_id")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str | None) -> str | None:
        return _clean_optional_text(value, "endpoint")

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "AuditUpdate":
        for field_name in _NON_NULLABLE_UPDATE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} no puede ser nulo")
        return self


class AuditResponse(AuditBase):
    id: int
    created_at: datetime
