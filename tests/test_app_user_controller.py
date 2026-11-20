from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.controllers.app_user_controller import (
    create_app_user,
    delete_app_user,
    get_app_user,
    list_app_users,
    update_app_user,
)
from app.models.app_user_model import AppUserModel
from app.schemas.app_user_schema import AppUserCreate, AppUserUpdate


def make_user(user_id: int = 1, email: str = "ana@example.com") -> AppUserModel:
    return AppUserModel(
        id=user_id,
        name="Ana",
        lastname="Lopez",
        email=email,
        password_hash="hash",
        birth_date=date(1990, 1, 1),
        gender="PREFIERO NO DECIR",
        height_cm=170,
        role="CLIENTE",
        status="ACTIVO",
    )


def test_create_app_user_commits():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    payload = AppUserCreate(
        name="Ana",
        email="Ana@Example.com",
        password_hash="hash",
    )

    result = create_app_user(db, payload)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert result.email == "ana@example.com"


def test_create_app_user_rejects_duplicate_email():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = make_user()
    payload = AppUserCreate(name="Ana", email="ana@example.com", password_hash="hash")

    with pytest.raises(HTTPException) as exc:
        create_app_user(db, payload)

    assert exc.value.status_code == 409


def test_get_app_user_returns_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_app_user(db, 99)

    assert exc.value.status_code == 404


def test_list_app_users_applies_pagination():
    db = MagicMock()
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = [make_user()]

    result = list_app_users(db, 5, 10)

    assert len(result) == 1
    assert result[0].id == 1
    db.query.return_value.offset.assert_called_once_with(5)
    db.query.return_value.offset.return_value.limit.assert_called_once_with(10)


def test_update_app_user_changes_fields():
    db = MagicMock()
    user = make_user()
    db.query.return_value.filter.return_value.first.return_value = user

    result = update_app_user(db, 1, AppUserUpdate(name="Lucia", status="BLOQUEADO"))

    assert result.name == "Lucia"
    assert result.status == "BLOQUEADO"
    db.commit.assert_called_once()


def test_update_app_user_rejects_duplicate_email():
    db = MagicMock()
    user = make_user(user_id=1, email="ana@example.com")
    other = make_user(user_id=2, email="otro@example.com")
    db.query.return_value.filter.return_value.first.side_effect = [user, other]

    with pytest.raises(HTTPException) as exc:
        update_app_user(db, 1, AppUserUpdate(email="otro@example.com"))

    assert exc.value.status_code == 409


def test_update_app_user_returns_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        update_app_user(db, 99, AppUserUpdate(name="Lucia"))

    assert exc.value.status_code == 404


def test_delete_app_user_removes_and_commits():
    db = MagicMock()
    user = make_user()
    db.query.return_value.filter.return_value.first.return_value = user

    delete_app_user(db, 1)

    db.delete.assert_called_once_with(user)
    db.commit.assert_called_once()


def test_delete_app_user_returns_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        delete_app_user(db, 99)

    assert exc.value.status_code == 404
