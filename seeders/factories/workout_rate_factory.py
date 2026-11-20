import random
from app.models.workout_rate_model import WorkoutRateModel


def make_workout_rate(id_workout: int, user_id: int, rate: int | None = None) -> WorkoutRateModel:
    """Crea una instancia de WorkoutRateModel con puntuación válida (1 a 5)."""
    return WorkoutRateModel(
        id_workout=id_workout,
        user_id=user_id,
        rate=rate if rate is not None else random.randint(1, 5),
    )
