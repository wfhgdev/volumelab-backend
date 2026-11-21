from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.controllers.weight_history_controller import (
    create_weight_history,
    delete_weight_history,
    get_weight_history,
    list_weight_history,
    update_weight_history,
)
from app.models.weight_history_model import WeightHistoryModel
from app.schemas.weight_history_schema import WeightHistoryCreate, WeightHistoryUpdate


def make_weight_record(
    record_id: int = 1,
    user_id: int = 1,
    weight_kg: Decimal = Decimal("75.50"),
) -> WeightHistoryModel:
    return WeightHistoryModel(
        id=record_id,
        user_id=user_id,
        weight_kg=weight_kg,
        created_at=datetime(2026, 11, 20, 9, 0, 0),
    )


def test_create_weight_history_commits_when_user_exists():
    db = MagicMock()
    db.execute.return_value.first.return_value = (1,)
    payload = WeightHistoryCreate(user_id=1, weight_kg=Decimal("75.50"))

    result = create_weight_history(db, payload)

    db.execute.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert result.user_id == 1
    assert result.weight_kg == Decimal("75.50")


def test_create_weight_history_raises_404_when_user_missing():
    db = MagicMock()
    db.execute.return_value.first.return_value = None
    payload = WeightHistoryCreate(user_id=999, weight_kg=Decimal("75.50"))

    with pytest.raises(HTTPException) as exc:
        create_weight_history(db, payload)

    assert exc.value.status_code == 404
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_list_weight_history_applies_order_and_pagination():
    db = MagicMock()
    query = db.query.return_value
    query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        make_weight_record()
    ]

    result = list_weight_history(db, skip=5, limit=10)

    assert len(result) == 1
    assert result[0].id == 1
    query.filter.assert_not_called()
    query.order_by.return_value.offset.assert_called_once_with(5)
    query.order_by.return_value.offset.return_value.limit.assert_called_once_with(10)


def test_list_weight_history_filters_by_user_id():
    db = MagicMock()
    query = db.query.return_value
    filtered = query.filter.return_value
    filtered.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        make_weight_record(user_id=2)
    ]

    result = list_weight_history(db, skip=0, limit=20, user_id=2)

    assert len(result) == 1
    assert result[0].user_id == 2
    query.filter.assert_called_once()


def test_get_weight_history_returns_record():
    db = MagicMock()
    record = make_weight_record(record_id=7)
    db.query.return_value.filter.return_value.first.return_value = record

    result = get_weight_history(db, 7)

    assert result.id == 7


def test_get_weight_history_returns_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_weight_history(db, 99)

    assert exc.value.status_code == 404


def test_update_weight_history_changes_weight():
    db = MagicMock()
    record = make_weight_record(record_id=1, user_id=1, weight_kg=Decimal("80.00"))
    db.query.return_value.filter.return_value.first.return_value = record

    result = update_weight_history(db, 1, WeightHistoryUpdate(weight_kg=Decimal("78.75")))

    assert result.weight_kg == Decimal("78.75")
    assert result.user_id == 1
    db.execute.assert_not_called()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(record)


def test_update_weight_history_validates_new_user_exists():
    db = MagicMock()
    record = make_weight_record(record_id=1, user_id=1, weight_kg=Decimal("80.00"))
    db.query.return_value.filter.return_value.first.return_value = record
    db.execute.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        update_weight_history(db, 1, WeightHistoryUpdate(user_id=999))

    assert exc.value.status_code == 404
    db.commit.assert_not_called()


def test_update_weight_history_changes_user_when_valid():
    db = MagicMock()
    record = make_weight_record(record_id=1, user_id=1, weight_kg=Decimal("80.00"))
    db.query.return_value.filter.return_value.first.return_value = record
    db.execute.return_value.first.return_value = (1,)

    result = update_weight_history(
        db, 1, WeightHistoryUpdate(user_id=2, weight_kg=Decimal("79.00"))
    )

    assert result.user_id == 2
    assert result.weight_kg == Decimal("79.00")
    db.commit.assert_called_once()


def test_update_weight_history_returns_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        update_weight_history(db, 99, WeightHistoryUpdate(weight_kg=Decimal("75.00")))

    assert exc.value.status_code == 404


def test_delete_weight_history_removes_and_commits():
    db = MagicMock()
    record = make_weight_record()
    db.query.return_value.filter.return_value.first.return_value = record

    delete_weight_history(db, 1)

    db.delete.assert_called_once_with(record)
    db.commit.assert_called_once()


def test_delete_weight_history_returns_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        delete_weight_history(db, 99)

    assert exc.value.status_code == 404
