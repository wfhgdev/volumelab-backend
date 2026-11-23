from enum import Enum as PythonEnum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_connection import Base
from app.models.muscle_group_model import MuscleGroupModel
from app.models.workout_model import WorkoutModel


class MuscleRole(str, PythonEnum):
    PRIMARY = "PRIMARIO"
    SECONDARY = "SECUNDARIO"
    TERTIARY = "TERCIARIO"


class MuscleWorkoutModel(Base):
    __tablename__ = "muscle_workout"
    __table_args__ = (
        PrimaryKeyConstraint("workout_id", "muscle_group_id", name="pk_muscle_workout"),
        CheckConstraint(
            "(role_muscular = 'PRIMARIO' AND weighing = 100) OR "
            "(role_muscular = 'SECUNDARIO' AND weighing = 50) OR "
            "(role_muscular = 'TERCIARIO' AND weighing = 10)",
            name="chk_muscle_workout_weighing",
        ),
        Index("idx_muscle_workout_muscle_group", "muscle_group_id"),
    )

    workout_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(WorkoutModel.__table__.c.id, name="fk_muscle_workout_workout", ondelete="CASCADE"),
        primary_key=True,
    )
    muscle_group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(MuscleGroupModel.__table__.c.id, name="fk_muscle_workout_muscle_group", ondelete="CASCADE"),
        primary_key=True,
    )
    muscle_role: Mapped[MuscleRole] = mapped_column(
        "role_muscular",
        Enum(MuscleRole, name="muscle_role", values_callable=lambda members: [member.value for member in members], validate_strings=True),
        nullable=False,
    )
    weighing: Mapped[int] = mapped_column(Integer, nullable=False)
