from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.app_user_schema import AppUserCreate, AppUserResponse, AppUserUpdate


def test_app_user_create_normalizes_email():
    payload = AppUserCreate(name="Ana", email="  ANA@Example.COM ", password="Password123!")
    assert payload.email == "ana@example.com"


def test_app_user_create_accepts_prefiero_no_decir_gender():
    payload = AppUserCreate(
        name="Ana",
        email="ana@example.com",
        password="Password123!",
        gender="PREFIERO NO DECIR",
    )
    assert payload.gender == "PREFIERO NO DECIR"


def test_app_user_rejects_invalid_email():
    with pytest.raises(ValidationError):
        AppUserCreate(name="Ana", email="invalid", password="Password123!")


def test_app_user_rejects_future_birth_date():
    future = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        AppUserCreate(name="Ana", email="ana@example.com", password="Password123!", birth_date=future)


def test_app_user_create_validates_password_length():
    with pytest.raises(ValidationError):
        AppUserCreate(name="Ana", email="ana@example.com", password="short")
    with pytest.raises(ValidationError):
        AppUserCreate(name="Ana", email="ana@example.com", password="a" * 129)


@pytest.mark.parametrize("height", [49, 301, 170.5])
def test_app_user_rejects_invalid_height_on_update(height):
    with pytest.raises(ValidationError):
        AppUserUpdate(height_cm=height)


@pytest.mark.parametrize("field", ["name", "email", "password", "role", "status"])
def test_app_user_update_rejects_explicit_null_on_non_nullable_fields(field):
    with pytest.raises(ValidationError):
        AppUserUpdate(**{field: None})


def test_app_user_response_does_not_expose_password_or_hash():
    response = AppUserResponse(
        id=1,
        name="Ana",
        lastname="Lopez",
        email="ana@example.com",
        birth_date=date(1990, 1, 1),
        gender="MUJER",
        height_cm=165,
        role="CLIENTE",
        status="ACTIVO",
        created_at=datetime(2026, 11, 20, 10, 0, 0),
    )
    dumped = response.model_dump()
    assert "password_hash" not in dumped
    assert "password" not in dumped
