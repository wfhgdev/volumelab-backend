from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.controllers.app_user_controller import (
    create_app_user,
    delete_app_user,
    get_app_user,
    list_app_users,
    update_app_user,
)
from app.schemas.app_user_schema import AppUserCreate, AppUserUpdate


def create_sample_user(
    db_session,
    email: str | None = None,
    name: str = "Ana",
) -> object:
    return create_app_user(
        db_session,
        AppUserCreate(
            name=name,
            email=email or f"app_user_{uuid4().hex}@example.com",
            password="Password123!",
        ),
    )


def test_create_app_user_persists_and_normalizes_email(db_session):
    email = f"app_user_{uuid4().hex}@Example.com"

    result = create_app_user(
        db_session,
        AppUserCreate(name="Ana", email=email, password="Password123!"),
    )

    assert result.id >= 1
    assert result.email == email.lower()
    assert get_app_user(db_session, result.id).id == result.id


def test_create_app_user_rejects_duplicate_email(db_session):
    email = f"app_user_{uuid4().hex}@example.com"
    create_sample_user(db_session, email=email)

    with pytest.raises(HTTPException) as exc:
        create_sample_user(db_session, email=email.upper())

    assert exc.value.status_code == 409
    assert "email" in exc.value.detail.lower()


def test_get_app_user_returns_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        get_app_user(db_session, 2_000_000_000)

    assert exc.value.status_code == 404


def test_list_app_users_paginates(db_session, admin_user):
    create_sample_user(db_session)
    create_sample_user(db_session)

    results = list_app_users(db_session, skip=0, limit=2, current_user=admin_user)
    assert len(results) <= 2


def test_update_app_user_modifies_fields(db_session, admin_user):
    user = create_sample_user(db_session)
    updated = update_app_user(
        db_session,
        user.id,
        AppUserUpdate(name="Carlos", password="NewPassword123!"),
        current_user=admin_user,
    )
    assert updated.name == "Carlos"


def test_delete_app_user_removes_record(db_session, admin_user):
    user = create_sample_user(db_session)
    delete_app_user(db_session, user.id, current_user=admin_user)

    with pytest.raises(HTTPException) as exc:
        get_app_user(db_session, user.id)
    assert exc.value.status_code == 404
