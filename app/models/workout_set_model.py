from decimal import Decimal
from enum import Enum as PythonEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database_connection import Base


class WorkoutSetExerciseType(str, PythonEnum):
    DINAMICO = "DINAMICO"
    ISOMETRICO = "ISOMETRICO"


class WorkoutSetSessionStatus(str, PythonEnum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


if "workout_session" not in Base.metadata.tables:
    workout_session_table = Table(
        "workout_session",
        Base.metadata,
        Column("id", BigInteger, primary_key=True),
        Column("current_bodyweight_kg", Numeric(6, 2)),
        Column("status", String(10)),
        extend_existing=True,
    )
else:
    workout_session_table = Base.metadata.tables["workout_session"]
    if "current_bodyweight_kg" not in workout_session_table.c:
        workout_session_table.append_column(Column("current_bodyweight_kg", Numeric(6, 2)))
    if "status" not in workout_session_table.c:
        workout_session_table.append_column(Column("status", String(10)))

if "workout" not in Base.metadata.tables:
    workout_table = Table(
        "workout",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("is_bodyweight", Boolean, nullable=False),
        Column("type", String(20), nullable=False),
        extend_existing=True,
    )
else:
    workout_table = Base.metadata.tables["workout"]
    if "is_bodyweight" not in workout_table.c:
        workout_table.append_column(Column("is_bodyweight", Boolean, nullable=False))
    if "type" not in workout_table.c:
        workout_table.append_column(Column("type", String(20), nullable=False))


class WorkoutSetModel(Base):
    __tablename__ = "workout_set"
    __table_args__ = (
        CheckConstraint("set_number >= 1", name="chk_set_number"),
        CheckConstraint("exercise_order >= 1", name="chk_set_order"),
        CheckConstraint("reps IS NULL OR reps >= 1", name="chk_set_reps"),
        CheckConstraint("duration_second IS NULL OR duration_second >= 1", name="chk_set_duration"),
        CheckConstraint("rir IS NULL OR (rir >= 0 AND rir <= 10)", name="chk_set_rir"),
        CheckConstraint("effective_weight_kg IS NULL OR effective_weight_kg > 0", name="chk_set_effective"),
        CheckConstraint(
            "one_rm_percentage IS NULL OR one_rm_percentage >= 0",
            name="chk_set_one_rm_pct",
        ),
        CheckConstraint(
            "(reps IS NULL) <> (duration_second IS NULL)",
            name="chk_set_reps_xor_duration",
        ),
        UniqueConstraint(
            "session_id",
            "exercise_order",
            "set_number",
            name="uq_workout_set_position",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(always=True),
        primary_key=True,
    )
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workout_session.id", name="fk_workout_set_session", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workout.id", name="fk_workout_set_exercise", ondelete="RESTRICT"),
        nullable=False,
    )
    exercise_order: Mapped[int] = mapped_column(Integer, nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    added_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_second: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rir: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    one_rm_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    one_rm_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    volume_load: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
