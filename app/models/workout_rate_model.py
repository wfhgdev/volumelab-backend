from datetime import datetime
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database_connection import Base

# Definición de tablas de referencia con extend_existing para resolución de FKs
# en SQLAlchemy antes de que los modelos completos sean cargados.
if "workout" not in Base.metadata.tables:
    Table("workout", Base.metadata, Column("id", Integer, primary_key=True), extend_existing=True)
if "app_user" not in Base.metadata.tables:
    Table("app_user", Base.metadata, Column("id", BigInteger, primary_key=True), extend_existing=True)


class WorkoutRateModel(Base):
    """
    Modelo ORM para la entidad 'workout_rate' (Valoraciones públicas de ejercicios).

    Representa la puntuación (1 a 5) otorgada por un usuario a un ejercicio público y activo.
    Reglas de negocio:
    - RN-18: Puntuación de 1 a 5 (chk_workout_rate).
    - Un único voto por usuario y ejercicio (uq_workout_rate_user).
    - Trigger trg_workout_rate_check_public: Solo se pueden valorar ejercicios con public=TRUE y state=TRUE.
    - RN-19: Supresión en cascada si se elimina el usuario o el ejercicio.
    """
    __tablename__ = "workout_rate"
    __table_args__ = (
        UniqueConstraint("id_workout", "user_id", name="uq_workout_rate_user"),
        CheckConstraint("rate >= 1 AND rate <= 5", name="chk_workout_rate"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, index=True
    )
    id_workout: Mapped[int] = mapped_column(
        Integer, ForeignKey("workout.id", ondelete="CASCADE"), nullable=False, index=True
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
