from datetime import datetime
import pytest
from pydantic import ValidationError

from app.schemas.session_rate_schema import (
    SessionRateCreate,
    SessionRateResponse,
    SessionRateUpdate,
    SessionScoreResponse,
)


def test_session_rate_create_valid():
    payload = SessionRateCreate(id_workout_session=10, user_id=5, rate=4)
    assert payload.id_workout_session == 10
    assert payload.user_id == 5
    assert payload.rate == 4


@pytest.mark.parametrize("invalid_rate", [0, -1, 6, 10])
def test_session_rate_create_rejects_rate_out_of_range(invalid_rate):
    with pytest.raises(ValidationError):
        SessionRateCreate(id_workout_session=10, user_id=5, rate=invalid_rate)


@pytest.mark.parametrize("invalid_id", [0, -5])
def test_session_rate_create_rejects_non_positive_ids(invalid_id):
    with pytest.raises(ValidationError):
        SessionRateCreate(id_workout_session=invalid_id, user_id=5, rate=3)
    with pytest.raises(ValidationError):
        SessionRateCreate(id_workout_session=10, user_id=invalid_id, rate=3)


def test_session_rate_update_valid():
    payload = SessionRateUpdate(rate=5)
    assert payload.rate == 5


@pytest.mark.parametrize("invalid_rate", [0, 6])
def test_session_rate_update_rejects_out_of_range(invalid_rate):
    with pytest.raises(ValidationError):
        SessionRateUpdate(rate=invalid_rate)


def test_session_rate_response_serialization():
    now = datetime(2026, 11, 20, 12, 0, 0)
    response = SessionRateResponse(
        id=1,
        id_workout_session=10,
        user_id=2,
        rate=5,
        created_at=now,
    )
    dumped = response.model_dump()
    assert dumped["id"] == 1
    assert dumped["rate"] == 5
    assert dumped["created_at"] == now


def test_session_score_response():
    score = SessionScoreResponse(
        id_workout_session=10,
        avg_rate=4.5,
        total_rates=12,
    )
    assert score.id_workout_session == 10
    assert score.avg_rate == 4.5
    assert score.total_rates == 12
