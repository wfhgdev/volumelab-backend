import pytest
from pydantic import ValidationError

from app.models.muscle_workout_model import MuscleRole, MuscleWorkoutModel
from app.schemas.muscle_workout_schema import MuscleWorkoutCreate, MuscleWorkoutResponse, MuscleWorkoutUpdate


@pytest.mark.parametrize(("role", "weighing"), [
    ("PRIMARIO", 100), ("SECUNDARIO", 50), ("TERCIARIO", 10),
])
def test_creation_derives_weighing_from_role(role, weighing):
    result = MuscleWorkoutCreate.model_validate({
        "workout_id": 1, "muscle_group_id": 2, "muscle_role": role,
    })
    assert result.weighing == weighing
    assert MuscleWorkoutCreate.model_validate(result.model_dump()).weighing == weighing


@pytest.mark.parametrize("changes", [
    {"workout_id": 0}, {"muscle_group_id": -1}, {"muscle_role": None},
    {"muscle_role": "INVALID"}, {"weighing": 50}, {"weighing": None},
    {"weighing": 100.0}, {"weighing": "100"}, {"id": 1},
])
def test_creation_rejects_invalid_input(changes):
    with pytest.raises(ValidationError):
        MuscleWorkoutCreate.model_validate({
            "workout_id": 1, "muscle_group_id": 2, "muscle_role": "PRIMARIO",
        } | changes)


def test_update_preserves_omitted_fields():
    assert MuscleWorkoutUpdate().model_dump(exclude_unset=True) == {}
    assert MuscleWorkoutUpdate(muscle_role=MuscleRole.SECONDARY).model_dump(exclude_unset=True) == {
        "muscle_role": MuscleRole.SECONDARY,
    }


@pytest.mark.parametrize("changes", [
    {"muscle_role": None}, {"weighing": None}, {"weighing": 25},
    {"workout_id": 2}, {"muscle_group_id": 3},
    {"muscle_role": "SECUNDARIO", "weighing": 100},
])
def test_update_rejects_invalid_input(changes):
    with pytest.raises(ValidationError):
        MuscleWorkoutUpdate.model_validate(changes)


def test_response_maps_english_attribute_to_existing_column():
    record = MuscleWorkoutModel(workout_id=1, muscle_group_id=2, muscle_role=MuscleRole.TERTIARY, weighing=10)
    response = MuscleWorkoutResponse.model_validate(record)
    assert response.model_dump(mode="json") == {
        "workout_id": 1, "muscle_group_id": 2, "muscle_role": "TERCIARIO", "weighing": 10,
    }
    assert MuscleWorkoutModel.__table__.c.role_muscular.name == "role_muscular"
