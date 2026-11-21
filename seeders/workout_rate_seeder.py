from sqlalchemy import text
from sqlalchemy.orm import Session
from seeders.factories.workout_rate_factory import make_workout_rate


def seed_workout_rates(db: Session) -> int:
    """
    Puebla valoraciones para ejercicios públicos y activos con usuarios existentes,
    respetando la restricción de unicidad (uq_workout_rate_user) y el trigger de validación.
    """
    public_workouts = db.execute(
        text("SELECT id FROM workout WHERE public = TRUE AND state = TRUE")
    ).scalars().all()
    users = db.execute(text("SELECT id FROM app_user")).scalars().all()

    inserted = 0
    for w_id in public_workouts:
        for u_id in users:
            exists = db.execute(
                text("SELECT 1 FROM workout_rate WHERE id_workout = :w_id AND user_id = :u_id"),
                {"w_id": w_id, "u_id": u_id},
            ).scalar()
            if not exists:
                db.add(make_workout_rate(id_workout=w_id, user_id=u_id))
                inserted += 1

    if inserted > 0:
        db.commit()
    return inserted
