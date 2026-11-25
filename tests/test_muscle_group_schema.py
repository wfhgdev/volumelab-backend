import pytest
from pydantic import ValidationError

from app.models.muscle_group_model import MuscleGroupModel
from app.schemas.muscle_group_schema import (
    MuscleGroupCreate, MuscleGroupResponse, MuscleGroupUpdate,
)


def test_creation_trims_name_and_preserves_optional_description():
    result = MuscleGroupCreate(name="  Chest  ", created_by=1)
    assert result.model_dump() == {
        "name": "Chest", "description": None, "created_by": 1,
    }


@pytest.mark.parametrize("changes", [
    {"name": ""}, {"name": " "}, {"name": "x" * 151}, {"name": None},
    {"created_by": 0}, {"created_by": -1},
    {"id": 5}, {"state": True},
])
def test_creation_rejects_invalid_input(changes):
    with pytest.raises(ValidationError):
        MuscleGroupCreate.model_validate({"name": "Chest", "created_by": 1} | changes)


def test_creation_allows_optional_creator():
    item = MuscleGroupCreate.model_validate({"name": "Chest"})
    assert item.created_by is None


def test_update_preserves_omissions_and_can_clear_description():
    assert MuscleGroupUpdate().model_dump(exclude_unset=True) == {}
    assert MuscleGroupUpdate(description=None).model_dump(exclude_unset=True) == {
        "description": None,
    }


@pytest.mark.parametrize("changes", [
    {"name": None}, {"created_by": None}, {"created_by": 0}, {"name": " "},
    {"name": "x" * 151}, {"state": False},
])
def test_update_rejects_invalid_input(changes):
    with pytest.raises(ValidationError):
        MuscleGroupUpdate.model_validate(changes)


def test_response_supports_anonymized_creator_and_orm_conversion():
    record = MuscleGroupModel(id=1, name="Chest", description=None, created_by=None)
    response = MuscleGroupResponse.model_validate(record)
    assert response.model_dump() == {
        "id": 1, "name": "Chest", "description": None, "created_by": None,
    }
