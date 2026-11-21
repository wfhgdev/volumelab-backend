from sqlalchemy import text
from sqlalchemy.orm import Session
from seeders.factories.session_rate_factory import make_session_rate


def seed_session_rates(db: Session) -> int:
    """
    Puebla valoraciones para sesiones públicas existentes,
    respetando la restricción de unicidad (uq_session_rate_user) y el trigger de validación.
    """
    public_sessions = db.execute(
        text("SELECT id FROM workout_session WHERE public = TRUE")
    ).scalars().all()
    users = db.execute(text("SELECT id FROM app_user")).scalars().all()

    inserted = 0
    for s_id in public_sessions:
        for u_id in users:
            exists = db.execute(
                text("SELECT 1 FROM session_rate WHERE id_workout_session = :s_id AND user_id = :u_id"),
                {"s_id": s_id, "u_id": u_id},
            ).scalar()
            if not exists:
                db.add(make_session_rate(id_workout_session=s_id, user_id=u_id))
                inserted += 1

    if inserted > 0:
        db.commit()
    return inserted
