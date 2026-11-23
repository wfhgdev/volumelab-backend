from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.controllers.weight_history_controller import (
    create_weight_history,
    delete_weight_history,
    get_weight_history,
    list_weight_history,
    update_weight_history,
)
from app.models.app_user_model import AppUserModel, RoleUser, UserStatus
from app.schemas.weight_history_schema import WeightHistoryCreate, WeightHistoryUpdate


def create_user(db_session) -> AppUserModel:
    user = AppUserModel(
        email=f"weight_user_{uuid4().hex}@example.com",
        password_hash="hash",
        name="Weight",
        role=RoleUser.CLIENTE,
        status=UserStatus.ACTIVO,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_record(db_session, user_id: int, weight: str = "75.50"):
    return create_weight_history(
        db_session,
        WeightHistoryCreate(user_id=user_id, weight_kg=Decimal(weight)),
    )


def test_create_weight_history_persists_when_user_exists(db_session, test_user):
    result = create_record(db_session, test_user.id)

    assert result.id >= 1
    assert result.user_id == test_user.id
    assert result.weight_kg == Decimal("75.50")
    assert get_weight_history(db_session, result.id).id == result.id


def test_create_weight_history_raises_404_when_user_missing(db_session):
    with pytest.raises(HTTPException) as exc:
        create_record(db_session, 2_000_000_000)

    assert exc.value.status_code == 404


def test_list_weight_history_applies_order_and_pagination(db_session, test_user):
    first = create_record(db_session, test_user.id, "75.50")
    second = create_record(db_session, test_user.id, "76.00")

    result = list_weight_history(db_session, skip=0, limit=500, user_id=test_user.id)

    ids = [record.id for record in result]
    assert first.id in ids
    assert second.id in ids
    assert ids.index(second.id) < ids.index(first.id)
    assert len(list_weight_history(db_session, skip=0, limit=1, user_id=test_user.id)) == 1


def test_list_weight_history_filters_by_user_id(db_session, test_user):
    other = create_user(db_session)
    own_record = create_record(db_session, test_user.id)

    result = list_weight_history(
        db_session, skip=0, limit=500, user_id=test_user.id
    )

    assert any(record.id == own_record.id for record in result)
    assert all(record.user_id == test_user.id for record in result)
    assert all(record.user_id != other.id for record in result)


def test_get_weight_history_returns_record(db_session, test_user):
    record = create_record(db_session, test_user.id)

    result = get_weight_history(db_session, record.id)

    assert result.id == record.id


def test_get_weight_history_returns_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        get_weight_history(db_session, 2_000_000_000)

    assert exc.value.status_code == 404


def test_update_weight_history_changes_weight(db_session, test_user):
    record = create_record(db_session, test_user.id, "80.00")

    result = update_weight_history(
        db_session, record.id, WeightHistoryUpdate(weight_kg=Decimal("78.75"))
    )

    assert result.weight_kg == Decimal("78.75")
    assert result.user_id == test_user.id


def test_update_weight_history_validates_new_user_exists(db_session, test_user):
    record = create_record(db_session, test_user.id, "80.00")

    with pytest.raises(HTTPException) as exc:
        update_weight_history(
            db_session, record.id, WeightHistoryUpdate(user_id=2_000_000_000)
        )

    assert exc.value.status_code == 404


def test_update_weight_history_changes_user_when_valid(db_session, test_user):
    other = create_user(db_session)
    record = create_record(db_session, test_user.id, "80.00")

    result = update_weight_history(
        db_session,
        record.id,
        WeightHistoryUpdate(user_id=other.id, weight_kg=Decimal("79.00")),
    )

    assert result.user_id == other.id
    assert result.weight_kg == Decimal("79.00")


def test_update_weight_history_returns_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        update_weight_history(
            db_session, 2_000_000_000, WeightHistoryUpdate(weight_kg=Decimal("75.00"))
        )

    assert exc.value.status_code == 404


def test_delete_weight_history_removes_and_commits(db_session, test_user):
    record = create_record(db_session, test_user.id)

    delete_weight_history(db_session, record.id)

    with pytest.raises(HTTPException) as exc:
        get_weight_history(db_session, record.id)
    assert exc.value.status_code == 404


def test_delete_weight_history_returns_not_found(db_session):
    with pytest.raises(HTTPException) as exc:
        delete_weight_history(db_session, 2_000_000_000)

    assert exc.value.status_code == 404
