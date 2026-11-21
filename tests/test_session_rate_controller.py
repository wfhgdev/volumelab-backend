from datetime import datetime
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.controllers.session_rate_controller import (
    create_session_rate,
    delete_session_rate,
    get_session_rate_by_id,
    get_session_rate_by_session_and_user,
    get_session_rates,
    get_session_score,
    update_session_rate,
    upsert_session_rate,
)
from app.models.session_rate_model import SessionRateModel
from app.schemas.session_rate_schema import SessionRateCreate, SessionRateUpdate


def make_session_rate(rate_id: int = 1, session_id: int = 10, user_id: int = 1, rate: int = 5) -> SessionRateModel:
    return SessionRateModel(
        id=rate_id,
        id_workout_session=session_id,
        user_id=user_id,
        rate=rate,
        created_at=datetime(2026, 11, 20, 10, 0, 0),
    )


def test_create_session_rate_commits():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    payload = SessionRateCreate(id_workout_session=10, user_id=1, rate=5)

    result = create_session_rate(db, payload)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert result.id_workout_session == 10
    assert result.user_id == 1
    assert result.rate == 5


def test_create_session_rate_rejects_duplicate():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = make_session_rate()
    payload = SessionRateCreate(id_workout_session=10, user_id=1, rate=4)

    with pytest.raises(HTTPException) as exc:
        create_session_rate(db, payload)

    assert exc.value.status_code == 409
    assert "ya ha valorado" in exc.value.detail


def test_create_session_rate_catches_private_trigger():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    orig_error = Exception("La sesión 10 no es pública y no se puede valorar")
    db.commit.side_effect = DBAPIError("INSERT", {}, orig_error)

    payload = SessionRateCreate(id_workout_session=10, user_id=1, rate=5)
    with pytest.raises(HTTPException) as exc:
        create_session_rate(db, payload)

    assert exc.value.status_code == 400
    assert "no es pública y no se puede valorar" in exc.value.detail


def test_get_session_rate_by_id_found():
    db = MagicMock()
    expected = make_session_rate(rate_id=5)
    db.query.return_value.filter.return_value.first.return_value = expected

    result = get_session_rate_by_id(db, 5)
    assert result.id == 5


def test_get_session_rate_by_id_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_session_rate_by_id(db, 999)

    assert exc.value.status_code == 404


def test_get_session_rate_by_session_and_user():
    db = MagicMock()
    expected = make_session_rate(session_id=10, user_id=1)
    db.query.return_value.filter.return_value.first.return_value = expected

    result = get_session_rate_by_session_and_user(db, 10, 1)
    assert result.id_workout_session == 10
    assert result.user_id == 1


def test_update_session_rate():
    db = MagicMock()
    existing = make_session_rate(rate_id=3, rate=2)
    db.query.return_value.filter.return_value.first.return_value = existing

    update_payload = SessionRateUpdate(rate=5)
    result = update_session_rate(db, 3, update_payload)

    assert result.rate == 5
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_upsert_session_rate_updates_if_exists():
    db = MagicMock()
    existing = make_session_rate(rate_id=3, rate=2)
    db.query.return_value.filter.return_value.first.return_value = existing

    payload = SessionRateCreate(id_workout_session=10, user_id=1, rate=4)
    result = upsert_session_rate(db, payload)

    assert result.rate == 4
    db.commit.assert_called_once()


def test_delete_session_rate():
    db = MagicMock()
    existing = make_session_rate(rate_id=3)
    db.query.return_value.filter.return_value.first.return_value = existing

    delete_session_rate(db, 3)

    db.delete.assert_called_once_with(existing)
    db.commit.assert_called_once()


def test_get_session_score():
    db = MagicMock()
    result_mock = MagicMock()
    result_mock.avg_rate = 4.25
    result_mock.total_rates = 8
    db.query.return_value.filter.return_value.one.return_value = result_mock

    score = get_session_score(db, 10)
    assert score["id_workout_session"] == 10
    assert score["avg_rate"] == 4.25
    assert score["total_rates"] == 8
