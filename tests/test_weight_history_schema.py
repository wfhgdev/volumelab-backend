from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.weight_history_schema import (
    WeightHistoryCreate,
    WeightHistoryUpdate,
)


@pytest.mark.parametrize("weight", [Decimal("0.01"), Decimal("9999.99")])
def test_weight_history_create_accepts_valid_boundary_values(weight):
    payload = WeightHistoryCreate(user_id=1, weight_kg=weight)
    assert payload.user_id == 1
    assert payload.weight_kg == weight


@pytest.mark.parametrize("weight", [0, -0.01, "75.555", "10000.00"])
def test_weight_history_create_rejects_invalid_weight(weight):
    with pytest.raises(ValidationError):
        WeightHistoryCreate(user_id=1, weight_kg=weight)


@pytest.mark.parametrize("user_id", [0, True])
def test_weight_history_create_rejects_invalid_user_id(user_id):
    with pytest.raises(ValidationError):
        WeightHistoryCreate(user_id=user_id, weight_kg=Decimal("75.00"))


def test_weight_history_update_accepts_partial_payload():
    payload = WeightHistoryUpdate(weight_kg=Decimal("74.25"))
    assert payload.weight_kg == Decimal("74.25")
    assert payload.user_id is None


@pytest.mark.parametrize("weight", [0, "74.123"])
def test_weight_history_update_rejects_invalid_weight(weight):
    with pytest.raises(ValidationError):
        WeightHistoryUpdate(weight_kg=weight)


@pytest.mark.parametrize("field", ["user_id", "weight_kg"])
def test_weight_history_update_rejects_explicit_null_on_non_nullable_fields(field):
    with pytest.raises(ValidationError):
        WeightHistoryUpdate(**{field: None})
