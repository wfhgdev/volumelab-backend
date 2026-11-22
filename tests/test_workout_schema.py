import pytest
from pydantic import ValidationError

from app.models.workout_model import ExerciseType
from app.schemas.workout_schema import WorkoutCreate, WorkoutResponse, WorkoutUpdate


def test_creation_preserves_database_defaults_and_trims_name():
    payload = WorkoutCreate(name="  Squat  ", type=ExerciseType.DYNAMIC, created_by=1)
    assert payload.name == "Squat"
    assert payload.type is ExerciseType.DYNAMIC
    assert payload.model_dump() == {
        "name": "Squat", "description": None, "type": ExerciseType.DYNAMIC,
        "is_bodyweight": False, "allow_positive_ballast": True,
        "allow_negative_ballast": False, "public": False, "state": True, "created_by": 1,
    }


@pytest.mark.parametrize("changes", [
    {"name": ""}, {"name": "   "}, {"name": "x" * 201},
    {"type": "INVALID"}, {"created_by": 0}, {"created_by": None},
    {"allow_negative_ballast": True}, {"id": 5},
])
def test_creation_rejects_invalid_input(changes):
    with pytest.raises(ValidationError):
        WorkoutCreate.model_validate({"name": "Squat", "type": "DINAMICO", "created_by": 1} | changes)


def test_bodyweight_exercise_can_allow_assistance():
    payload = WorkoutCreate(name="Pull-up", type=ExerciseType.DYNAMIC, created_by=1, is_bodyweight=True,
                            allow_negative_ballast=True)
    assert payload.allow_negative_ballast


@pytest.mark.parametrize("field_name",
                         ["name", "type", "created_by", "state", "public", "is_bodyweight", "allow_positive_ballast",
                          "allow_negative_ballast"])
def test_update_rejects_explicit_null(field_name):
    with pytest.raises(ValidationError):
        WorkoutUpdate.model_validate({field_name: None})


def test_update_preserves_omissions_and_allows_clearing_description():
    assert WorkoutUpdate().model_dump(exclude_unset=True) == {}
    assert WorkoutUpdate(description=None).model_dump(exclude_unset=True) == {"description": None}


def test_response_supports_anonymized_creator():
    result = WorkoutResponse(id=1, name="Plank", type=ExerciseType.ISOMETRIC, created_by=None)
    assert result.created_by is None
    assert "created_at" not in result.model_dump()
