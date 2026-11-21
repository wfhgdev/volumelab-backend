from datetime import datetime
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database_connection import Base

# Stub para workout_session si aún no ha sido cargado en Base.metadata
if "workout_session" not in Base.metadata.tables:
    Table("workout_session", Base.metadata, Column("id", BigInteger, primary_key=True), extend_existing=True)


class SessionRateModel(Base):
    """
    Modelo ORM para la entidad 'session_rate' (Valoraciones públicas de sesiones de entrenamiento).

    Representa la puntuación (1 a 5) otorgada por un usuario a una sesión de entrenamiento pública.
    Reglas de negocio:
    - RN-18: Puntuación de 1 a 5 (chk_session_rate).
    - Un único voto por usuario y sesión (uq_session_rate_user).
    - Trigger trg_session_rate_check_public: Solo se pueden valorar sesiones con public=TRUE.
    - RN-19: Supresión en cascada si se elimina el usuario o la sesión.
    """
    __tablename__ = "session_rate"
    __table_args__ = (
        UniqueConstraint("id_workout_session", "user_id", name="uq_session_rate_user"),
        CheckConstraint("rate >= 1 AND rate <= 5", name="chk_session_rate"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True, index=True
    )
    id_workout_session: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workout_session.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rate: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
