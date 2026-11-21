import random
from app.models.session_rate_model import SessionRateModel


def make_session_rate(id_workout_session: int, user_id: int, rate: int | None = None) -> SessionRateModel:
    """Crea una instancia de SessionRateModel con puntuación válida (1 a 5)."""
    return SessionRateModel(
        id_workout_session=id_workout_session,
        user_id=user_id,
        rate=rate if rate is not None else random.randint(1, 5),
    )
