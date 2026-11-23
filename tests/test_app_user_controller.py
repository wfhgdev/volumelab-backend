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
            password_hash="hash",
        ),
    )


def test_create_app_user_persists_and_normalizes_email(db_session):
    email = f"app_user_{uuid4().hex}@Example.com"

    result = create_app_user(
        db_session,
        AppUserCreate(name="Ana", email=email, password_hash="hash"),
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


def test_list_app_users_applies_pagination(db_session):
    first = create_sample_user(db_session)
    second = create_sample_user(db_session)

    result = list_app_users(db_session, 0, 500)

    ids = {user.id for user in result}
    assert first.id in ids
    assert second.id in ids
    assert len(list_app_users(db_session, 0, 1)) == 1


def test_update_app_user_changes_fields(db_session):
    user = create_sample_user(db_session)

    result = update_app_user(
        db_session, user.id, AppUserUpdate(name="Lucia", status="BLOQUEADO")
    )

    assert result.name == "Lucia"
    assert result.status == "BLOQUEADO"
    assert get_app_user(db_session, user.id).name == "Lucia"


def test_update_app_user_rejects_duplicate_email(db_session):
    first = create_sample_user(db_session)
    second = create_sample_user(db_session)

    with pytest.raises(HTTPException) as exc:
        update_app_user(db_session, first.id, AppUserUpdate(email=second.email.upper()))

    assert exc.value.status_code == 409


def test_update_app_user_returns_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        update_app_user(db_session, 2_000_000_000, AppUserUpdate(name="Lucia"))

    assert exc.value.status_code == 404


def test_delete_app_user_removes_and_commits(db_session):
    user = create_sample_user(db_session)

    delete_app_user(db_session, user.id)

    with pytest.raises(HTTPException) as exc:
        get_app_user(db_session, user.id)
    assert exc.value.status_code == 404


def test_delete_app_user_returns_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        delete_app_user(db_session, 2_000_000_000)

    assert exc.value.status_code == 404
